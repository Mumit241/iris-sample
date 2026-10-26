
from app.terrain.parcels import analyze_parcels
from app.terrain.export import (
    export_metrics_csv,
    export_metrics_geojson,
)

DEM = "fixtures/synthetic_dem.tif"
PARCELS = "fixtures/synthetic_parcels.geojson"

results = analyze_parcels(
    DEM,
    PARCELS,
    minimum_coverage=0.80,
    steep_threshold=10.0,
)

for parcel in results:
    print(parcel)

csv_path = export_metrics_csv(
    results,
    "outputs/parcel_metrics.csv",
)

geojson_path = export_metrics_geojson(
    results,
    PARCELS,
    "outputs/parcel_metrics.geojson",
)

print(f"CSV created: {csv_path}")
print(f"GeoJSON created: {geojson_path}")
