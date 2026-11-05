"""Chargement et validation de data/parcours.json (source de vérité)."""
import json
from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA_FILE = BASE / "data" / "parcours.json"
USERS = ("Maryse", "Laeticia")
KEYS = {"id", "target_user", "field", "curriculum_alignment", "pisa_competency", "title",
        "contexte", "khan", "labo", "carnet", "exercises", "xp_reward", "revision"}
PROCESSES = {"Formular", "Emplear", "Interpretar", "Evaluar"}
# Catégorie déduite du préfixe de `field` : le schéma JSON reste inchangé.
CATEGORIES = {"matematicas": "matematicas", "quimica": "ciencias", "biologia": "ciencias", "fisica": "ciencias"}


def category(p: dict) -> str:
    return CATEGORIES[p["field"].split("_", 1)[0]]


SECRETS = ("expected_answer", "rubric_keywords", "feedback_success")


def validate(p: dict) -> None:
    """Échoue au démarrage si un parcours est mal formé (mieux qu'un bug en production)."""
    pid = p.get("id", "?")
    if KEYS - p.keys():
        raise ValueError(f"{pid}: clés manquantes {sorted(KEYS - p.keys())}")
    if p["target_user"] not in USERS:
        raise ValueError(f"{pid}: target_user inconnu")
    if {c["process"] for c in p["carnet"]} != PROCESSES or len(p["carnet"]) != 4:
        raise ValueError(f"{pid}: le carnet doit couvrir les 4 processus PISA")
    if p["field"].split("_", 1)[0] not in CATEGORIES:
        raise ValueError(f"{pid}: préfixe de field inconnu (attendu: {sorted(CATEGORIES)})")
    if [e["level"] for e in p["exercises"]] != [1, 2, 3, 4]:
        raise ValueError(f"{pid}: 4 exercices de niveau 1 à 4 requis")
    if len(p["exercises"][3].get("rubric_keywords", [])) < 4:
        raise ValueError(f"{pid}: le niveau 4 exige au moins 4 rubric_keywords")
    c = p["contexte"]
    need = {"titre", "texte", "problema", "meta", "question_reflexion"}
    if not (need <= set(c) <= need | {"dato"}) or not all(isinstance(c[k], str) and c[k].strip() for k in need):
        raise ValueError(f"{pid}: contexte doit avoir titre, texte, problema, meta, question_reflexion (non vides) et, en option, dato")
    d = c.get("dato")
    if d is not None and not (d.get("titulo") and 2 <= len(d.get("filas", [])) <= 5 and all(len(x) == 2 and all(isinstance(v, str) and v for v in x) for x in d["filas"])):
        raise ValueError(f"{pid}: contexte.dato mal formé (titulo + 2 à 5 filas de 2 cellules)")
    r = p["revision"]
    if not (r.get("idea") and 4 <= len(r.get("mapa", [])) <= 6 and r.get("formulas") and len(r.get("astucias", [])) >= 2
            and r.get("errores") and len(r.get("tarjetas", [])) >= 3):
        raise ValueError(f"{pid}: la fiche de révision (revision) est incomplète")
    if not all(c.get("q") and c.get("a") for c in r["tarjetas"]) or not all(x.get("t") and x.get("f") for x in r["formulas"]):
        raise ValueError(f"{pid}: tarjetas ou formulas mal formées")
    if not (BASE / p["labo"]["file"]).is_file():
        raise ValueError(f"{pid}: laboratoire introuvable ({p['labo']['file']})")


@lru_cache(maxsize=1)
def load() -> dict[str, dict]:
    with DATA_FILE.open(encoding="utf-8") as f:
        items = json.load(f)
    ids = [p["id"] for p in items]
    if len(ids) != len(set(ids)):
        raise ValueError("ids de parcours dupliqués")
    for p in items:
        validate(p)
    return {p["id"]: p for p in items}


def public_view(p: dict) -> dict:
    """Version envoyée au navigateur : sans réponses ni rubriques."""
    safe = json.loads(json.dumps(p))
    for ex in safe["exercises"]:
        for k in SECRETS:
            ex.pop(k, None)
    return safe
