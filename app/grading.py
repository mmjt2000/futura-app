"""Logique de correction pure (sans I/O) : facile à tester."""
import math
import re
import unicodedata

THRESHOLD = 0.6      # 60 % des mots-clés de la rubrique
MIN_WORDS_L4 = 15    # une liste de mots-clés n'est pas une argumentation


def normalize(text: str) -> str:
    """Minuscules, sans accents, signes mathématiques unifiés."""
    text = text.strip().lower().replace("^2", "²").replace("−", "-").replace("–", "-")
    text = unicodedata.normalize("NFD", text.replace("\u00a0", " "))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text)


def compact(text: str) -> str:
    return normalize(text).replace(" ", "").rstrip(".")


def check_short(student: str, expected: str) -> bool:
    """Niveaux 1-3 : correspondance exacte ; alternatives séparées par '|'."""
    s = compact(student)
    return any(s == compact(alt) for alt in expected.split("|") if alt.strip())


def _hit(keyword: str, answer: str) -> bool:
    """Mot-clé présent tel quel, ou par son radical (factorizar ↔ factorización)."""
    k = normalize(keyword)
    return k in answer or (" " not in k and len(k) >= 7 and k[:-3] in answer)


def check_rubric(student: str, keywords: list[str]) -> tuple[bool, int, int]:
    """Niveau 4 : (validé, trouvés, requis)."""
    answer = normalize(student)
    required = max(1, math.ceil(len(keywords) * THRESHOLD - 1e-9))
    found = sum(_hit(k, answer) for k in keywords)
    return (found >= required and len(answer.split()) >= MIN_WORDS_L4), found, required
