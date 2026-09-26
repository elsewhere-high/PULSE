"""Validate and summarize the canonical Chengdu coverage and LLM runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
from pathlib import Path


EXPECTED_AGENTS = 20_937_757
SEEDS = (42, 43, 44)
COVERAGE_NAMES = ("cov000", "cov030", "cov060", "cov100")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(rows: list[dict], key: str) -> float:
    return statistics.fmean(float(row[key]) for row in rows)


def extract(path: Path, kind: str, config: str, seed: int) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    totals = data["totals"]
    row = {
        "tag": data.get("tag") or path.parent.name,
        "kind": kind,
        "config": config,
        "seed": seed,
        "n_agents": int(totals["n_agents"]),
        "Safe15": float(totals["share_safe_by_15min"]),
        "Safe30": float(totals["share_safe_by_30min"]),
        "Safe60": float(totals["share_safe_by_60min"]),
        "Safe120": float(totals["share_safe_by_120min"]),
        "Queue_max": int(totals["queue_max"]),
        "Overflow": int(totals["overfilled_shelters"]),
        "EquityGap": float(totals["shelter_occupancy_gini"]),
        "sheltered": int(totals["sheltered"]),
        "shelter_utilisation": float(totals["shelter_utilisation"]),
        "median_walk_m": float(totals["median_dist_walked_m"]),
        "distinct_destinations": int(totals["distinct_destinations"]),
        "rethink_events": int(totals["rethink_events"]),
        "accounted": int(totals["accounted"]),
        "conservation_error": int(totals["conservation_error"]),
        "steps": int(data["steps"]),
        "wall_s": float(data.get("wall_s") or 0.0),
        "frac_knows_one": float(data.get("frac_knows_one") or 0.0),
        "broadcast_reach": float(data.get("broadcast_reach") or 0.0),
        "llm_enabled": bool(data.get("llm_enabled", False)),
        "summary_sha256": sha256(path),
        "summary_path": str(path),
    }
    if not (
        row["n_agents"] == EXPECTED_AGENTS
        and row["accounted"] == EXPECTED_AGENTS
        and row["conservation_error"] == 0
        and row["Overflow"] == 0
        and row["steps"] == 1080
    ):
        raise ValueError(f"Hard-gate failure in {path}")
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-dir", type=Path, required=True)
    parser.add_argument("--llm-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--population-cache", type=Path, required=True)
    parser.add_argument("--routing-cache", type=Path, required=True)
    parser.add_argument("--population-provenance", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for config in COVERAGE_NAMES:
        for seed in SEEDS:
            path = args.coverage_dir / f"c20_{config}_s{seed}" / "summary.json"
            rows.append(extract(path, "coverage", config, seed))
    for seed in SEEDS:
        path = args.llm_dir / f"c20_llm_s{seed}" / "summary.json"
        rows.append(extract(path, "llm", "llm", seed))

    dataset_path = args.output_dir / "analysis_dataset.csv"
    with dataset_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    grouped = {}
    for config in (*COVERAGE_NAMES, "llm"):
        selected = [row for row in rows if row["config"] == config]
        grouped[config] = {
            key: {
                "mean": mean(selected, key),
                "median": statistics.median(float(row[key]) for row in selected),
                "min": min(float(row[key]) for row in selected),
                "max": max(float(row[key]) for row in selected),
            }
            for key in (
                "Safe15", "Safe120", "Queue_max", "EquityGap", "sheltered",
                "shelter_utilisation", "median_walk_m", "distinct_destinations",
                "rethink_events",
            )
        }

    paired = []
    for seed in SEEDS:
        baseline = next(row for row in rows if row["config"] == "cov030" and row["seed"] == seed)
        llm = next(row for row in rows if row["config"] == "llm" and row["seed"] == seed)
        paired.append({
            "seed": seed,
            **{
                f"delta_{key}": float(llm[key]) - float(baseline[key])
                for key in (
                    "Safe15", "Safe120", "Queue_max", "EquityGap", "sheltered",
                    "shelter_utilisation", "median_walk_m", "distinct_destinations",
                    "rethink_events",
                )
            },
        })
    paired_path = args.output_dir / "paired_llm_effects.csv"
    with paired_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(paired[0]))
        writer.writeheader()
        writer.writerows(paired)

    coverage_effect = {
        key: grouped["cov100"][key]["mean"] - grouped["cov000"][key]["mean"]
        for key in grouped["cov000"]
    }
    llm_effect = {
        key.removeprefix("delta_"): statistics.fmean(row[key] for row in paired)
        for key in paired[0]
        if key.startswith("delta_")
    }
    result = {
        "schema_version": "1.0",
        "instance": "chengdu_census2020_worldpop_block_v1",
        "n_runs": len(rows),
        "hard_gates_passed": len(rows),
        "coverage_effect_cov100_minus_cov000": coverage_effect,
        "coverage_reversal": coverage_effect["Safe15"] * coverage_effect["Safe120"] < 0,
        "paired_llm_minus_cov030": llm_effect,
        "groups": grouped,
        "inputs": {
            "population_cache": {"path": str(args.population_cache), "sha256": sha256(args.population_cache)},
            "routing_cache": {"path": str(args.routing_cache), "sha256": sha256(args.routing_cache)},
            "population_provenance": {"path": str(args.population_provenance), "sha256": sha256(args.population_provenance)},
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "artifacts": {
            "analysis_dataset_sha256": sha256(dataset_path),
            "paired_llm_effects_sha256": sha256(paired_path),
        },
    }
    (args.output_dir / "effect_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "n_runs": result["n_runs"],
        "coverage_reversal": result["coverage_reversal"],
        "coverage_effect": coverage_effect,
        "llm_effect": llm_effect,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
