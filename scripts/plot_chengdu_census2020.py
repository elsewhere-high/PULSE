"""Create publication-ready figures for the canonical Chengdu V2 evidence.

Inputs are the committed 15-run analysis table and paired LLM effects.  The
figures deliberately show seed ranges and keep early safety, late safety,
congestion, and equity separate rather than collapsing them into one score.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DATASET = RESULTS / "analysis_dataset.csv"
PAIRED = RESULTS / "paired_effects.csv"
RAW = RESULTS / "runs_raw"
OUT = ROOT / "results/figures"

NAVY = "#203337"
BLUE = "#0E8074"
CYAN = "#65A9AB"
GREEN = "#517F4F"
RED = "#D94B55"
ORANGE = "#D18439"
GRAY = "#66778F"
LIGHT = "#E9EEF5"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.labelcolor": NAVY,
        "axes.edgecolor": LIGHT,
        "xtick.color": GRAY,
        "ytick.color": GRAY,
        "text.color": NAVY,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def grouped(rows: list[dict[str, str]], field: str):
    configs = ["c20_cov000", "c20_cov030", "c20_cov060", "c20_cov100"]
    values = []
    for config in configs:
        values.append(np.array([float(r[field]) for r in rows if r["config"] == config]))
    return configs, values


def mean_range(values: list[np.ndarray]):
    mean = np.array([v.mean() for v in values])
    low = mean - np.array([v.min() for v in values])
    high = np.array([v.max() for v in values]) - mean
    return mean, np.vstack([low, high])


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.text(0.01, -0.085, "PULSE / Recorded sample analysis · Chengdu census 2020",
             fontsize=9, color=GRAY)
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_coverage(rows: list[dict[str, str]]) -> None:
    coverage_rows = [r for r in rows if r["caliber"] == "chengdu_census2020"
                     and r["config"].startswith("c20_cov")]
    x = np.array([0, 30, 60, 100])
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.1), gridspec_kw={"wspace": 0.34})

    _, early = grouped(coverage_rows, "Safe15")
    _, late = grouped(coverage_rows, "Safe120")
    for vals, color, label in [(early, BLUE, "Safe15"), (late, GREEN, "Safe120")]:
        mean, err = mean_range(vals)
        axes[0].errorbar(x, mean * 100, yerr=err * 100, marker="o", lw=2.8,
                         ms=7, capsize=4, color=color, label=label)
    axes[0].set_title("Safety improves, then saturates")
    axes[0].set_xlabel("Information coverage (%)")
    axes[0].set_ylabel("Residents safe (%)")
    axes[0].legend(frameon=False, loc="lower right")

    _, queue = grouped(coverage_rows, "Queue_max")
    qmean, qerr = mean_range(queue)
    axes[1].errorbar(x, qmean / 1e6, yerr=qerr / 1e6, marker="o", lw=2.8,
                     ms=7, capsize=4, color=RED)
    axes[1].set_title("Peak rejected arrivals rise")
    axes[1].set_xlabel("Information coverage (%)")
    axes[1].set_ylabel("Queue_max (million people)")

    _, equity = grouped(coverage_rows, "EquityGap")
    emean, eerr = mean_range(equity)
    axes[2].errorbar(x, emean, yerr=eerr, marker="o", lw=2.8,
                     ms=7, capsize=4, color=ORANGE)
    axes[2].set_title("Equity optimum is intermediate")
    axes[2].set_xlabel("Information coverage (%)")
    axes[2].set_ylabel("Shelter occupancy Gini (lower is better)")

    for ax in axes:
        ax.grid(axis="y", color=LIGHT, lw=1)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xticks(x)
    fig.suptitle("Canonical Chengdu · 20,937,757 agents · 3 seeds per configuration",
                 fontsize=18, fontweight="bold", color=NAVY, y=1.02)
    fig.text(0.5, -0.02,
             "Coverage 0→100%: Safe15 +2.142 pp; Safe120 +0.307 pp; Queue_max +2.861M; no sign reversal.",
             ha="center", fontsize=12.5, color=NAVY, fontweight="bold")
    save(fig, "fig_c20_coverage.png")


def plot_llm(paired: list[dict[str, str]]) -> None:
    paired = [r for r in paired if r["caliber"] == "chengdu_census2020"
              and r["config"] == "c20_llm"]
    metrics = [
        ("d_Safe15", "Safe15", 100, "pp"),
        ("d_Safe120", "Safe120", 100, "pp"),
        ("d_shelter_util", "Shelter\nutilisation", 100, "pp"),
        ("d_EquityGap", "EquityGap", 1, "Gini"),
    ]
    means = [np.mean([float(r[key]) for r in paired]) * scale for key, _, scale, _ in metrics]
    lows = [m - min(float(r[key]) * scale for r in paired) for m, (key, _, scale, _) in zip(means, metrics)]
    highs = [max(float(r[key]) * scale for r in paired) - m for m, (key, _, scale, _) in zip(means, metrics)]
    labels = [m[1] for m in metrics]
    colors = [RED if v < 0 else ORANGE for v in means]

    llm_stats = []
    for seed in (42, 43, 44):
        with (RAW / f"c20_llm_s{seed}.json").open(encoding="utf-8") as stream:
            llm_stats.append(json.load(stream)["llm"])

    fig, axes = plt.subplots(1, 2, figsize=(15.2, 5.2), gridspec_kw={"width_ratios": [1.35, 1]})
    xpos = np.arange(len(labels))
    axes[0].bar(xpos, means, color=colors, width=0.64)
    axes[0].errorbar(xpos, means, yerr=np.vstack([lows, highs]), fmt="none",
                     ecolor=NAVY, capsize=4, lw=1.5)
    axes[0].axhline(0, color=NAVY, lw=1)
    axes[0].set_xticks(xpos, labels)
    axes[0].set_title("Paired effect: LLM − no leader")
    axes[0].set_ylabel("Percentage points, except EquityGap (Gini)")
    for x, value in zip(xpos, means):
        axes[0].text(x, value + (0.35 if value >= 0 else -0.35), f"{value:+.3f}",
                     ha="center", va="bottom" if value >= 0 else "top", fontweight="bold")

    gate_labels = ["Parsed", "Applied", "Grammar", "No full-shelter\ndirection"]
    gate_values = [
        1 - np.mean([s["unparseable_replies"] / s["calls"] for s in llm_stats]),
        np.mean([s["applied_share"] for s in llm_stats]),
        np.mean([s["grammar_share"] for s in llm_stats]),
        1 - np.mean([s["sent_to_full_share"] for s in llm_stats]),
    ]
    axes[1].barh(np.arange(4), np.array(gate_values) * 100, color=GREEN, height=0.58)
    axes[1].set_yticks(np.arange(4), gate_labels)
    axes[1].set_xlim(0, 105)
    axes[1].set_xlabel("Successful checks (%)")
    axes[1].set_title("Execution validity: 100%")
    axes[1].invert_yaxis()
    for i, value in enumerate(gate_values):
        axes[1].text(value * 100 - 1.5, i, f"{value*100:.0f}%", ha="right", va="center",
                     color="white", fontweight="bold")

    for ax in axes:
        ax.grid(axis="y" if ax is axes[0] else "x", color=LIGHT, lw=1, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Valid actions do not guarantee effective coordination",
                 fontsize=18, fontweight="bold", color=NAVY, y=1.02)
    fig.text(0.5, -0.02,
             "All 3 seeds agree: Safe120 −1.456 pp, 304k fewer sheltered, EquityGap +0.0856.",
             ha="center", fontsize=12.5, color=NAVY, fontweight="bold")
    save(fig, "fig_c20_llm_validity.png")


def plot_mechanism(paired: list[dict[str, str]]) -> None:
    paired = [r for r in paired if r["caliber"] == "chengdu_census2020"
              and r["config"] == "c20_llm"]
    specs = [
        ("d_walk_median_m", "Median walk", 1, "m"),
        ("d_n_destinations", "Destinations", 1, "count"),
        ("d_rethink", "Re-decisions", 1e-6, "million"),
        ("d_sheltered", "Sheltered", 1e-3, "thousand"),
    ]
    means = np.array([np.mean([float(r[key]) for r in paired]) * scale for key, _, scale, _ in specs])
    ranges = np.array([
        [means[i] - min(float(r[key]) * scale for r in paired),
         max(float(r[key]) * scale for r in paired) - means[i]]
        for i, (key, _, scale, _) in enumerate(specs)
    ]).T
    labels = [s[1] for s in specs]
    units = [s[3] for s in specs]

    fig, ax = plt.subplots(figsize=(13.6, 5.2))
    y = np.arange(len(labels))
    colors = [CYAN, CYAN, ORANGE, RED]
    ax.barh(y, means, color=colors, height=0.58)
    ax.errorbar(means, y, xerr=ranges, fmt="none", ecolor=NAVY, capsize=4, lw=1.5)
    ax.axvline(0, color=NAVY, lw=1.2)
    ax.set_yticks(y, [f"{label} ({unit})" for label, unit in zip(labels, units)])
    ax.invert_yaxis()
    ax.set_title("LLM concentrates choices, then multiplies re-decision churn", pad=18)
    ax.set_xlabel("Paired difference: LLM − no leader (mixed units, labelled)")
    for yi, value, unit in zip(y, means, units):
        label = f"{value:+,.1f}" if unit != "count" else f"{value:+,.0f}"
        offset = max(abs(means)) * 0.018
        # Keep labels inside the bars so long negative values do not collide
        # with the y-axis category labels.
        ax.text(value + (-offset if value >= 0 else offset), yi, label,
                ha="right" if value >= 0 else "left", va="center",
                color="white", fontweight="bold")
    ax.grid(axis="x", color=LIGHT, lw=1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, -0.02,
             "Mechanism evidence: 68 fewer destinations and 144.4M more re-decisions accompany 304k fewer sheltered residents.",
             ha="center", fontsize=12.5, color=NAVY, fontweight="bold")
    save(fig, "fig_c20_llm_mechanism.png")


def load_raw(tag: str) -> dict:
    with (RAW / f"{tag}.json").open(encoding="utf-8") as stream:
        return json.load(stream)


def plot_timeseries() -> None:
    configs = [
        ("c20_cov000_s42", "0%", GRAY),
        ("c20_cov030_s42", "30%", BLUE),
        ("c20_cov060_s42", "60%", CYAN),
        ("c20_cov100_s42", "100%", GREEN),
    ]
    fig, ax = plt.subplots(figsize=(13.6, 5.5))
    for tag, label, color in configs:
        data = load_raw(tag)
        series = np.asarray(data["eva_series"], dtype=float)
        # One simulation step is ten seconds; columns are documented in each summary.
        minutes = series[:, 0] / 6.0
        sheltered = series[:, 3] / data["n_agents"] * 100
        ax.plot(minutes, sheltered, color=color, lw=2.8, label=f"Coverage {label}")
    ax.axvline(15, color=RED, ls="--", lw=1.5)
    ax.axvline(120, color=ORANGE, ls="--", lw=1.5)
    ax.text(15, 1.2, "15 min", color=RED, ha="left", fontweight="bold")
    ax.text(120, 1.2, "120 min", color=ORANGE, ha="left", fontweight="bold")
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 9.1)
    ax.set_xlabel("Simulation time (minutes)")
    ax.set_ylabel("Residents sheltered (%)")
    ax.set_title("Coverage accelerates early evacuation; terminal curves converge")
    ax.legend(frameon=False, ncol=2, loc="lower right")
    ax.grid(color=LIGHT, lw=1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, -0.02,
             "Canonical Chengdu · seed 42 example · the three-seed aggregates are reported in the main result.",
             ha="center", fontsize=12, color=NAVY, fontweight="bold")
    save(fig, "fig_c20_evacuation_curves.png")

    fig, ax = plt.subplots(figsize=(13.6, 5.5))
    for tag, label, color in configs:
        data = load_raw(tag)
        q = np.asarray(data["queue_series"], dtype=float) / 1e6
        minutes = np.arange(len(q)) / 6.0
        ax.plot(minutes, q, color=color, lw=2.5, label=f"Coverage {label}")
    ax.set_xlim(0, 180)
    ax.set_xlabel("Simulation time (minutes)")
    ax.set_ylabel("Rejected arrivals this step (million)")
    ax.set_title("More shared guidance produces a higher, earlier gate-pressure peak")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.grid(color=LIGHT, lw=1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, -0.02,
             "Queue_max is a rejected-arrivals proxy; interpret it jointly with safety and reachability, never alone.",
             ha="center", fontsize=12, color=NAVY, fontweight="bold")
    save(fig, "fig_c20_queue_curves.png")


def main() -> None:
    style()
    rows = load_csv(DATASET)
    paired = load_csv(PAIRED)
    plot_coverage(rows)
    plot_llm(paired)
    plot_mechanism(paired)
    plot_timeseries()
    for path in sorted(OUT.glob("fig_c20_*.png")):
        print(path.relative_to(ROOT), path.stat().st_size)


if __name__ == "__main__":
    main()
