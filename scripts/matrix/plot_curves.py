# -*- coding: utf-8 -*-
"""Generate evacuation and queue curves with portable English labels."""
import io, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.environ.get("PULSE_MATRIX_DIR", os.path.join(ROOT, "results", "matrix"))
FIG = os.path.join(OUT, "figs")
os.makedirs(FIG, exist_ok=True)

CONFIGS = [("cov00","Coverage 0.00","#B03A32"),
           ("cov30","Coverage 0.30 (baseline)","#2A4C8F"),
           ("cov60","Coverage 0.60","#1F7A5C"),
           ("cov100","Coverage 1.00","#8A5CB8"),
           ("dmg15","Road damage 0.15","#D08A1E"),
           ("dmg30","Road damage 0.30","#7A4A22")]
SEED = 42
DT_MIN = 1080 / 180.5 if False else None   # 由数据自算

def load(cfg, seed=SEED):
    p = os.path.join(OUT, "%s_s%d" % (cfg, seed), "summary.json")
    if not os.path.exists(p): return None
    return json.load(io.open(p, encoding="utf-8"))

# 每步分钟数:由 totals.t_minutes / steps 反推
def minutes_per_step(d):
    return d["totals"]["t_minutes"] / max(d.get("steps", 1080), 1)

# ---------------- Fig 1: evacuation curves ----------------
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axes[0]
for cfg, lab, col in CONFIGS:
    d = load(cfg)
    if not d or not d.get("eva_series"): continue
    mps = minutes_per_step(d)
    e = d["eva_series"]
    t = [r[0] * mps for r in e]
    shel = [r[3] / d["totals"]["n_agents"] * 100 for r in e]
    ax.plot(t, shel, label=lab, color=col, lw=1.8)
ax.set_xlabel("Elapsed time (min)"); ax.set_ylabel("Sheltered (% of population)")
ax.set_title("(a) Evacuation curve — sheltered share", fontsize=11)
ax.grid(alpha=.25); ax.legend(fontsize=8, frameon=False)

ax = axes[1]
for cfg, lab, col in CONFIGS:
    d = load(cfg)
    if not d or not d.get("eva_series"): continue
    mps = minutes_per_step(d)
    e = d["eva_series"]
    t = [r[0] * mps for r in e]
    tr = [r[2] / d["totals"]["n_agents"] * 100 for r in e]
    ax.plot(t, tr, label=lab, color=col, lw=1.8)
ax.set_xlabel("Elapsed time (min)"); ax.set_ylabel("In transit (% of population)")
ax.set_title("(b) Evacuation curve — in-transit share", fontsize=11)
ax.grid(alpha=.25)
fig.suptitle("Chengdu (chengdu_admin, 22,381,605 agents) — seed %d" % SEED, fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_evacuation_curves.png"), dpi=160)
print("wrote fig_evacuation_curves.png")

# ---------------- Fig 2: queue curves ----------------
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axes[0]
for cfg, lab, col in CONFIGS:
    d = load(cfg)
    if not d or not d.get("queue_series"): continue
    mps = minutes_per_step(d)
    q = d["queue_series"]
    t = [i * mps for i in range(len(q))]
    ax.plot(t, [v / 1e3 for v in q], label=lab, color=col, lw=1.2)
ax.set_xlabel("Elapsed time (min)"); ax.set_ylabel("Turned away at full gate (thousands / step)")
ax.set_title("(a) Queue curve — instantaneous gate overflow", fontsize=11)
ax.grid(alpha=.25); ax.legend(fontsize=8, frameon=False)

ax = axes[1]
names, vals, cols = [], [], []
for cfg, lab, col in CONFIGS:
    d = load(cfg)
    if not d: continue
    names.append(lab.replace(" (baseline)", "*")); vals.append(d["totals"].get("queue_max", 0) / 1e6); cols.append(col)
ax.barh(range(len(names)), vals, color=cols, height=.6)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9)
ax.invert_yaxis(); ax.set_xlabel("Queue_max (millions)")
ax.set_title("(b) Queue_max — peak of the curve in (a)", fontsize=11)
ax.grid(axis="x", alpha=.25)
fig.suptitle("Queue_max is the fourth component of J(theta); defined as peak per-step arrivals refused at a full gate",
             fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_queue_curves.png"), dpi=160)
print("wrote fig_queue_curves.png")
print("目录:", FIG)
