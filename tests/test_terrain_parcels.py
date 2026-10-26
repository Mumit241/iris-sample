
import json

import numpy as np
import pytest
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely import transform

from app.terrain.parcels import analyze_parcels


DEM_PATH = "fixtures/synthetic_dem.tif"
PARCEL_PATH = "fixtures/synthetic_parcels.geojson"


def test_insufficient_coverage():
    """Poor coverage must require human review."""
    results = analyze_parcels(DEM_PATH, PARCEL_PATH)

    by_id = {
        result["parcel_id"]: result
        for result in results
    }

    assert by_id["P001"]["status"] == "PASS"

    for parcel_id in ("P002", "P003", "P004"):
        parcel = by_id[parcel_id]

        assert parcel["status"] == "REVIEW_REQUIRED"
        assert parcel["coverage"] < 0.80
        assert parcel["median_slope_deg"] is None
        assert parcel["p90_slope_deg"] is None
        assert parcel["max_slope_deg"] is None


def test_mixed_crs_reprojection(tmp_path):
    """Equivalent parcel geometries in different CRSs
    should produce matching terrain metrics.
    """
    with open(PARCEL_PATH, encoding="utf-8") as file:
        data = json.load(file)

    # Convert synthetic EPSG:32632 parcel coordinates
    # into EPSG:4326 for the mixed-CRS test.
    transformer = Transformer.from_crs(
        "EPSG:32632",
        "EPSG:4326",
        always_xy=True,
    )

    for feature in data["features"]:
        geom = shape(feature["geometry"])
        converted = transform(geom, transformer.transform, interleaved=False)
        feature["geometry"] = mapping(converted)

    # Standard GeoJSON coordinates are EPSG:4326.
    data.pop("crs", None)

    converted_path = tmp_path / "parcels_4326.geojson"

    with open(converted_path, "w", encoding="utf-8") as file:
        json.dump(data, file)

    original = analyze_parcels(DEM_PATH, PARCEL_PATH)
    converted = analyze_parcels(DEM_PATH, converted_path)

    assert len(original) == len(converted)

    for a, b in zip(original, converted):
        assert a["parcel_id"] == b["parcel_id"]
        assert a["status"] == b["status"]
        assert a["coverage"] == pytest.approx(
            b["coverage"], abs=0.01
        )

        if a["median_slope_deg"] is not None:
            assert a["median_slope_deg"] == pytest.approx(
                b["median_slope_deg"], abs=0.01
            )


def test_configurable_coverage_threshold():
    """Increasing the coverage requirement
    must never turn a review parcel into PASS.
    """
    results = analyze_parcels(
        DEM_PATH,
        PARCEL_PATH,
        minimum_coverage=0.95,
    )

    for result in results:
        if result["coverage"] < 0.95:
            assert result["status"] == "REVIEW_REQUIRED"


def test_invalid_coverage_threshold():
    """Reject impossible configuration values."""
    with pytest.raises(ValueError):
        analyze_parcels(
            DEM_PATH,
            PARCEL_PATH,
            minimum_coverage=1.5,
        )

def test_narrow_parcel_coverage(tmp_path):
    """A narrow parcel intersecting valid DEM cells
    must not automatically receive zero coverage.
    """
    import json
    from shapely.geometry import box, mapping

    # Narrow polygon inside the valid part of the DEM.
    # Width 2 m, compared with a 10 m raster cell.
    polygon = box(201, 101, 203, 151)

    fixture = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "EPSG:32632"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"parcel_id": "NARROW001"},
                "geometry": mapping(polygon),
            }
        ],
    }

    path = tmp_path / "narrow_parcel.geojson"

    with path.open("w", encoding="utf-8") as file:
        json.dump(fixture, file)

    results = analyze_parcels(DEM_PATH, path)

    assert len(results) == 1
    assert results[0]["coverage"] > 0
