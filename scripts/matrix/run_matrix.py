# -*- coding: utf-8 -*-
"""Run six coverage and road-damage configurations across three random seeds.

Event streams are disabled to avoid large output files. Existing summaries
allow interrupted batches to resume. City inputs use the local runner defaults.
"""
import os, io, json, subprocess, time, csv, sys

CLA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY  = sys.executable
OUT = os.environ.get("PULSE_MATRIX_DIR", os.path.join(CLA, "results", "matrix"))
LOG = os.path.join(OUT, "matrix.log")
STEPS = 1080
SEEDS = [42, 43, 44]

# (名称, 额外参数, 说明)
CONFIGS = [
 ("cov00",  ["--frac-knows-one","0.0","--broadcast-reach","0.0"], "信息覆盖 0"),
 ("cov30",  [],                                                    "基准(覆盖 0.30/广播 0.35)"),
 ("cov60",  ["--frac-knows-one","0.6","--broadcast-reach","0.6"],  "信息覆盖 0.60"),
 ("cov100", ["--frac-knows-one","1.0","--broadcast-reach","1.0"],  "信息覆盖 1.00"),
 ("dmg15",  ["--road-damage","0.15"],                               "道路失效 0.15"),
 ("dmg30",  ["--road-damage","0.30"],                               "道路失效 0.30"),
]

os.makedirs(OUT, exist_ok=True)

def log(m):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    io.open(LOG, "a", encoding="utf-8").write(line + "\n")

log("=== 矩阵开始:%d 配置 x %d 种子 = %d 次 ===" % (len(CONFIGS), len(SEEDS), len(CONFIGS)*len(SEEDS)))
t_all = time.time()
done, failed = [], []

for name, extra, desc in CONFIGS:
    for seed in SEEDS:
        tag = "%s_s%d" % (name, seed)
        rd  = os.path.join(OUT, tag)
        sj  = os.path.join(rd, "summary.json")
        if os.path.exists(sj) and os.path.getsize(sj) > 200:
            log("跳过(已有) %s" % tag); done.append(tag); continue
        cmd = [PY, "scripts/bench_swarm.py", "--steps", str(STEPS), "--no-events",
               "--seed", str(seed), "--run-dir", rd, "--tag", tag] + extra
        log("跑 %s  (%s, seed=%d) ..." % (tag, desc, seed))
        t0 = time.time()
        p = subprocess.run(cmd, cwd=CLA, capture_output=True)
        dt = time.time() - t0
        if p.returncode == 0 and os.path.exists(sj):
            try:
                d = json.load(io.open(sj, encoding="utf-8"))
                t = d["totals"]
                log("  OK %s  %.0fs  Safe15=%.5f Safe120=%.5f Qmax=%s cons_err=%s"
                    % (tag, dt, t["share_safe_by_15min"], t["share_safe_by_120min"],
                       t.get("queue_max"), t["conservation_error"]))
                done.append(tag)
            except Exception as e:
                log("  !! %s summary 解析失败 %s" % (tag, e)); failed.append(tag)
        else:
            tail = (p.stdout + p.stderr).decode("utf-8", "ignore")[-600:]
            log("  FAIL %s rc=%d\n%s" % (tag, p.returncode, tail)); failed.append(tag)

# ---- 汇总成表 ----
rows = []
for name, extra, desc in CONFIGS:
    for seed in SEEDS:
        tag = "%s_s%d" % (name, seed)
        sj = os.path.join(OUT, tag, "summary.json")
        if not os.path.exists(sj): continue
        d = json.load(io.open(sj, encoding="utf-8")); t = d["totals"]
        rows.append({
            "config": name, "desc": desc, "seed": seed,
            "n_agents": t["n_agents"],
            "conservation_error": t["conservation_error"],
            "Safe15": t["share_safe_by_15min"],
            "Safe30": t["share_safe_by_30min"],
            "Safe60": t["share_safe_by_60min"],
            "Safe120": t["share_safe_by_120min"],
            "Queue_max": t.get("queue_max"),
            "Overflow": t["overfilled_shelters"],
            "EquityGap_gini": t["shelter_occupancy_gini"],
            "sheltered": t["sheltered"], "gave_up": t["gave_up"],
            "median_walk_m": t["median_dist_walked_m"],
            "wall_s": d.get("wall_s"), "ms_per_step": d.get("ms_per_step"),
            "frac_knows_one": d.get("frac_knows_one"),
            "broadcast_reach": d.get("broadcast_reach"),
            "road_damage": d.get("road_damage"),
        })
if rows:
    with io.open(os.path.join(OUT, "matrix_results.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    io.open(os.path.join(OUT, "matrix_results.json"), "w", encoding="utf-8").write(
        json.dumps(rows, ensure_ascii=False, indent=1))

log("=== 矩阵结束 %.1f min  成功 %d  失败 %d ===" % ((time.time()-t_all)/60, len(done), len(failed)))
if failed: log("失败: %s" % failed)
