
import csv
import json

import pytest
from rasterio.warp import transform_geom
from shapely.geometry import shape

from app.terrain.parcels import analyze_parcels
from app.terrain.export import (
    export_metrics_csv,
    export_metrics_geojson,
)


DEM = "fixtures/synthetic_dem.tif"
PARCELS = "fixtures/synthetic_parcels.geojson"


@pytest.fixture
def results():
    return analyze_parcels(
        DEM,
        PARCELS,
        minimum_coverage=0.80,
        steep_threshold=10.0,
    )


def test_csv_export(tmp_path, results):
    path = tmp_path / "metrics.csv"
    export_metrics_csv(results, path)

    assert path.exists()

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 4
    assert {
        "parcel_id", "median_slope_deg",
        "p90_slope_deg", "max_slope_deg",
        "coverage", "nodata_share", "status"
    }.issubset(reader.fieldnames)

    p003 = next(
        row for row in rows if row["parcel_id"] == "P003"
    )
    assert p003["status"] == "REVIEW_REQUIRED"
    assert p003["median_slope_deg"] == ""
    assert float(p003["coverage"]) < 0.80


def test_geojson_export(tmp_path, results):
    path = tmp_path / "metrics.geojson"
    export_metrics_geojson(results, PARCELS, path)

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 4
    assert "crs" not in data

    features = {
        f["properties"]["parcel_id"]: f
        for f in data["features"]
    }

    p003 = features["P003"]
    assert p003["properties"]["status"] == "REVIEW_REQUIRED"
    assert p003["properties"]["median_slope_deg"] is None


def test_geojson_coordinates_reprojected(tmp_path, results):
    path = tmp_path / "metrics.geojson"
    export_metrics_geojson(results, PARCELS, path)

    with open(PARCELS, encoding="utf-8") as f:
        source = json.load(f)

    with path.open(encoding="utf-8") as f:
        exported = json.load(f)

    original_geom = source["features"][0]["geometry"]
    expected_geom = transform_geom(
        "EPSG:32632", "EPSG:4326", original_geom
    )

    actual = shape(exported["features"][0]["geometry"])
    expected = shape(expected_geom)

    assert actual.equals_exact(expected, tolerance=1e-8)


def test_csv_preserves_all_parcel_ids(tmp_path, results):
    path = tmp_path / "metrics.csv"
    export_metrics_csv(results, path)

    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert {r["parcel_id"] for r in rows} == {
        "P001", "P002", "P003", "P004"
    }
