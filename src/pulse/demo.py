"""Small synthetic city inputs for PULSE's optional city simulator."""

from pathlib import Path

import numpy as np


def city_arrays():
    """Return a 4 × 4 grid with 1,600 residents and 960 shelter places."""
    side = 4
    x, y = np.meshgrid(np.arange(side), np.arange(side))
    lon = x.ravel().astype(np.float64) * 200.0 / 111_320.0
    lat = y.ravel().astype(np.float64) * 200.0 / 110_540.0
    neighbours = np.full((side * side, 4), -1, dtype=np.int32)
    for row in range(side):
        for col in range(side):
            adjacent = [(row + dr, col + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))]
            ids = [r * side + c for r, c in adjacent if 0 <= r < side and 0 <= c < side]
            neighbours[row * side + col, :len(ids)] = ids
    return {
        "lon": lon, "lat": lat,
        "pop": np.full(side * side, 100.0),
        "area": np.full(side * side, 40_000.0),
        "neigh": neighbours,
        "deg": (neighbours >= 0).sum(axis=1).astype(np.int32),
        "s_lon": lon.copy(), "s_lat": lat.copy(),
        "s_cap": np.full(side * side, 60.0),
    }


def write_city_cache(path: Path) -> None:
    """Write a synthetic cache without overwriting an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        np.savez(stream, **city_arrays())
