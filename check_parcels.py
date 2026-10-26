
from app.terrain.parcels import analyze_parcels

results = analyze_parcels(
    "fixtures/synthetic_dem.tif",
    "fixtures/synthetic_parcels.geojson",
    minimum_coverage=0.80,
    steep_threshold=10.0,
)

for parcel in results:
    print(parcel)
