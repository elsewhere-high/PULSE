"""Build a census-constrained Chengdu cache on one frozen geometry.

The source cache is already clipped to the fixed 20-district boundary.  This
script preserves every geometry, topology, shelter and capacity array and only
replaces the per-block population.  District totals are apportioned with the
Hamilton (largest-remainder) method so materialising one agent per integer
person preserves every district target and the city total exactly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_targets(path: Path) -> dict[int, int]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    targets = {
        int(row["adcode"]): int(row["population_2020_census"])
        for row in rows
    }
    if len(rows) != 20 or len(targets) != 20:
        raise ValueError(f"Expected 20 unique district rows, found {len(targets)}")
    return targets


def apportion(weights: np.ndarray, target: int, global_indices: np.ndarray) -> np.ndarray:
    if target < 0:
        raise ValueError("Population target cannot be negative")
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Population weights must be finite and non-negative")
    total = float(weights.sum())
    if target and total <= 0:
        raise ValueError("A positive district target has no positive block weight")
    if target == 0:
        return np.zeros(weights.shape, dtype=np.int64)

    exact = weights / total * target
    allocated = np.floor(exact).astype(np.int64)
    remaining = int(target - int(allocated.sum()))
    if remaining:
        fractional = exact - allocated
        # Primary key: descending fractional remainder.  Tie-break: ascending
        # original block index, which makes the build deterministic.
        order = np.lexsort((global_indices, -fractional))
        allocated[order[:remaining]] += 1
    if int(allocated.sum()) != target:
        raise AssertionError("Hamilton apportionment did not preserve the target")
    return allocated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--census-csv", type=Path, required=True)
    parser.add_argument("--output-cache", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--boundary", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    for output in (args.output_cache, args.provenance):
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {output}; pass --overwrite")
        output.parent.mkdir(parents=True, exist_ok=True)

    source = np.load(args.source_cache)
    required = {
        "lon", "lat", "pop", "area", "neigh", "deg",
        "s_lon", "s_lat", "s_cap", "district", "adcode",
    }
    missing = required - set(source.files)
    if missing:
        raise KeyError(f"Source cache is missing arrays: {sorted(missing)}")

    n_blocks = len(source["pop"])
    district = source["district"].astype(np.int64, copy=False)
    adcodes = source["adcode"].astype(np.int64, copy=False)
    if district.shape != (n_blocks,):
        raise ValueError("district array must have one value per block")
    if district.min() < 0 or district.max() >= len(adcodes):
        raise ValueError("district array contains an invalid district index")

    targets = load_targets(args.census_csv)
    if set(map(int, adcodes)) != set(targets):
        raise ValueError("Cache adcodes and census adcodes do not match exactly")

    source_pop = source["pop"].astype(np.float64, copy=False)
    population = np.zeros(n_blocks, dtype=np.int64)
    district_report = []
    for district_index, adcode_raw in enumerate(adcodes):
        adcode = int(adcode_raw)
        indices = np.flatnonzero(district == district_index)
        target = targets[adcode]
        allocated = apportion(source_pop[indices], target, indices)
        population[indices] = allocated
        district_report.append({
            "district_index": district_index,
            "adcode": adcode,
            "blocks": int(len(indices)),
            "source_weight_sum": float(source_pop[indices].sum()),
            "census_target": target,
            "allocated_population": int(allocated.sum()),
            "scale_factor": target / float(source_pop[indices].sum()),
        })

    city_total = int(population.sum())
    census_total = int(sum(targets.values()))
    if city_total != census_total:
        raise AssertionError(f"City total mismatch: {city_total} != {census_total}")

    output_arrays = {name: source[name] for name in source.files}
    output_arrays["pop"] = population.astype(np.float64)
    temporary = args.output_cache.with_name(args.output_cache.name + ".tmp.npz")
    np.savez(temporary, **output_arrays)
    temporary.replace(args.output_cache)

    written = np.load(args.output_cache)
    unchanged = {}
    for name in source.files:
        if name == "pop":
            continue
        unchanged[name] = bool(np.array_equal(source[name], written[name], equal_nan=True))
    if not all(unchanged.values()):
        raise AssertionError("A non-population source array changed")

    report = {
        "schema_version": "1.0",
        "instance": "chengdu_census2020_worldpop_block_v1",
        "method": (
            "2020 seventh-census district totals constrained exactly; "
            "within-district weights inherited from the WorldPop-derived "
            "population of the frozen administrative-boundary block cache; "
            "Hamilton largest-remainder integer apportionment"
        ),
        "limitations": [
            "Block populations are model inputs, not census counts at block level.",
            "Within-district weights inherit uncertainty from WorldPop and road-enclosed block coverage.",
            "The fixed 20-district boundary file is hash-pinned and is not claimed as a survey-grade cadastral boundary.",
            "Shelter capacities are scenario inputs and are not claimed as an official capacity inventory.",
        ],
        "source_cache": {
            "path": str(args.source_cache),
            "sha256": sha256(args.source_cache),
            "source_population": float(source_pop.sum()),
        },
        "census": {
            "path": str(args.census_csv),
            "sha256": sha256(args.census_csv),
            "districts": len(targets),
            "city_total": census_total,
        },
        "boundary": ({
            "path": str(args.boundary),
            "sha256": sha256(args.boundary),
        } if args.boundary else None),
        "output_cache": {
            "path": str(args.output_cache),
            "sha256": sha256(args.output_cache),
            "n_blocks": n_blocks,
            "n_agents": city_total,
            "n_shelters": int(len(written["s_cap"])),
            "shelter_capacity": float(written["s_cap"].sum()),
            "all_non_population_arrays_unchanged": all(unchanged.values()),
        },
        "district_validation": district_report,
    }
    args.provenance.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["output_cache"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
