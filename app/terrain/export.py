
import csv
import json
from pathlib import Path

from rasterio.warp import transform_geom


def export_metrics_csv(results, output_path):
    """Export parcel terrain statistics to CSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    fields = [
        "parcel_id",
        "median_slope_deg",
        "p90_slope_deg",
        "max_slope_deg",
        "coverage",
        "nodata_share",
        "status",
    ]

    with output_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(results)

    return output_path


def export_metrics_geojson(
    results,
    parcels_path,
    output_path,
):
    """Export parcel metrics as EPSG:4326 GeoJSON."""

    with Path(parcels_path).open(
        "r", encoding="utf-8"
    ) as file:
        parcels = json.load(file)

    source_crs = (
        parcels.get("crs", {})
        .get("properties", {})
        .get("name", "EPSG:4326")
    )

    metrics_by_id = {
        result["parcel_id"]: result
        for result in results
    }

    exported_features = []

    for feature in parcels["features"]:
        parcel_id = feature["properties"]["parcel_id"]

        if parcel_id not in metrics_by_id:
            raise ValueError(
                f"Missing metrics for {parcel_id}"
            )

        geometry = feature["geometry"]

        # Standard GeoJSON uses longitude/latitude.
        if source_crs != "EPSG:4326":
            geometry = transform_geom(
                source_crs,
                "EPSG:4326",
                geometry,
            )

        properties = {
            **feature["properties"],
            **metrics_by_id[parcel_id],
        }

        exported_features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": geometry,
        })

    exported = {
        "type": "FeatureCollection",
        "features": exported_features,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    with output_path.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(exported, file, indent=2)

    return output_path
