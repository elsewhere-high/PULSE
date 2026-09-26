"""Render PULSE's mechanism exports as a shareable PNG figure."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/demo"))
    parser.add_argument("--output", type=Path, default=Path("results/demo/pulse_demo.png"))
    args = parser.parse_args()
    with (args.input / "queue_series.csv").open() as stream:
        queue = list(csv.DictReader(stream))
    with (args.input / "demand_scan.csv").open() as stream:
        scan = list(csv.DictReader(stream))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": "#203337", "text.color": "#203337"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    fig.suptitle("PULSE  /  Evacuation mechanism experiments", fontweight="bold", fontsize=19)
    t = [float(r["time_s"]) / 60 for r in queue]
    for field, label, color in [("baseline_queue", "No intervention", "#0e8074"),
                                ("selected_queue", "Selected control", "#d18439")]:
        axes[0].plot(t, [float(r[field]) for r in queue], label=label, color=color, lw=2.2)
    axes[0].set(title="Queue response · 1,000 vehicles", xlabel="Elapsed time (min)", ylabel="Queue (vehicles)")
    axes[0].legend(frameon=False)
    axes[1].plot([float(r["demand"]) for r in scan], [float(r["max_queue"]) for r in scan],
                 "o-", color="#0e8074", lw=2.2, label="Selected control")
    axes[1].axvspan(1100, 1300, color="#d18439", alpha=.14, label="Candidate boundary")
    axes[1].set(title="Demand scan", xlabel="Evacuation demand (vehicles)", ylabel="Peak queue (vehicles)")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(axis="y", color="#e2e9e9")
        ax.set_axisbelow(True)
        ax.set_ylim(bottom=0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180, facecolor="white")
    plt.close(fig)
    print(f"PULSE figure: {args.output}")


if __name__ == "__main__":
    main()
