
import numpy as np
import pytest
import rasterio

from app.terrain.slope import calculate_slope


DEM_PATH = "fixtures/synthetic_dem.tif"


def test_synthetic_planar_slope():
    """A planar DEM must return the theoretical slope."""
    slope = calculate_slope(DEM_PATH)

    expected = np.degrees(
        np.arctan(np.hypot(0.1, 0.05))
    )

    valid = slope[np.isfinite(slope)]

    assert valid.size > 0
    assert np.allclose(valid, expected, atol=0.01)


def test_nodata_cells_excluded():
    """Nodata cells must never produce valid slopes."""
    slope = calculate_slope(DEM_PATH)

    with rasterio.open(DEM_PATH) as src:
        dem = src.read(1, masked=True)
        nodata_mask = np.ma.getmaskarray(dem)

    assert nodata_mask.sum() == 225
    assert np.all(np.isnan(slope[nodata_mask]))


def test_neighbours_of_nodata_excluded():
    """A missing elevation invalidates its 3x3 neighbourhood."""
    slope = calculate_slope(DEM_PATH)

    # The known nodata block is rows 30:45, cols 40:55.
    # The surrounding one-pixel halo is also unassessed.
    assert np.all(np.isnan(slope[29:46, 39:56]))


def test_reject_geographic_crs(tmp_path):
    """Geographic degree-based DEMs must be rejected."""
    path = tmp_path / "geographic_dem.tif"

    with rasterio.open(DEM_PATH) as src:
        profile = src.profile.copy()
        elevation = src.read(1)

    profile.update(crs="EPSG:4326")

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(elevation, 1)

    with pytest.raises(ValueError, match="projected CRS"):
        calculate_slope(path)
