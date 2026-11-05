"""API Futura : parcours, correction des exercices, XP, métacognition."""
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..content import category, load, public_view
from ..db import Completion, ExerciseResult, Prediction, Reflection, User, get_db, now
from ..grading import check_rubric, check_short
from ..security import read_token, subject

router = APIRouter(prefix="/api", tags=["futura"])


def _allowed(p: dict, u: User) -> bool:
    """Un élève voit ses parcours ; FUTURA_TEST_MODE=1 ouvre tout à tout le monde (tests)."""
    return os.getenv("FUTURA_TEST_MODE") == "1" or p["target_user"] == u.name


class CheckIn(BaseModel):
    user: str = Field(max_length=40)
    answer: str = Field(min_length=1, max_length=3000)


class ReflectionIn(BaseModel):
    user: str = Field(max_length=40)
    confidence: int = Field(ge=1, le=5)
    comment: str = Field("", max_length=1000)
    prediction_result: str | None = Field(None, pattern="^(acerte|casi|cambie)$")


class PredictionIn(BaseModel):
    user: str = Field(max_length=40)
    text: str = Field("", max_length=600)


def _user(db: Session, name: str) -> User:
    u = db.scalar(select(User).where(User.name == name))
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


def _auth(u: User, token: str | None) -> None:
    """Si l'élève a un PIN, un jeton valide est obligatoire."""
    if u.pin_hash and read_token(token) != subject(u):
        raise HTTPException(401, "Sesión no válida: escribe tu PIN para entrar.")


def _parcours(pid: str) -> dict:
    p = load().get(pid)
    if not p:
        raise HTTPException(404, "Parcours no encontrado")
    return p


def _solved(db: Session, uid: int, pid: str) -> list[str]:
    return list(db.scalars(select(ExerciseResult.exercise_id).where(
        ExerciseResult.user_id == uid, ExerciseResult.parcours_id == pid, ExerciseResult.correct)))


@router.get("/users")
def users(db: Session = Depends(get_db)):
    return [{"name": u.name, "xp": u.xp, "has_pin": bool(u.pin_hash)} for u in db.scalars(select(User).order_by(User.id))]


@router.get("/parcours")
def list_parcours(user: str, db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    u = _user(db, user)
    _auth(u, x_futura_token)
    done = set(db.scalars(select(Completion.parcours_id).where(Completion.user_id == u.id)))
    return [{"id": p["id"], "title": p["title"], "field": p["field"], "category": category(p), "xp_reward": p["xp_reward"],
             "done": p["id"] in done, "solved": len(_solved(db, u.id, p["id"]))}
            for p in load().values() if _allowed(p, u)]


@router.get("/parcours/{pid}")
def get_parcours(pid: str, user: str, db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    u = _user(db, user)
    _auth(u, x_futura_token)
    p = _parcours(pid)
    if not _allowed(p, u):
        raise HTTPException(403, "Este parcours es para otra persona")
    pred = db.scalar(select(Prediction).where(Prediction.user_id == u.id, Prediction.parcours_id == pid))
    return {**public_view(p), "category": category(p), "solved": _solved(db, u.id, pid), "prediction": pred.text if pred else ""}


@router.post("/parcours/{pid}/exercises/{eid}/check")
def check(pid: str, eid: str, body: CheckIn, db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    u = _user(db, body.user)
    _auth(u, x_futura_token)
    p = _parcours(pid)
    if not _allowed(p, u):
        raise HTTPException(403, "Este parcours es para otra persona")
    ex = next((e for e in p["exercises"] if e["id"] == eid), None)
    if not ex:
        raise HTTPException(404, "Ejercicio no encontrado")

    out = {"correct": False, "feedback": "", "xp_awarded": 0}
    if ex["level"] <= 3:
        out["correct"] = check_short(body.answer, ex["expected_answer"])
        fail = "Casi. Revisa tu razonamiento e inténtalo de nuevo."
    else:
        ok, found, req = check_rubric(body.answer, ex["rubric_keywords"])
        out.update(correct=ok, keywords_found=found, keywords_required=req)
        fail = (f"Tu argumento aún no es suficiente: usa al menos {req} conceptos clave "
                f"(llevas {found}) y explica tu razonamiento con varias frases.")
    out["feedback"] = ex["feedback_success"] if out["correct"] else fail
    if out["correct"] and ex["level"] == 4:
        out["model_answer"] = ex["expected_answer"]  # se muestra solo tras acertar

    r = db.scalar(select(ExerciseResult).where(ExerciseResult.user_id == u.id,
                  ExerciseResult.parcours_id == pid, ExerciseResult.exercise_id == eid))
    if not r:
        r = ExerciseResult(user_id=u.id, parcours_id=pid, exercise_id=eid, attempts=0, correct=False)
        db.add(r)
    r.attempts += 1
    r.correct = r.correct or out["correct"]
    db.flush()

    if out["correct"] and len(_solved(db, u.id, pid)) == len(p["exercises"]) \
            and not db.scalar(select(Completion).where(Completion.user_id == u.id, Completion.parcours_id == pid)):
        db.add(Completion(user_id=u.id, parcours_id=pid, xp=p["xp_reward"]))
        u.xp += p["xp_reward"]  # XP otorgado una sola vez por parcours
        out["xp_awarded"] = p["xp_reward"]
    db.commit()
    out["total_xp"] = u.xp
    return out


@router.post("/parcours/{pid}/metacognition")
def metacognition(pid: str, body: ReflectionIn, db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    u = _user(db, body.user)
    _auth(u, x_futura_token)
    _parcours(pid)
    db.add(Reflection(user_id=u.id, parcours_id=pid, confidence=body.confidence, comment=body.comment, prediction_result=body.prediction_result))
    db.commit()
    return {"ok": True}


@router.post("/parcours/{pid}/prediction")
def prediction(pid: str, body: PredictionIn, db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    u = _user(db, body.user)
    _auth(u, x_futura_token)
    p = _parcours(pid)
    if not _allowed(p, u):
        raise HTTPException(403, "Este parcours es para otra persona")
    row = db.scalar(select(Prediction).where(Prediction.user_id == u.id, Prediction.parcours_id == pid))
    if row:
        row.text, row.updated_at = body.text.strip(), now()
    else:
        db.add(Prediction(user_id=u.id, parcours_id=pid, text=body.text.strip()))
    db.commit()
    return {"ok": True}
