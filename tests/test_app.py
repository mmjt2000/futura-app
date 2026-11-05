import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.grading import check_rubric, check_short, normalize
from app.content import load


def test_normalisation_et_alternatives():
    assert check_short("x^2 + 3x −40 = 0", "x²+3x-40=0")
    assert check_short("2 y 3", "2,3|2y3")
    assert check_short("Púrpura", "púrpura|morada")
    assert not check_short("3", "4|4s")
    assert normalize("  ÁÉ  ñ ") == "ae n"


def test_rubrique_niveau_4():
    kw = ["factorizar", "fórmula general", "discriminante", "comprobar", "solución"]
    long = "Al factorizar la ecuación encuentro cada solución y para comprobar sustituyo cada valor en la ecuación original con cuidado"
    assert check_rubric(long, kw)[0]
    assert not check_rubric("factorizar discriminante comprobar", kw)[0]  # trop court
    assert not check_rubric("No sé nada de este tema pero lo intento con muchas palabras sin sentido alguno aquí", kw)[0]


def test_contenu_valide_et_espagnol_present():
    assert len(load()) == 32


def test_categories():
    from app.content import category
    cats = {pid: category(p) for pid, p in load().items()}
    assert cats["mat_funcion_lineal"] == "matematicas" and cats["mat_interes_compuesto"] == "matematicas"
    assert cats["bio_celula"] == cats["qui_estructura_atomica"] == cats["bio_genetica_mendel"] == "ciencias"


def test_chaque_parcours_est_resoluble_par_son_propre_corrige():
    """Qualité du contenu : les réponses attendues passent le correcteur."""
    for p in load().values():
        for ex in p["exercises"][:3]:
            assert all(check_short(alt, ex["expected_answer"]) for alt in ex["expected_answer"].split("|")), (p["id"], ex["id"])
        l4 = p["exercises"][3]
        assert check_rubric(l4["expected_answer"], l4["rubric_keywords"])[0], p["id"]


def test_api_flux_complet():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        assert {u["name"] for u in c.get("/api/users").json()} == {"Maryse", "Laeticia"}
        pid = "bio_genetica_mendel"
        detail = c.get(f"/api/parcours/{pid}", params={"user": "Laeticia"}).json()
        assert "expected_answer" not in str(detail) and "rubric_keywords" not in str(detail)
        assert c.get(f"/api/parcours/{pid}", params={"user": "Maryse"}).status_code == 403
        url = lambda e: f"/api/parcours/{pid}/exercises/{e}/check"
        assert not c.post(url("ex_02"), json={"user": "Laeticia", "answer": "50"}).json()["correct"]
        for e, a in [("ex_01", "púrpura"), ("ex_02", "25%"), ("ex_03", "heterocigoto")]:
            assert c.post(url(e), json={"user": "Laeticia", "answer": a}).json()["correct"]
        r = c.post(url("ex_04"), json={"user": "Laeticia", "answer":
            "Es falso porque si los padres son heterocigoto cada alelo recesivo puede aparecer en el genotipo de un hijo con baja probabilidad"}).json()
        assert r["correct"] and r["xp_awarded"] == 30 and "model_answer" in r
        again = c.post(url("ex_04"), json={"user": "Laeticia", "answer": r["model_answer"]}).json()
        assert again["xp_awarded"] == 0  # XP une seule fois
        assert c.post(f"/api/parcours/{pid}/metacognition", json={"user": "Laeticia", "confidence": 4}).json()["ok"]
        assert c.get("/sw.js").status_code == 200 and c.get("/labos/genetica_mendel.html").status_code == 200


def test_mode_test_ouvre_tous_les_parcours(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        assert len(c.get("/api/parcours", params={"user": "Maryse"}).json()) == 16
        monkeypatch.setenv("FUTURA_TEST_MODE", "1")
        lst = c.get("/api/parcours", params={"user": "Maryse"}).json()
        assert len(lst) == 32 and sum(p["category"] == "matematicas" for p in lst) == 16
        assert c.get("/api/parcours/mat_funcion_lineal", params={"user": "Maryse"}).status_code == 200


def test_ocho_parcours_de_matematicas_por_alumna():
    from app.content import category
    for user in ("Maryse", "Laeticia"):
        n = sum(1 for p in load().values() if p["target_user"] == user and category(p) == "matematicas")
        assert n == 8, (user, n)


def _parent_headers(c, monkeypatch):
    monkeypatch.setenv("FUTURA_PARENT_PIN", "9999")
    tok = c.post("/api/parent/login", json={"pin": "9999"}).json()["token"]
    return {"X-Futura-Token": tok}


def test_pin_eleve_y_panel_parent(monkeypatch):
    from fastapi.testclient import TestClient
    from app import security as sec
    from app.main import app
    with TestClient(app) as c:
        monkeypatch.setenv("FUTURA_PARENT_PIN", "9999")
        assert c.post("/api/parent/login", json={"pin": "0000"}).status_code == 401
        H = _parent_headers(c, monkeypatch)
        assert c.get("/api/parent/summary").status_code == 401                      # sin token
        try:
            assert c.post("/api/parent/pin", json={"user": "Maryse", "pin": "12"}, headers=H).status_code == 422
            assert c.post("/api/parent/pin", json={"user": "Maryse", "pin": "4321"}, headers=H).json()["has_pin"]
            assert c.get("/api/parcours", params={"user": "Maryse"}).status_code == 401
            assert c.post("/api/login", json={"user": "Maryse", "pin": "0000"}).status_code == 401
            t = c.post("/api/login", json={"user": "Maryse", "pin": "4321"}).json()["token"]
            T = {"X-Futura-Token": t}
            assert c.get("/api/parcours", params={"user": "Maryse"}, headers=T).status_code == 200
            assert c.get("/api/parcours", params={"user": "Laeticia"}, headers=T).status_code == 200   # Laeticia no tiene PIN
            ex = c.post("/api/parcours/mat_pitagoras/exercises/ex_01/check", json={"user": "Maryse", "answer": "10"})
            assert ex.status_code == 401                                              # tampoco se puede responder sin sesión
            assert c.post("/api/parcours/mat_pitagoras/exercises/ex_01/check", json={"user": "Maryse", "answer": "10"}, headers=T).json()["correct"]
            s = c.get("/api/parent/summary", headers=H).json()
            assert {x["name"] for x in s} == {"Maryse", "Laeticia"} and all(x["parcours"] for x in s)
            assert next(x for x in s if x["name"] == "Maryse")["has_pin"]
            assert c.post("/api/parent/pin", json={"user": "Maryse", "pin": "8765"}, headers=H).status_code == 200
            assert c.get("/api/parcours", params={"user": "Maryse"}, headers=T).status_code == 401   # cambiar el PIN cierra sesiones
        finally:
            c.post("/api/parent/pin", json={"user": "Maryse", "pin": None}, headers=H)
            sec._fails.clear()
        assert c.get("/api/parcours", params={"user": "Maryse"}).status_code == 200


def test_bloqueo_tras_cinco_intentos(monkeypatch):
    from fastapi.testclient import TestClient
    from app import security as sec
    from app.main import app
    with TestClient(app) as c:
        H = _parent_headers(c, monkeypatch)
        try:
            c.post("/api/parent/pin", json={"user": "Laeticia", "pin": "1111"}, headers=H)
            codes = [c.post("/api/login", json={"user": "Laeticia", "pin": "0000"}).status_code for _ in range(5)]
            assert codes == [401] * 5
            assert c.post("/api/login", json={"user": "Laeticia", "pin": "1111"}).status_code == 429   # bloqueada aunque acierte
        finally:
            c.post("/api/parent/pin", json={"user": "Laeticia", "pin": None}, headers=H)
            sec._fails.clear()


def test_espacio_parent_desactivado_sin_variable(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.delenv("FUTURA_PARENT_PIN", raising=False)
    with TestClient(app) as c:
        assert c.post("/api/parent/login", json={"pin": "1234"}).status_code == 403


def test_ocho_parcours_de_ciencias_por_alumna():
    from app.content import category
    for user in ("Maryse", "Laeticia"):
        n = sum(1 for p in load().values() if p["target_user"] == user and category(p) == "ciencias")
        assert n == 8, (user, n)


def test_cada_parcours_tiene_ficha_de_repaso_visual():
    for pid, p in load().items():
        r = p["revision"]
        assert len(r["mapa"]) >= 4 and all(len(x) <= 40 for x in r["mapa"]), pid       # cabe en el mapa mental
        assert len(r["tarjetas"]) >= 3 and r["formulas"] and r["errores"], pid


def test_contexto_tiene_texto_en_todos_los_parcours():
    for pid, p in load().items():
        c = p["contexte"]
        assert c["texte"].strip() and c["question_reflexion"].strip() and c["problema"].strip() and c["meta"].startswith("Al terminar"), pid
        assert c["question_reflexion"].rstrip().endswith(("?", ".")), pid


def test_prediccion_se_guarda_y_el_padre_la_ve(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        u, base = {"user": "Laeticia"}, "/api/parcours/mat_trigonometria"
        assert c.get(base, params=u).json()["prediction"] == ""
        assert c.post(base + "/prediction", json={**u, "text": "Creo que mide 20 m"}).json()["ok"]
        assert c.get(base, params=u).json()["prediction"] == "Creo que mide 20 m"
        c.post(base + "/prediction", json={**u, "text": "Mide más de 20 m"})
        assert c.get(base, params=u).json()["prediction"] == "Mide más de 20 m"        # se actualiza, no se duplica
        assert c.post("/api/parcours/mat_pitagoras/prediction", json={**u, "text": "x"}).status_code == 403
        assert c.post(base + "/metacognition", json={**u, "confidence": 4, "prediction_result": "mal"}).status_code == 422
        assert c.post(base + "/metacognition", json={**u, "confidence": 4, "comment": "bien", "prediction_result": "casi"}).json()["ok"]
        H = _parent_headers(c, monkeypatch)
        L = next(x for x in c.get("/api/parent/summary", headers=H).json() if x["name"] == "Laeticia")
        assert L["predictions"][0]["text"] == "Mide más de 20 m" and L["predictions"][0]["result"] == "casi"
