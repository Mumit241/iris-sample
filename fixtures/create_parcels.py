
import json
from pathlib import Path
from shapely.geometry import box, mapping

# Synthetic parcel coordinates in EPSG:32632.
# These are test coordinates, not real properties.

parcels = [
    {
        "id": "P001",
        "geometry": box(100, 100, 300, 300)
    },
    {
        "id": "P002",
        "geometry": box(350, 500, 600, 750)
    },
    {
        "id": "P003",
        "geometry": box(850, 850, 1100, 1100)
    },
    {
        "id": "P004",
        "geometry": box(400, 550, 550, 700)
    }
]

features = []

for parcel in parcels:
    features.append({
        "type": "Feature",
        "properties": {
            "parcel_id": parcel["id"]
        },
        "geometry": mapping(parcel["geometry"])
    })

geojson = {
    "type": "FeatureCollection",
    "name": "synthetic_parcels",
    "crs": {
        "type": "name",
        "properties": {
            "name": "EPSG:32632"
        }
    },
    "features": features
}

output = Path(__file__).parent / "synthetic_parcels.geojson"

with output.open("w", encoding="utf-8") as f:
    json.dump(geojson, f, indent=2)

print(f"Created: {output}")
print(f"Total parcels: {len(features)}")
