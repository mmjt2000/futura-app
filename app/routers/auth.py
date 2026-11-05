"""Connexion par PIN (élèves), espace parent protégé et résumé de progression."""
import hmac
import os
import re

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content import category, load
from ..db import Completion, ExerciseResult, Prediction, Reflection, User, get_db
from ..security import clear_fails, hash_pin, locked, make_token, read_token, register_fail, subject, verify_pin

router = APIRouter(prefix="/api", tags=["auth"])


class LoginIn(BaseModel):
    user: str = Field(max_length=40)
    pin: str | None = Field(None, max_length=12)


class ParentLoginIn(BaseModel):
    pin: str = Field(max_length=64)


class SetPinIn(BaseModel):
    user: str = Field(max_length=40)
    pin: str | None = Field(None, max_length=12)  # None = supprimer le PIN


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.name == body.user))
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if u.pin_hash:
        key = f"user:{u.name}"
        if locked(key):
            raise HTTPException(429, "Demasiados intentos. Espera unos minutos.")
        if not body.pin or not verify_pin(body.pin, u.pin_hash):
            register_fail(key)
            raise HTTPException(401, "PIN incorrecto")
        clear_fails(key)
    return {"token": make_token(subject(u)), "has_pin": bool(u.pin_hash)}


@router.post("/parent/login")
def parent_login(body: ParentLoginIn):
    expected = os.getenv("FUTURA_PARENT_PIN")
    if not expected:
        raise HTTPException(403, "Espace parent désactivé : définis la variable FUTURA_PARENT_PIN.")
    if locked("parent"):
        raise HTTPException(429, "Trop d'essais : attends quelques minutes.")
    if not hmac.compare_digest(body.pin.encode(), expected.encode()):
        register_fail("parent")
        raise HTTPException(401, "Code incorrect")
    clear_fails("parent")
    return {"token": make_token("parent")}


def _require_parent(token: str | None) -> None:
    if read_token(token) != "parent":
        raise HTTPException(401, "Session parent expirée : reconnecte-toi.")


@router.get("/parent/summary")
def summary(db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    _require_parent(x_futura_token)
    P, out = load(), []
    for u in db.scalars(select(User).order_by(User.id)):
        results = db.scalars(select(ExerciseResult).where(ExerciseResult.user_id == u.id)).all()
        done = {c.parcours_id: c for c in db.scalars(select(Completion).where(Completion.user_id == u.id))}
        rows = []
        for pid, p in P.items():
            if p["target_user"] != u.name:
                continue
            rr = [r for r in results if r.parcours_id == pid]
            rows.append({"id": pid, "title": p["title"], "category": category(p), "solved": sum(r.correct for r in rr),
                         "attempts": sum(r.attempts for r in rr), "done": pid in done,
                         "completed_at": done[pid].completed_at.isoformat() if pid in done else None})
        refl = db.scalars(select(Reflection).where(Reflection.user_id == u.id).order_by(Reflection.created_at.desc()).limit(10)).all()
        preds = db.scalars(select(Prediction).where(Prediction.user_id == u.id, Prediction.text != "").order_by(Prediction.updated_at.desc()).limit(10)).all()
        last = {r.parcours_id: r.prediction_result for r in sorted(refl, key=lambda r: r.created_at) if r.prediction_result}
        out.append({"name": u.name, "xp": u.xp, "has_pin": bool(u.pin_hash), "parcours": rows,
                    "reflections": [{"title": P[r.parcours_id]["title"] if r.parcours_id in P else r.parcours_id,
                                     "confidence": r.confidence, "comment": r.comment, "prediction_result": r.prediction_result, "created_at": r.created_at.isoformat()} for r in refl],
                    "predictions": [{"title": P[x.parcours_id]["title"] if x.parcours_id in P else x.parcours_id, "text": x.text, "result": last.get(x.parcours_id),
                                     "question": P[x.parcours_id]["contexte"]["question_reflexion"] if x.parcours_id in P else "", "updated_at": x.updated_at.isoformat()} for x in preds]})
    return out


@router.post("/parent/pin")
def set_pin(body: SetPinIn, db: Session = Depends(get_db), x_futura_token: str | None = Header(None)):
    _require_parent(x_futura_token)
    u = db.scalar(select(User).where(User.name == body.user))
    if not u:
        raise HTTPException(404, "Élève introuvable")
    if body.pin is None:
        u.pin_hash = None
    elif re.fullmatch(r"\d{4,8}", body.pin):
        u.pin_hash = hash_pin(body.pin)
    else:
        raise HTTPException(422, "Le code doit contenir de 4 à 8 chiffres.")
    db.commit()
    return {"ok": True, "has_pin": bool(u.pin_hash)}
