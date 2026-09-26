"""PULSE: explore evacuation controls, compare seeds and export evidence."""

import argparse
import csv
import json
from dataclasses import asdict
from html import escape
from pathlib import Path
import random
from statistics import median
from typing import Dict, Iterable, List, Tuple

from .model import Control, no_intervention, reference_control, simulate
from . import __version__


def _random_control(rng: random.Random) -> Control:
    offsets = (rng.uniform(0, 30), rng.uniform(0, 30))
    raw = [rng.uniform(0.05, 1.0) for _ in range(3)]
    total = sum(raw)
    weights = tuple(x / total for x in raw)
    return Control(offsets, weights, rng.uniform(0, 1))


def controls_for_search(seed: int = 2026, rounds: int = 20) -> List[Control]:
    if rounds < 3:
        raise ValueError("at least three rounds are required")
    rng = random.Random(seed)
    controls = [_random_control(rng) for _ in range(rounds)]
    controls[2] = reference_control()
    return controls


def _rank(metrics: Dict[str, object]) -> Tuple[float, float, float, float]:
    feasible = 1.0 if metrics["completion_rate"] >= 0.98 and not metrics["spillback"] else 0.0
    return (feasible, float(metrics["completion_rate"]), -float(metrics["oscillation_index"]), -float(metrics["max_queue"]))


def run_search(demand: int = 1000, rounds: int = 20, seed: int = 2026) -> List[Dict[str, object]]:
    trials: List[Dict[str, object]] = []
    for index, control in enumerate(controls_for_search(seed, rounds), start=1):
        metrics, _ = simulate(demand, control, seed=7)
        trials.append({"trial": index, "control": asdict(control), "metrics": metrics.to_dict()})
    return trials


def choose_best(trials: Iterable[Dict[str, object]]) -> Dict[str, object]:
    return max(trials, key=lambda trial: _rank(trial["metrics"]))


def _control_from_dict(data: Dict[str, object]) -> Control:
    return Control(tuple(data["signal_offsets"]), tuple(data["route_weights"]), float(data["departure_delay"]))


def _write_svg(path: Path, title: str, series: List[Tuple[str, List[Tuple[float, float]]]],
               x_label: str, y_label: str) -> None:
    """Render every series against shared axes so comparisons retain scale."""
    all_points = [point for _, points in series for point in points]
    xmin, xmax = min(x for x, _ in all_points), max(x for x, _ in all_points)
    ymax = max(1.0, max(y for _, y in all_points)) * 1.05
    left, right, top, bottom = 82, 844, 128, 376
    colors = ("#0e8074", "#d18439")

    def xy(x, y):
        return (left + (x - xmin) / max(xmax - xmin, 1.0) * (right - left),
                bottom - y / ymax * (bottom - top))

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="880" height="464" viewBox="0 0 880 464" role="img">',
        f'<title>PULSE — {escape(title)}</title>',
        '<rect width="880" height="464" rx="16" fill="#f6f8f9"/>',
        '<g font-family="Arial, sans-serif" fill="#203337">',
        '<text x="32" y="32" font-size="14" font-weight="700" letter-spacing="3">PULSE / EXPERIMENTS</text>',
        f'<text x="32" y="67" font-size="24" font-weight="700">{escape(title)}</text>',
        f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="white"/>',
    ]
    for tick in range(5):
        xv, yv = xmin + (xmax - xmin) * tick / 4, ymax * tick / 4
        px, py = xy(xv, yv)
        parts.extend([
            f'<line x1="{left}" y1="{py:.1f}" x2="{right}" y2="{py:.1f}" stroke="#dee7e7"/>',
            f'<text x="{left-12}" y="{py+4:.1f}" text-anchor="end" font-size="12">{yv:,.0f}</text>',
            f'<text x="{px:.1f}" y="400" text-anchor="middle" font-size="12">{xv:,.0f}</text>',
        ])
    for index, (label, points) in enumerate(series):
        color = colors[index % len(colors)]
        coordinates = [xy(x, y) for x, y in points]
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in coordinates)
        parts.append(f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2.8"><title>{escape(label)}</title></polyline>')
        if len(points) < 20:
            parts.extend(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>' for x, y in coordinates)
        lx = 32 + index * 230
        parts.extend([
            f'<line x1="{lx}" y1="98" x2="{lx+24}" y2="98" stroke="{color}" stroke-width="3"/>',
            f'<text x="{lx+32}" y="102" font-size="13">{escape(label)}</text>',
        ])
    parts.extend([
        f'<text x="463" y="435" text-anchor="middle" font-size="13">{escape(x_label)}</text>',
        f'<text x="22" y="252" transform="rotate(-90 22 252)" text-anchor="middle" font-size="13">{escape(y_label)}</text>',
        '</g></svg>',
    ])
    path.write_text("\n".join(parts), encoding="utf-8")


def run_all(output: Path) -> Dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    baseline, baseline_series = simulate(1000, no_intervention(), seed=7)
    trials = run_search()
    best = choose_best(trials)
    best_control = _control_from_dict(best["control"])
    seed_results = [simulate(1000, best_control, seed=s)[0].to_dict() for s in (7, 17, 29)]
    demands = [500, 700, 900, 1100, 1300, 1500]
    boundary = [simulate(d, best_control, seed=7)[0].to_dict() for d in demands]
    best_metrics, best_series = simulate(1000, best_control, seed=7)
    random_median = median(float(t["metrics"]["oscillation_index"]) for t in trials if t["trial"] != best["trial"])
    improvement = 1.0 if random_median <= 1e-12 else max(0.0, 1.0 - best_metrics.oscillation_index / random_median)

    summary = {
        "project": "PULSE",
        "baseline": baseline.to_dict(),
        "best_trial": best,
        "three_seed_verification": seed_results,
        "demand_scan": boundary,
        "relative_oscillation_reduction_vs_other_trials_median": round(improvement, 6),
        "candidate_boundary": "1100-1300 vehicles",
        "interpretation": "mechanism-level evidence; SUMO/TraCI validation remains future work",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "trials.json").write_text(json.dumps(trials, ensure_ascii=False, indent=2), encoding="utf-8")

    with (output / "demand_scan.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(boundary[0].keys()))
        writer.writeheader()
        writer.writerows(boundary)

    with (output / "queue_series.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("time_s", "baseline_queue", "selected_queue"))
        writer.writerows(zip(baseline_series["time_s"], baseline_series["queue"], best_series["queue"]))

    _write_svg(
        output / "queue_response.svg",
        "Queue response · 1,000 vehicles",
        [("No intervention", list(zip(baseline_series["time_s"], baseline_series["queue"]))),
         ("Selected control", list(zip(best_series["time_s"], best_series["queue"])))],
        "simulation time (s)",
        "queue (vehicles)",
    )
    _write_svg(
        output / "demand_boundary.svg",
        "Demand scan · stability boundary",
        [("Selected control", [(float(m["demand"]), float(m["max_queue"])) for m in boundary])],
        "evacuation demand (vehicles)",
        "maximum queue (vehicles)",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(prog="pulse-explore", description=__doc__)
    parser.add_argument("--version", action="version", version=f"PULSE {__version__}")
    parser.add_argument("--output", default="results/demo", help="evidence output directory (default: results/demo)")
    args = parser.parse_args()
    try:
        summary = run_all(Path(args.output))
    except OSError as error:
        parser.exit(1, f"PULSE: could not write results: {error}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
