"""Run three paired LLM-leader trials on canonical Chengdu census 2020."""

from __future__ import annotations

import json
import os
import sys
import subprocess
import time
import urllib.request
from pathlib import Path


PYTHON = sys.executable
SIMULATOR = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("PULSE_BASE", SIMULATOR / "data/chengdu_census2020/base"))
CACHE = Path(os.environ.get("PULSE_CACHE", SIMULATOR / "data/chengdu_census2020/chengdu_census2020_v1.npz"))
ROUTING = Path(os.environ.get("PULSE_ROUTING", SIMULATOR / "results/cache/chengdu_census2020_routing_v1.npz"))
BASELINES = Path(os.environ.get("PULSE_COVERAGE_DIR", SIMULATOR / "results/chengdu_census2020/coverage_v1"))
OUTPUT = Path(os.environ.get("PULSE_LLM_DIR", SIMULATOR / "results/chengdu_census2020/llm_v1"))
LOG = OUTPUT / "llm_matrix.log"
SEEDS = (42, 43, 44)
EXPECTED_AGENTS = 20_937_757


def log(message: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def load_valid(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    totals = data["totals"]
    if not (
        int(totals["n_agents"]) == EXPECTED_AGENTS
        and int(totals["accounted"]) == EXPECTED_AGENTS
        and int(totals["conservation_error"]) == 0
        and int(totals["overfilled_shelters"]) == 0
        and int(data["steps"]) == 1080
    ):
        raise ValueError(f"Invalid summary: {path}")
    return data


def require_server() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"llama.cpp health returned {response.status}")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    require_server()
    log("Canonical Chengdu paired LLM matrix: coverage=0.3, seeds=42/43/44")
    failures = []
    for seed in SEEDS:
        baseline_path = BASELINES / f"c20_cov030_s{seed}" / "summary.json"
        load_valid(baseline_path)
        tag = f"c20_llm_s{seed}"
        run_dir = OUTPUT / tag
        summary_path = run_dir / "summary.json"
        if summary_path.exists():
            try:
                load_valid(summary_path)
                log(f"SKIP {tag}: valid summary already exists")
                continue
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass

        run_dir.mkdir(parents=True, exist_ok=True)
        command = [
            PYTHON,
            "scripts/bench_swarm.py",
            "--base", str(BASE),
            "--cache", str(CACHE),
            "--route-cache", str(ROUTING),
            "--run-dir", str(run_dir),
            "--steps", "1080",
            "--warmup", "3",
            "--no-events",
            "--seed", str(seed),
            "--tag", tag,
            "--frac-knows-one", "0.3",
            "--broadcast-reach", "0.3",
            "--leader-comm", "0.5",
            "--llm-interval-min", "10",
            "--llm-slots", "32",
            "--vram-fraction", "0.72",
            "--llm",
        ]
        log(f"RUN {tag}: paired against c20_cov030_s{seed}")
        started = time.time()
        with (run_dir / "run.log").open("w", encoding="utf-8") as stream:
            process = subprocess.run(
                command,
                cwd=SIMULATOR,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        elapsed = time.time() - started
        try:
            data = load_valid(summary_path)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            data = None
        if process.returncode or data is None:
            failures.append(tag)
            log(f"FAIL {tag}: rc={process.returncode}, elapsed={elapsed:.1f}s")
            continue
        totals = data["totals"]
        llm = data.get("llm", {})
        log(
            f"OK {tag}: {elapsed / 60:.1f}min, "
            f"Safe15={totals['share_safe_by_15min']:.6f}, "
            f"Safe120={totals['share_safe_by_120min']:.6f}, "
            f"applied_share={llm.get('applied_share')}"
        )

    log(f"DONE: valid={len(SEEDS)-len(failures)}/3, failed={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
