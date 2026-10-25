
from pathlib import Path

import numpy as np
import rasterio


def calculate_slope(dem_path: str | Path) -> np.ndarray:
    """Calculate Horn 3x3 slope in degrees.

    Assumptions:
    - Projected CRS with horizontal units in metres.
    - Elevation values in metres.
    - North-up raster with square pixels.
    - A complete valid 3x3 neighbourhood is required.
    """
    with rasterio.open(dem_path) as src:
        if src.count != 1:
            raise ValueError("Expected a single-band DEM.")

        crs = src.crs
        if crs is None or not crs.is_projected:
            raise ValueError(
                "DEM requires a projected CRS."
            )

        unit_factor = crs.linear_units_factor
        if (
            unit_factor is None
            or not np.isclose(unit_factor[1], 1.0)
        ):
            raise ValueError(
                "DEM horizontal units must be metres."
            )

        t = src.transform
        if not np.isclose(t.b, 0) or not np.isclose(t.d, 0):
            raise ValueError(
                "Rotated or sheared DEMs are not supported."
            )

        dx = abs(t.a)
        dy = abs(t.e)
        if (
            dx <= 0
            or dy <= 0
            or not np.isclose(dx, dy)
            or t.a <= 0
            or t.e >= 0
        ):
            raise ValueError(
                "DEM must be north-up with square metric pixels."
            )

        dem = src.read(1, masked=True)
        z = np.asarray(
            dem.astype("float64").filled(np.nan),
            dtype=np.float64,
        )

    # Prevent nonfinite elevations from entering slope math.
    z[~np.isfinite(z)] = np.nan

    # Outer raster border is unassessed.
    p = np.pad(z, 1, constant_values=np.nan)

    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]

    dzdx = (
        (c + 2 * f + i) - (a + 2 * d + g)
    ) / (8 * dx)

    dzdy = (
        (g + 2 * h + i) - (a + 2 * b + c)
    ) / (8 * dy)

    slope = np.degrees(
        np.arctan(np.hypot(dzdx, dzdy))
    )

    # An invalid cell or neighbour makes slope unassessed.
    slope[~np.isfinite(z)] = np.nan
    return slope.astype("float32")
