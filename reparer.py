import json

try:
    with open('data/parcours.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("✅ Le fichier JSON est déjà valide ! Aucune réparation nécessaire.")
except json.JSONDecodeError as e:
    print(f"❌ Erreur trouvée : {e}")
    print("Tentative de réparation...")
    
    # On lit le contenu brut
    with open('data/parcours.json', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # On essaie de corriger les virgules manquantes entre les objets
    # (C'est une réparation simple qui marche souvent)
    import re
    content = re.sub(r'\}\s*\{', '},{', content)
    
    # On essaie de recharger
    try:
        data = json.loads(content)
        # Si ça marche, on sauvegarde
        with open('data/parcours.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ Réparation réussie ! Le fichier a été sauvegardé.")
    except json.JSONDecodeError as e2:
        print(f"❌ La réparation simple n'a pas suffi. Erreur : {e2}")
        print("Il faut vérifier manuellement le fichier.")