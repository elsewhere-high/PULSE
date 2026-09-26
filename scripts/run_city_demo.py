"""Run PULSE's synthetic 1,600-resident city demo on the CPU."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pulse.demo import write_city_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/city_demo")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pulse_city_") as folder:
        cache = Path(folder) / "synthetic_city.npz"
        write_city_cache(cache)
        subprocess.run([
            sys.executable, str(ROOT / "scripts/bench_swarm.py"),
            "--device", "cpu", "--cache", str(cache),
            "--route-cache", str(Path(folder) / "routing.npz"),
            "--run-dir", str(output), "--steps", "180", "--warmup", "3",
            "--profile-every", "30", "--profile-after", "30",
            "--no-events", "--seed", "42", "--tag", "pulse_synthetic_demo",
            "--frames-every", "30", "--traj3d-every", "30", "--traj3d-n", "100",
        ], check=True, cwd=ROOT)
    report = json.loads((output / "summary.json").read_text())
    totals = report["totals"]
    if (totals["n_agents"] != 1600 or totals["accounted"] != 1600
            or totals["conservation_error"] != 0 or totals["overfilled_shelters"] != 0):
        raise RuntimeError("PULSE city demo failed its population/capacity checks")
    print(f"PULSE city demo passed: 1,600 residents; output: {output}")


if __name__ == "__main__":
    main()
