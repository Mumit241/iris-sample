
import csv
import json
from pathlib import Path


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
    """Attach calculated metrics to parcel geometries."""

    with Path(parcels_path).open(
        "r", encoding="utf-8"
    ) as file:
        parcels = json.load(file)

    metrics_by_id = {
        result["parcel_id"]: result
        for result in results
    }

    for feature in parcels["features"]:
        parcel_id = feature["properties"]["parcel_id"]

        if parcel_id not in metrics_by_id:
            raise ValueError(
                f"Missing metrics for {parcel_id}"
            )

        feature["properties"].update(
            metrics_by_id[parcel_id]
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    with output_path.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(parcels, file, indent=2)

    return output_path
