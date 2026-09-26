"""Run the canonical Chengdu 2020 census coverage matrix sequentially.

All configurations share one population cache and one routing cache.  The
only experimental change is the tied initial-knowledge/broadcast coverage
level.  Existing valid summaries are skipped so an interrupted matrix resumes
without overwriting completed runs.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import subprocess
import time
from pathlib import Path


PYTHON = sys.executable
SIMULATOR = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("PULSE_BASE", SIMULATOR / "data/chengdu_census2020/base"))
CACHE = Path(os.environ.get("PULSE_CACHE", SIMULATOR / "data/chengdu_census2020/chengdu_census2020_v1.npz"))
ROUTING = Path(os.environ.get("PULSE_ROUTING", SIMULATOR / "results/cache/chengdu_census2020_routing_v1.npz"))
OUTPUT = Path(os.environ.get("PULSE_COVERAGE_DIR", SIMULATOR / "results/chengdu_census2020/coverage_v1"))
LOG = OUTPUT / "matrix.log"
STEPS = 1080
SEEDS = (42, 43, 44)
COVERAGE = (0.0, 0.3, 0.6, 1.0)
EXPECTED_AGENTS = 20_937_757


def log(message: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def valid_summary(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        totals = data["totals"]
        return (
            int(totals["n_agents"]) == EXPECTED_AGENTS
            and int(totals["accounted"]) == EXPECTED_AGENTS
            and int(totals["conservation_error"]) == 0
            and int(totals["overfilled_shelters"]) == 0
            and int(data["steps"]) == STEPS
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    log("Canonical Chengdu coverage matrix: 4 levels x 3 seeds = 12 runs")
    started = time.time()
    failures: list[str] = []

    for coverage in COVERAGE:
        name = f"cov{int(round(coverage * 100)):03d}"
        for seed in SEEDS:
            tag = f"c20_{name}_s{seed}"
            run_dir = OUTPUT / tag
            summary = run_dir / "summary.json"
            if valid_summary(summary):
                log(f"SKIP {tag}: valid summary already exists")
                continue

            run_dir.mkdir(parents=True, exist_ok=True)
            command = [
                PYTHON,
                "scripts/bench_swarm.py",
                "--base", str(BASE),
                "--cache", str(CACHE),
                "--route-cache", str(ROUTING),
                "--run-dir", str(run_dir),
                "--steps", str(STEPS),
                "--warmup", "3",
                "--no-events",
                "--seed", str(seed),
                "--tag", tag,
                "--frac-knows-one", str(coverage),
                "--broadcast-reach", str(coverage),
            ]
            log(f"RUN {tag}: coverage={coverage:.1f}, seed={seed}")
            run_started = time.time()
            with (run_dir / "run.log").open("w", encoding="utf-8") as stream:
                process = subprocess.run(
                    command,
                    cwd=SIMULATOR,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            elapsed = time.time() - run_started
            if process.returncode or not valid_summary(summary):
                failures.append(tag)
                log(f"FAIL {tag}: rc={process.returncode}, elapsed={elapsed:.1f}s")
                continue
            totals = json.loads(summary.read_text(encoding="utf-8"))["totals"]
            log(
                f"OK {tag}: {elapsed:.1f}s, "
                f"Safe15={totals['share_safe_by_15min']:.6f}, "
                f"Safe120={totals['share_safe_by_120min']:.6f}, "
                f"Queue_max={totals['queue_max']}"
            )

    rows = []
    for coverage in COVERAGE:
        name = f"cov{int(round(coverage * 100)):03d}"
        for seed in SEEDS:
            tag = f"c20_{name}_s{seed}"
            summary = OUTPUT / tag / "summary.json"
            if not valid_summary(summary):
                continue
            data = json.loads(summary.read_text(encoding="utf-8"))
            totals = data["totals"]
            rows.append({
                "tag": tag,
                "coverage": coverage,
                "seed": seed,
                "n_agents": totals["n_agents"],
                "Safe15": totals["share_safe_by_15min"],
                "Safe30": totals["share_safe_by_30min"],
                "Safe60": totals["share_safe_by_60min"],
                "Safe120": totals["share_safe_by_120min"],
                "Queue_max": totals["queue_max"],
                "Overflow": totals["overfilled_shelters"],
                "EquityGap": totals["shelter_occupancy_gini"],
                "sheltered": totals["sheltered"],
                "shelter_utilisation": totals["shelter_utilisation"],
                "median_walk_m": totals["median_dist_walked_m"],
                "distinct_destinations": totals["distinct_destinations"],
                "rethink_events": totals["rethink_events"],
                "conservation_error": totals["conservation_error"],
                "wall_s": data.get("wall_s"),
            })

    if rows:
        table = OUTPUT / "matrix_results.csv"
        with table.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    log(
        f"DONE: valid={len(rows)}/12, failed={len(failures)}, "
        f"elapsed={(time.time() - started) / 60:.1f}min"
    )
    if failures or len(rows) != 12:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
