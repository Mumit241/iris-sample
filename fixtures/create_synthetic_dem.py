
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin

# Synthetic fixture: no real-world location is represented.
size = 100
resolution = 10.0  # metres per pixel
nodata = -9999.0

# Pixel centre coordinates in a projected metric CRS
rows, cols = np.indices((size, size))
x = (cols + 0.5) * resolution
y = (size - rows - 0.5) * resolution

# Known planar surface: z = 100 + 0.1x + 0.05y
elevation = 100.0 + 0.1 * x + 0.05 * y
elevation = elevation.astype("float32")

# A small deliberately missing-data region
elevation[30:45, 40:55] = nodata

output = Path(__file__).parent / "synthetic_dem.tif"

# Coordinates are synthetic but use metric EPSG:32632 conventions.
transform = from_origin(0, size * resolution,
                        resolution, resolution)

with rasterio.open(
    output,
    "w",
    driver="GTiff",
    height=size,
    width=size,
    count=1,
    dtype="float32",
    crs="EPSG:32632",
    transform=transform,
    nodata=nodata,
) as dst:
    dst.write(elevation, 1)

print(f"Created DEM: {output}")
print(f"Raster shape: {size} x {size}")
print("Resolution: 10 metres")
print("CRS: EPSG:32632 (synthetic coordinates)")
print("Horizontal units: metres")
print("Vertical units: assumed metres")
print("Vertical datum: undefined (synthetic)")
print("Expected planar slope: approx. 6.38 degrees")
