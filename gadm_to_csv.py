import json
import csv

# Charger le fichier GeoJSON
with open("gadm41_BEN_3.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extraire les informations
rows = []
for feature in data["features"]:
    props = feature["properties"]
    rows.append({
        "country": props.get("NAME_0"),
        "region": props.get("NAME_1"),
        "commune": props.get("NAME_2"),
        "arrondissement": props.get("NAME_3"),
    })

# Enregistrer dans un fichier CSV
with open("benin_administratif.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["country", "region", "commune", "arrondissement"])
    writer.writeheader()
    writer.writerows(rows)

print("✅ Fichier CSV généré : benin_administratif.csv")
