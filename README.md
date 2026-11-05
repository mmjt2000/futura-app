# Futura — application familiale d'apprentissage (Maryse et Laeticia)

## Lancer
```bash
python3.12 -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
export FUTURA_PARENT_PIN=1234        # Windows PowerShell : $env:FUTURA_PARENT_PIN="1234"
uvicorn app.main:app --reload        # http://127.0.0.1:8000
pytest                               # 15 tests
```

## Pages
- `/` : application des élèves (choix de l'élève, PIN si défini).
- `/parent` : espace parent (code `FUTURA_PARENT_PIN`) : progression, tentatives, réflexions, gestion des PIN.
- `/docs` : documentation de l'API.

## Variables d'environnement
| Variable | Rôle |
|---|---|
| `FUTURA_PARENT_PIN` | Code de l'espace parent. Sans cette variable, l'espace parent est désactivé. |
| `FUTURA_TEST_MODE=1` | Chaque élève voit tous les parcours (pour tester). |
| `FUTURA_SECRET` | Clé de signature des sessions (sinon générée dans `data/.secret`). |

## Contenu
`data/parcours.json` est la source de vérité (32 parcours). Au démarrage, chaque parcours est validé :
schéma complet, 4 processus PISA dans le carnet, exercices de niveau 1 à 4, rubrique du niveau 4, laboratoire existant.
Les laboratoires sont dans `labos/` ; ceux de maths utilisent le kit `static/tp.js` + `static/tp.css`.

## Repaso visual
Chaque parcours a une fiche de révision (clé `revision` dans `parcours.json`) : idée clé, carte mentale,
formules, astuces, erreurs fréquentes et cartes à retourner. L'élève l'ouvre avec le bouton « 📚 Repaso visual »
et peut l'imprimer (les réponses des cartes apparaissent alors). Le serveur refuse de démarrer si une fiche est incomplète.

## Contexte et prédiction
Chaque parcours s'ouvre sur : une scène réelle (`texte`), le problème à résoudre (`problema`), un petit tableau de données (`dato`),
une question de prédiction (`question_reflexion`) et un objectif (`meta`). L'élève écrit sa prédiction, elle est enregistrée sur le serveur,
puis ressort en fin de parcours (Metacognición) où elle dit si elle avait raison. L'espace parent affiche prédictions et bilan.

## Sécurité
- PIN élève : 4 à 8 chiffres, stocké haché (PBKDF2 + sel). Session de 12 h, invalidée si le PIN change.
- Blocage de 5 minutes après 5 erreurs de code (élève ou parent).
- Les bonnes réponses ne sont jamais envoyées au navigateur avant d'être trouvées.
- Ne pas exposer l'application sur Internet sans HTTPS.
