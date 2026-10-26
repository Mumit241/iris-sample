from rasterio.transform import array_bounds

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from shapely.geometry import shape, box

from app.terrain.slope import calculate_slope


def analyze_parcels(
    dem_path,
    parcels_path,
    minimum_coverage=0.80,
    steep_threshold=10.0,
):
    """Calculate parcel-level terrain statistics.

    Assumptions:
    - DEM horizontal and vertical units are metres.
    - Slope values are expressed in degrees.
    - Parcel geometries are transformed into DEM CRS.
    - Coverage includes areas outside the DEM footprint.
    - Parcels with insufficient coverage require review.
    """

    if not 0 < minimum_coverage <= 1:
        raise ValueError(
            "minimum_coverage must be between 0 and 1."
        )

    if not np.isfinite(steep_threshold) or steep_threshold < 0:
        raise ValueError(
            "steep_threshold must be a non-negative number."
        )

    # Step 1: Calculate the DEM slope raster
    slope = calculate_slope(dem_path)

    # Step 2: Read the DEM metadata
    with rasterio.open(dem_path) as src:
        dem_crs = src.crs
        transform = src.transform
        height, width = src.shape
        bounds = src.bounds

    # DEM footprint polygon
    dem_footprint = box(
        bounds.left,
        bounds.bottom,
        bounds.right,
        bounds.top,
    )

    # Step 3: Read parcel GeoJSON
    with Path(parcels_path).open(
        "r", encoding="utf-8"
    ) as f:
        geojson = json.load(f)

    if geojson.get("type") != "FeatureCollection":
        raise ValueError(
            "Expected a GeoJSON FeatureCollection."
        )

    # Standard GeoJSON defaults to EPSG:4326.
    # Our synthetic fixture explicitly declares EPSG:32632.
    crs_info = geojson.get("crs")
    parcel_crs = (
        crs_info.get("properties", {}).get("name")
        if crs_info
        else "EPSG:4326"
    )

    if not parcel_crs:
        raise ValueError(
            "Invalid parcel CRS declaration."
        )

    results = []

    # Step 4: Process individual parcels
    for feature in geojson["features"]:

        parcel_id = feature["properties"]["parcel_id"]
        geom = feature["geometry"]

        # Reproject parcel geometry when CRS differs
        if parcel_crs != str(dem_crs):
            geom = transform_geom(
                parcel_crs,
                dem_crs,
                geom,
            )

        # Step 5: Convert geometry to Shapely
        parcel_geometry = shape(geom)

        if (
            parcel_geometry.is_empty
            or not parcel_geometry.is_valid
            or parcel_geometry.area <= 0
        ):
            raise ValueError(
                f"Invalid parcel geometry: {parcel_id}"
            )

        # Step 6: Calculate footprint intersection
        parcel_area = parcel_geometry.area

        intersection_area = (
            parcel_geometry.intersection(
                dem_footprint
            ).area
        )

        footprint_share = (
            intersection_area / parcel_area
        )

        # Step 7: Identify DEM pixels inside parcel
        inside = geometry_mask(
            [geom],
            out_shape=(height, width),
            transform=transform,
            invert=True,
            all_touched=False,
        )

        count_inside = int(
            np.count_nonzero(inside)
        )

        # Parcel entirely outside DEM or too small
        # to contain a sampled raster pixel
        if count_inside == 0:
            results.append({
                "parcel_id": parcel_id,
                "median_slope_deg": None,
                "p90_slope_deg": None,
                "max_slope_deg": None,
                "coverage": 0.0,
                "nodata_share": 1.0,
                "status": "REVIEW_REQUIRED",
            })
            continue

        # Step 8: Extract slope values
        selected = slope[inside]

        valid = selected[
            np.isfinite(selected)
        ]

        internal_coverage = (
            len(valid) / count_inside
        )

        # Step 9: Include outside-DEM area
        coverage = (
            internal_coverage * footprint_share
        )

        coverage = float(
            np.clip(coverage, 0.0, 1.0)
        )

        nodata_share = 1.0 - coverage

        # Step 10: Terrain classification
        if (
            coverage < minimum_coverage
            or len(valid) == 0
        ):
            status = "REVIEW_REQUIRED"

            # Do not present incomplete terrain
            # statistics as reliable assessments.
            median_slope = None
            p90_slope = None
            max_slope = None

        else:
            median_slope = float(
                np.median(valid)
            )

            p90_slope = float(
                np.percentile(valid, 90)
            )

            max_slope = float(
                np.max(valid)
            )

            if p90_slope >= steep_threshold:
                status = "STEEP"
            else:
                status = "PASS"

        # Step 11: Store parcel metrics
        results.append({
            "parcel_id": parcel_id,
            "median_slope_deg": median_slope,
            "p90_slope_deg": p90_slope,
            "max_slope_deg": max_slope,
            "coverage": coverage,
            "nodata_share": nodata_share,
            "status": status,
        })

    return results

