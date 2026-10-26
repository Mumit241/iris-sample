# PROJECT IRIS — DEM-Based Parcel Slope and Terrain Quality Checks

**Task ID:** IRIS-48H-09  
**Stream:** Geo / Terrain  
**Development branch:** `feature/iris-48h-09-terrain`  
**Base repository:** https://github.com/amaurisantosjr/iris-sample

## Overview

This self-contained assessment adapter reads a synthetic single-band DEM, calculates slope in degrees, summarizes terrain for parcel polygons, flags areas with insufficient valid slope coverage, and exports CSV and GeoJSON. It is designed to run without project production data, databases, APIs, or credentials.

### Assessment files

```text
app/terrain/
  __init__.py
  slope.py
  parcels.py
  export.py
  obstacles.py
fixtures/
  create_synthetic_dem.py
  synthetic_dem.tif
  create_parcels.py
  synthetic_parcels.geojson
tests/
  test_terrain_slope.py
  test_terrain_parcels.py
  test_terrain_export.py
  test_obstacles.py
outputs/
  parcel_metrics.csv
  parcel_metrics.geojson
check_parcels.py
terrain_test_results.txt
README_IRIS_48H_09.md
```

The base repository's `README.md` remains unchanged. The listed files reflect the assessment workflow reported during development; verify the file list against the final Git checkout.

## Environment and installation

**Verified test environment (reported by the candidate):** Windows, Python **3.14.0**, Pytest **9.1.1**. Other Python versions and operating systems have not been verified for this assessment.

Obtain the assessment branch from the submitted fork/remote, not just the upstream default branch:

```powershell
git clone <SUBMITTED_REPOSITORY_URL>
cd iris-sample
git switch feature/iris-48h-09-terrain
```

Replace `<SUBMITTED_REPOSITORY_URL>` with the actual submitted repository URL. If delivering a ZIP, extract it and open PowerShell in the extracted `iris-sample` folder instead.

Install the isolated environment with [uv](https://docs.astral.sh/uv/) (Python 3.14 must be available):

```powershell
uv venv --python 3.14 .venv
uv pip install --python .\.venv\Scripts\python.exe numpy rasterio shapely pyproj pytest
.\.venv\Scripts\python.exe --version
```

These are the **standalone assessment** dependencies; installing the full IRIS application is not required to execute the synthetic DEM workflow. For final release, pin package versions in the dependency lockfile or record actual installed versions.

## Reproduce fixtures and outputs

Run from the **repository root**:

```powershell
.\.venv\Scripts\python.exe fixtures/create_synthetic_dem.py
.\.venv\Scripts\python.exe fixtures/create_parcels.py
.\.venv\Scripts\python.exe check_parcels.py
```

Outputs:

- `outputs/parcel_metrics.csv` — one record per parcel.
- `outputs/parcel_metrics.geojson` — geometries with parcel metrics in standard longitude/latitude (EPSG:4326).

Inspect the CSV:

```powershell
Import-Csv .\outputs\parcel_metrics.csv | Format-Table
```

## DEM fixture and CRS / unit assumptions

The synthetic DEM uses a **100 × 100** pixel float32 GeoTIFF with **10 m** square pixels and a generated planar elevation surface:

\[
z(x,y) = 100 + 0.1x + 0.05y
\]

Its theoretical slope is

\[
\theta = \arctan(\sqrt{0.1^2 + 0.05^2}) \approx 6.37937^\circ.
\]

- Horizontal CRS: **EPSG:32632**; horizontal unit **metres**.
- Vertical unit: **assumed metres**; **vertical datum undefined** (synthetic fixture).
- Nodata sentinel: **−9999**; a 15 × 15 cell gap (225 cells) is inserted.
- Geographic coordinates are **fabricated for computation**, not surveyed real-world parcels. The synthetic projected coordinates are outside the usual geographic applicability of UTM zone 32N. Exported latitude/longitude coordinates are likewise **not real sites**.

The slope module requires a projected metre-based CRS, north-up nonrotated square pixels, and a complete valid 3 × 3 neighbourhood. It rejects incompatible raster geometry or horizontal units rather than silently treating angular degrees as metres. Because vertical units are assumed, no elevation-unit conversion or vertical datum transformation is performed.

## Slope and parcel analysis

`app/terrain/slope.py` applies a Horn 3 × 3 weighted elevation gradient, then calculates slope in degrees:

\[
\theta = \frac{180}{\pi}\arctan\left(\sqrt{(\partial z/\partial x)^2+(\partial z/\partial y)^2}\right).
\]

The outer raster edge and pixels with incomplete or invalid neighbourhoods are **unassessed** (`NaN`).

`app/terrain/parcels.py` transforms parcel geometries into the DEM CRS, intersects parcel polygons with valid slope raster cells, and computes:

- `median_slope_deg`, `p90_slope_deg`, `max_slope_deg`
- `coverage` (fraction of parcel area overlapping **valid computed slope cells**)
- `nodata_share` (implemented as **1 − coverage**, i.e. *unassessed slope area*, not strictly raw DEM nodata)
- `status` (`PASS`, `STEEP`, or `REVIEW_REQUIRED`)

**Demonstration thresholds:** `minimum_coverage=0.80`; `steep_threshold=10.0` degrees, based on parcel P90. If coverage is below threshold or no usable slope exists, return `REVIEW_REQUIRED` and null parcel slope statistics. Otherwise, P90 at least 10° produces `STEEP`; lower values produce `PASS`. These are **illustrative screening settings, not engineering-approved site suitability standards**.

Area-based intersection is used to avoid overlooking parcels partly outside the raster or narrow parcels with no raster cell centres inside them. **Coverage is area-weighted, but the slope median/P90/max are based on selected slope samples; they are not area-weighted percentiles.** This distinction should be accounted for before using the adapter for production decisions.

### Recorded fixture results

| Parcel | Median slope | Coverage | Status |
|---|---:|---:|---|
| P001 | 6.37937° | 100% | PASS |
| P002 | Unassessed | 53.76% | REVIEW_REQUIRED |
| P003 | Unassessed | 31.36% | REVIEW_REQUIRED |
| P004 | Unassessed | 0% | REVIEW_REQUIRED |

These values were reported from the local synthetic fixture run, not from a production site. `PASS` means passing this limited slope and coverage screen only; it does **not** establish feasible access, obstacle clearance, or construction suitability.

## Exports and human obstacle review

`app/terrain/export.py` writes CSV and GeoJSON. The GeoJSON exporter converts the synthetic fixture coordinates from EPSG:32632 to EPSG:4326 and omits the legacy `crs` member. Null slope metrics remain null in GeoJSON (and blank in CSV).

`app/terrain/obstacles.py` provides a **schema for human visual-review notes**, e.g.:

```json
{
  "parcel_id": "P003",
  "obstacle_type": null,
  "review_note": null,
  "review_status": "NOT_REVIEWED",
  "reviewer_id": null
}
```

A null obstacle value signifies **not reviewed**, not “no obstacle”. This is a standalone review-note schema; automated obstacle detection and UI workflow integration are outside the slice.

## Automated acceptance tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/
```

**Last reported local result:** `14 passed in 12.88s` on Windows / Python 3.14.0 / Pytest 9.1.1. Re-run after any subsequent code change and preserve the final terminal output; this README does not claim an independent clean-machine test.

Test coverage includes:

1. Planar-surface theoretical slope within tolerance.
2. Nodata and neighbouring invalid cells excluded.
3. Geographic CRS rejected for slope calculation.
4. Mixed parcel/DEM CRSs reprojected consistently.
5. Poor-coverage parcels remain `REVIEW_REQUIRED`.
6. Configurable/invalid coverage thresholds.
7. Narrow parcel intersecting valid pixels even without pixel centres.
8. Default unreviewed obstacle-note schema.
9. CSV/GeoJSON records, identifiers, review statuses, null metrics and coordinate transformation.

## Trade-offs and limitations

- This is a **single small synthetic DEM** and handful of parcels, not bulk raster tiling, large-site optimization, or full geotechnical validation.
- Full per-cell polygon intersections are relatively expensive for larger rasters; limit candidate cells to parcel windows or use a more scalable fractional coverage algorithm in production.
- Edge and nodata halo cells have invalid slope under the complete-neighbourhood policy; coverage refers to valid **slope** availability, not necessarily source elevation availability.
- No explicit vertical datum, z-unit inference, slope uncertainty propagation or DEM resolution suitability assessment is provided.
- Current slope statistics use selected samples, not weighted quantiles by polygon–pixel overlap area.
- EPSG:32632 assignment is a computational test convention; coordinates must not be interpreted as valid real-world sites.
- Obstacle detection, access geometry, logistics turn-radius validation, and deployment integration are outside scope.
- Optional hillshade has not been implemented in the described assessment workflow.

## Data provenance, licensing and safe integration

Fixture elevations and parcel shapes are generated programmatically for testing; no external, scraped, unlicensed, or real-world coordinates are needed. Python dependencies retain their respective open-source licences. Verify the upstream IRIS repository licence and any contribution/reuse terms separately.

The adapter sits in `app/terrain/` and can be integrated only after validating IRIS's backend interfaces, CRS and vertical datum conventions, source data permissions, error handling, and expected data contracts. The current slice does **not** access production databases, secrets, or live pipelines.

## Submission checklist

- Source: `app/terrain/`, `check_parcels.py`
- Fixtures and generation scripts: `fixtures/`
- Tests: `tests/test_terrain_*`, `tests/test_obstacles.py`
- Outputs: `outputs/parcel_metrics.csv`, `outputs/parcel_metrics.geojson`
- Documentation: this README and a separate engineering note if requested
- Confirm all tests pass in the final checkout; include the **actual final commit hash**, public readable GitHub branch/PR URL or ZIP, and final command output.

**Note:** This assessment README documents the standalone vertical slice. The original repository README remains the reference for the full IRIS application.
