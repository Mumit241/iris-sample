# PROJECT IRIS — Engineering Notes

**Assessment:** IRIS-48H-09 — DEM-Based Parcel Slope and Terrain Quality Checks  
**Branch:** `feature/iris-48h-09-terrain`  
**Scope:** One synthetic DEM and four synthetic parcels; independently executable, no production services required.

## 1. Engineering objective and boundary

The adapter demonstrates a reproducible path from a single-band elevation GeoTIFF to parcel-level slope screening metrics and human-review statuses. The components described in the assessment implementation are `app/terrain/slope.py`, `parcels.py`, `export.py`, and `obstacles.py`, with generated fixtures under `fixtures/` and tests under `tests/`.

This is a **screening aid**, not an engineering certification or automated obstacle detection system. It does not evaluate access routes, vehicle turn radii, geotechnical stability, construction suitability, or logistics feasibility. No live IRIS database, secrets, or external elevation downloads are needed.

## 2. Source provenance and licence limits

- The 100 × 100 elevation raster and parcel geometries are **synthetic and programmatically generated** by the submitted fixture scripts.
- No third-party DEM, parcel dataset, imagery, API, or real-world coordinates are required to reproduce the assessment.
- The declared raster CRS is EPSG:32632, with artificial test coordinates near the coordinate origin. Those coordinates are outside the normal geographic area of use of that UTM zone; transformed longitude/latitude coordinates in example GeoJSON **must not be treated as real sites**.
- Rasterio, NumPy, Shapely, PyProj, and Pytest are third-party dependencies with their own licence terms. Use and redistribution must respect those terms. The original IRIS repository's licence and reuse permissions require separate verification; ownership of the assessment code does not authorize deployment into production.

## 3. Horizontal CRS and vertical reference assumptions

The slope module requires a projected, metre-based horizontal CRS and a north-up, unrotated raster with square pixels. The sample DEM is 10 m/pixel. It explicitly rejects geographic angular coordinates for slope mathematics rather than interpreting degrees as metres; mixed parcel CRS is transformed into the DEM CRS before spatial analysis. The export module converts polygon geometry to standard GeoJSON longitude/latitude (EPSG:4326) and omits the legacy GeoJSON `crs` member.

Elevations are **assumed to be in metres**, but the synthetic fixture has **no defined vertical datum**. No vertical unit conversion, geoid transformation, or reconciliation of DEM and survey vertical datums is implemented. For real terrain, source metadata and vertical reference compatibility must be checked before computation. Horizontal and vertical values must have compatible linear units to yield meaningful slopes.

## 4. Slope method and edge treatment

The slope raster uses a Horn 3 × 3 finite-difference gradient. For an interior cell with a complete valid neighbourhood, horizontal/vertical derivatives are formed from weighted neighbouring elevations and converted to slope in degrees:

\[
\theta = \arctan\left(\sqrt{(\partial z/\partial x)^2 + (\partial z/\partial y)^2}\right)\frac{180}{\pi}.
\]

The planar synthetic DEM is `z(x,y) = 100 + 0.1x + 0.05y` metres, with theoretical slope approximately **6.37937°**. The declared acceptance tolerance in the synthetic slope test is **±0.01°**.

Source nodata, nonfinite elevations, outer DEM edges, and pixels lacking a complete valid 3 × 3 neighbourhood are **unassessed** (`NaN`) rather than assigned zero slope. This is conservative: the set of valid *slope* cells is smaller than the set of valid *elevation* cells. Slope on an interpolated or incompletely supported neighbourhood is deliberately not estimated.

## 5. Parcel intersection, statistics, and coverage

Each parcel geometry is reprojected to the DEM CRS for analysis. For coverage, the current pilot intersects the parcel polygon with valid slope-cell polygons and sums intersection areas:

\[
C = \frac{\sum\limits_{i\in\text{valid slope cells}} \operatorname{Area}(P\cap R_i)}{\operatorname{Area}(P)}.
\]

This accounts for partial boundary pixels and areas outside the raster footprint. A narrow-parcel regression test checks that a polygon can have valid coverage even when it contains no raster pixel centres.

**Critical distinction:** the coverage calculation is area-weighted, but **median, P90, and maximum slope are currently calculated from selected raster slope values, not from fully area-weighted quantiles**. The selection logic uses intersected/touched cells; a tiny sliver of cell may influence these statistics as much as a substantially overlapping cell. Those statistics should not be described as area-weighted. If area-proportional quantiles are required, compute a cell-intersection-area weight per selected value and use a documented weighted-percentile definition.

The exported `nodata_share` in the current pilot is `1 - valid_slope_coverage`. It therefore means **unassessed parcel slope area**, which may include original DEM nodata, neighbourhood-edge invalidity, and terrain outside the DEM. It is **not** solely the share of original source DEM nodata cells. A production output should expose separate fields for `source_dem_nodata_share`, `slope_unassessed_share`, and `outside_dem_share` if downstream consumers need to distinguish causes.

## 6. Classification and safe uncertainty behaviour

The demonstration runner applies `minimum_coverage = 0.80` and `steep_threshold = 10.0` degrees, using parcel P90 slope for steepness classification once coverage is sufficient:

- **`REVIEW_REQUIRED`**: coverage below 80%, or no usable slope values; median/P90/max are emitted as null rather than implying a reliable parcel assessment.
- **`STEEP`**: sufficiently covered and P90 slope is at least 10°.
- **`PASS`**: sufficiently covered and P90 slope is below 10°.

These threshold values are **illustrative, configurable screening defaults**, not validated access-risk limits. `PASS` is not a finding of safe access or buildability. A `REVIEW_REQUIRED` result must never be replaced with `PASS` solely because the small assessed portion appears flat.

The obstacle-note model supports `parcel_id`, `obstacle_type`, `review_note`, `review_status`, and `reviewer_id`. Blank values and `NOT_REVIEWED` mean that **no visual assessment has been performed**, not that obstacles are absent. The model is available as a human-review schema but is not an obstacle-detection algorithm or a verified reviewer workflow.

## 7. Outputs and fixture observations

The standalone runner is `check_parcels.py`; it writes:

- `outputs/parcel_metrics.csv` — one metrics record per synthetic parcel.
- `outputs/parcel_metrics.geojson` — parcel geometries in EPSG:4326 with attached metrics and nulls for unassessed statistics.

The user's reported fixture results after the area-intersection correction were:

| Parcel | Valid slope coverage | Status | Reported median slope |
|---|---:|---|---:|
| P001 | 100.00% | PASS | 6.37937° |
| P002 | 53.76% | REVIEW_REQUIRED | null |
| P003 | 31.36% | REVIEW_REQUIRED | null |
| P004 | 0.00% | REVIEW_REQUIRED | null |

These are **synthetic results**, not geographic assessments. The sample CRS transformation and four GeoJSON features were manually checked. They should not be used as authoritative coordinates or suitability decisions.

## 8. Tests and reproducibility

On **Windows / Python 3.14.0 / Pytest 9.1.1**, the user reported running:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/
```

The last reported summary was **`14 passed in 12.88s`**, with the Git working tree clean after commit `56d25bf` at that point. This is user-reported evidence from the development environment, **not an independently repeated clean-install verification**. The test suite exercises planar slope and nodata, CRS rejection/reprojection, insufficient coverage, configurable thresholds, narrow parcels, obstacle note defaults, and CSV/GeoJSON outputs.

To reproduce from the repository root on Windows, first install the documented dependencies into `.venv`, then run:

```powershell
.\.venv\Scripts\python.exe fixtures/create_synthetic_dem.py
.\.venv\Scripts\python.exe fixtures/create_parcels.py
.\.venv\Scripts\python.exe check_parcels.py
.\.venv\Scripts\python.exe -m pytest -q tests/
```

Test evidence should be regenerated for the **final** commit, and an independent clean environment should be checked before claiming fully reproducible installation.

## 9. Trade-offs and non-goals

| Decision | Benefit | Limitation / next step |
|---|---|---|
| Horn 3 × 3, complete valid neighbourhood | Simple, testable, conservative nodata behaviour | Edge cells become unassessed; other terrain derivatives not provided |
| Reject unsupported DEM geometry/units | Avoids silently incorrect gradient mathematics | Does not handle angular-unit rasters or rotated grids without preprocessing |
| Exact polygon–cell intersection for coverage | Handles partial coverage and narrow parcels | Python-level polygon intersections can be slow for larger rasters |
| Touched-cell slope statistics | Simple and compatible with small test fixture | Median/P90 are not area-weighted; small slivers can affect results |
| Null statistics for low coverage | Prevents false reassurance from incomplete DEMs | Partial measurements are deliberately withheld from final metrics |
| Separate obstacles schema | Leaves room for auditable human review | Does not collect evidence or identify physical obstacles automatically |
| No production IRIS dependencies | Reproducible, safe evaluation | No live database or end-to-end Stage 4 integration has been demonstrated |

### Performance path for future integration

The present pilot performs polygon-cell intersections over valid slope cells, suitable for a small raster and handful of parcels. A scaled implementation should restrict intersection candidates to each parcel's raster window, use bounding-box/geometry prefilters or spatial indexing, and benchmark runtime and memory. It should not silently substitute pixel-centre coverage for fractional-area coverage in cases where boundary precision matters.

### Additional QA before operational use

- Validate geometry emptiness/self-intersections and reject malformed CRS declarations.
- Check duplicate parcel identifiers and output/geometry alignment.
- Distinguish source nodata, algorithm-edge invalidity, and out-of-footprint area.
- Introduce area-weighted parcel percentiles if needed by the decision specification.
- Test concave and multipart parcels, holes, very small parcels, and parcels wholly outside the DEM.
- Test missing/malformed DEM vertical metadata and non-metric units.
- Define a formal configuration/data contract and QA acceptance rules for the existing IRIS pipeline.
- Confirm output schema compatibility with downstream consumers and document any transformation accuracy constraints.

## 10. Safe integration recommendation

Keep the adapter isolated under `app/terrain/` until maintainers approve a concrete integration point. Pass fixture or authorized DEM/parcel paths explicitly; avoid reading credentials, writing to live databases, or modifying pipeline state. Validate input CRS and vertical metadata before processing, treat review flags as blocking until assessed, and record data provenance, software versions, thresholds, and test execution details with each run.

The pilot demonstrates the core raster/parcel screening workflow within the assessment's limited scope. **Deployment, reuse, access-risk interpretation, and integration into IRIS Stage 4 require separate review and agreement.**
