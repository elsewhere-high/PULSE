# -*- coding: utf-8 -*-
"""
从疏散仿真样例构建分析数据集
================================================================
输入 : results/runs_raw/*.json     48 份原始运行样例
输出 : analysis_dataset.csv        逐运行平表(分析用)
       paired_effects.csv          配对差(每个非基准配置 x 每个种子)
       construction_log.txt        逐步构造留痕

原则(与数据字典一致):
  * 每一个派生变量都写明来源字段与公式,不静默构造
  * 冗余字段只保留一个代表,其余仅作校验
  * 单位统一为**分数**(不用百分数),避免 100 倍量级错误
  * 不删除任何运行;异常一律标记而非剔除
"""
import json, io, os, glob, csv, statistics as st, argparse

# 输入/输出默认取仓库内相对路径,无需机器专属路径即可复算样例证据链:
#   results/runs_raw/*.json (48 份原始 summary,随仓库分发)
#     -> 本脚本 -> analysis_dataset.csv / paired_effects.csv / effect_summary.csv
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ap = argparse.ArgumentParser()
_ap.add_argument("--runs", default=os.path.join(_REPO, "results", "runs_raw"),
                 help="原始 summary 目录(默认: 仓库内 results/runs_raw)")
_ap.add_argument("--out", default=os.path.join(_REPO, "results"),
                 help="输出目录(默认: 仓库内 results)")
_args = _ap.parse_args()
RUNS = _args.runs
OUT  = _args.out
LOG  = []

def log(m):
    LOG.append(m); print(m)

log("=" * 64)
log("变量构造 — 疏散仿真样例")
log("=" * 64)

# ---------------------------------------------------------------
# 步骤 1  读入原始运行
# ---------------------------------------------------------------
files = sorted(glob.glob(os.path.join(RUNS, "*.json")))
raw = {}
for p in files:
    tag = os.path.basename(p)[:-5]
    raw[tag] = json.load(io.open(p, encoding="utf-8"))
log("\n[1] 读入 %d 份运行输出" % len(raw))

# ---------------------------------------------------------------
# 步骤 2  分组:口径与配置
#   口径由 base map 决定;tag 以 'off' 开头者为 chengdu_official
#   配置由 tag 去掉 _s<seed> 后缀得到
# ---------------------------------------------------------------
def caliber(tag):
    # 第三口径:c20_* = chengdu_census2020
    # (普查 2020 对齐底图,20,937,757 代理;管线 smoke/coverage/llm 三段,seed 42/43/44)
    if tag.startswith("c20"):
        return "chengdu_census2020"
    return "chengdu_official" if tag.startswith("off") else "chengdu831"

def config(tag):
    return tag.rsplit("_s", 1)[0]

def seed_of(tag, d):
    s = d.get("seed")
    if s is not None: return int(s)
    return int(tag.rsplit("_s", 1)[1])

log("[2] 分组:口径由 tag 前缀判定,配置由 tag 去 _s<seed> 得到")

# 每个口径的基准配置(信息覆盖 0.30 / 无 LLM / 无损伤)
BASELINE = {"chengdu831": "cov30", "chengdu_official": "off",
            "chengdu_census2020": "c20_cov030"}
log("    基准配置: %s" % BASELINE)

# ---------------------------------------------------------------
# 步骤 3  构造逐运行平表
# ---------------------------------------------------------------
log("\n[3] 构造逐运行变量")

# 3.1 直接取用(无变换)——冗余组只取代表
DIRECT = [
    # DV
    ("Safe15",        "share_safe_by_15min",     "totals", "直接取用"),
    ("Safe30",        "share_safe_by_30min",     "totals", "直接取用"),
    ("Safe60",        "share_safe_by_60min",     "totals", "直接取用"),
    ("Safe120",       "share_safe_by_120min",    "totals", "直接取用"),
    ("Queue_max",     "queue_max",               "totals", "直接取用"),
    ("Overflow",      "overfilled_shelters",     "totals", "直接取用"),
    ("EquityGap",     "shelter_occupancy_gini",  "totals", "直接取用"),
    ("sheltered",     "sheltered",               "totals", "冗余组代表(= shelter_occupancy = n_with_time)"),
    ("shelter_util",  "shelter_utilisation",     "totals", "直接取用"),
    ("gave_up",       "gave_up",                 "totals", "直接取用"),
    ("t_p50_min",     "t_p50_min_of_sheltered",  "totals", "直接取用"),
    ("t_p90_min",     "t_p90_min_of_sheltered",  "totals", "直接取用"),
    # MED
    ("n_destinations","distinct_destinations",   "totals", "直接取用"),
    ("walk_median_m", "median_dist_walked_m",    "totals", "直接取用"),
    ("walk_mean_m",   "mean_dist_walked_m",      "totals", "直接取用;右偏,不可与中位数互换"),
    ("rethink",       "rethink_events",          "totals", "直接取用"),
    ("rejections",    "rejections_at_full_gate", "totals", "累计量,非峰值"),
    ("shelters_known","mean_shelters_known",     "totals", "直接取用"),
    ("hops_mean",     "mean_hops",               "totals", "直接取用"),
    ("switch_share",  "share_who_ever_switched", "totals", "直接取用"),
    ("giveup_exhaust","gave_up_exhausted",       "totals", "直接取用"),
    ("giveup_nopath", "gave_up_no_path",         "totals", "直接取用"),
    # CTRL
    ("n_agents",      "n_agents",                "totals", "直接取用"),
    ("capacity",      "shelter_capacity",        "totals", "直接取用"),
    ("cap_share",     "capacity_share_of_population", "totals", "直接取用"),
    # INV
    ("cons_error",    "conservation_error",      "totals", "不变量,必须为 0"),
    ("accounted",     "accounted",               "totals", "不变量,应等于 n_agents"),
    # IV / META (顶层)
    ("seed",          "seed",                    "top",    "直接取用"),
    ("steps",         "steps",                   "top",    "直接取用"),
    ("n_blocks",      "n_blocks",                "top",    "直接取用"),
    ("frac_knows_one","frac_knows_one",          "top",    "直接取用"),
    ("broadcast",     "broadcast_reach",         "top",    "直接取用"),
    ("road_damage",   "road_damage",             "top",    "直接取用"),
    ("llm_enabled",   "llm_enabled",             "top",    "直接取用"),
    ("leader_comm",   "leader_comm",             "top",    "直接取用"),
    ("wall_s",        "wall_s",                  "top",    "直接取用"),
]
for name, src, where, note in DIRECT:
    log("    %-16s <- %-28s [%s]  %s" % (name, src, where, note))

# 3.2 派生变量
log("\n    -- 派生 --")
DERIVED_DOC = [
  ("unreached",      "n_agents - sheltered",                     "未获避难人数(与 unsheltered_share 等价,取绝对数以免单位混淆)"),
  ("shelter_use_share","n_destinations / n_shelters_total",      "被使用的避难所占全部避难所的比例;n_shelters_total = 1252"),
  ("exhaust_share",  "giveup_exhaust / gave_up",                 "放弃者中因力竭者的占比(机制指标)"),
  ("nopath_share",   "giveup_nopath / gave_up",                  "放弃者中因无路者的占比(机制指标)"),
  ("late_early_ratio","Safe120 / Safe15",                        "晚期对早期的倍数;越接近 1 说明收益全在早期"),
  ("J_raw",          "Safe15 - Queue_max/n_agents - Overflow/n_shelters_total - EquityGap",
                     "J(theta) 的**透明权重版**:四分量各按其自然尺度归一后等权相减。"
                     "此处未固定 alpha/beta/gamma/eta,故此处不作唯一排名,仅供分量并列参考"),
]
for name, formula, note in DERIVED_DOC:
    log("    %-18s = %-44s  %s" % (name, formula, note))

N_SHELTERS_TOTAL = 1252

rows = []
for tag, d in sorted(raw.items()):
    t = d.get("totals", {})
    r = {"tag": tag, "caliber": caliber(tag), "config": config(tag)}
    for name, src, where, _ in DIRECT:
        r[name] = (t if where == "totals" else d).get(src)
    r["seed"] = seed_of(tag, d)
    # 派生
    r["unreached"] = r["n_agents"] - r["sheltered"]
    r["shelter_use_share"] = r["n_destinations"] / N_SHELTERS_TOTAL
    r["exhaust_share"] = r["giveup_exhaust"] / r["gave_up"] if r["gave_up"] else None
    r["nopath_share"]  = r["giveup_nopath"] / r["gave_up"] if r["gave_up"] else None
    r["late_early_ratio"] = r["Safe120"] / r["Safe15"] if r["Safe15"] else None
    r["J_raw"] = (r["Safe15"] - r["Queue_max"]/r["n_agents"]
                  - r["Overflow"]/N_SHELTERS_TOTAL - r["EquityGap"])
    # 有效性标记(标记而非剔除)
    r["flag_cons"]  = 0 if r["cons_error"] == 0 else 1
    r["flag_overflow"] = 0 if r["Overflow"] == 0 else 1
    r["flag_accounted"] = 0 if r["accounted"] == r["n_agents"] else 1
    rows.append(r)

log("\n    构造完成:%d 行 x %d 列" % (len(rows), len(rows[0])))
bad = [r["tag"] for r in rows if r["flag_cons"] or r["flag_overflow"] or r["flag_accounted"]]
log("    有效性标记非 0 的运行:%s" % (bad if bad else "无"))

# ---------------------------------------------------------------
# 步骤 4  配对差(每个非基准配置 vs 同口径同种子的基准)
# ---------------------------------------------------------------
log("\n[4] 构造配对差:同口径、同种子,仅配置不同")
idx = {(r["caliber"], r["config"], r["seed"]): r for r in rows}
PAIR_VARS = ["Safe15","Safe120","Queue_max","EquityGap","sheltered",
             "shelter_util","walk_median_m","n_destinations","rethink"]
pairs = []
for r in rows:
    base_cfg = BASELINE[r["caliber"]]
    if r["config"] == base_cfg: continue
    b = idx.get((r["caliber"], base_cfg, r["seed"]))
    if not b:
        log("    !! 缺基准配对:%s" % r["tag"]); continue
    p = {"caliber": r["caliber"], "config": r["config"], "seed": r["seed"],
         "baseline": base_cfg}
    for v in PAIR_VARS:
        p["d_" + v] = r[v] - b[v]
    pairs.append(p)
log("    配对差:%d 行" % len(pairs))

# 4.1 每配置的种子一致性与效应/噪声
log("\n[5] 每配置汇总:中位效应、种子极差、同号数")
summ = []
by = {}
for p in pairs:
    by.setdefault((p["caliber"], p["config"]), []).append(p)
for (cal, cfg), ps in sorted(by.items()):
    row = {"caliber": cal, "config": cfg, "n_seeds": len(ps)}
    for v in PAIR_VARS:
        ds = [p["d_" + v] for p in ps]
        med = st.median(ds)
        sgn = 0 if med == 0 else (1 if med > 0 else -1)
        agree = sum(1 for x in ds if (0 if x == 0 else (1 if x > 0 else -1)) == sgn)
        # 噪声 = 该配置与其基准各自的种子极差取大者
        vals_c = [idx[(cal, cfg, p["seed"])][v] for p in ps]
        vals_b = [idx[(cal, BASELINE[cal], p["seed"])][v] for p in ps]
        noise = max(max(vals_c) - min(vals_c), max(vals_b) - min(vals_b))
        row["med_d_" + v] = med
        row["agree_" + v] = "%d/%d" % (agree, len(ds))
        row["ratio_" + v] = (abs(med) / noise) if noise else None
    # 反转边界
    row["in_B"] = 1 if row["med_d_Safe15"] * row["med_d_Safe120"] < 0 else 0
    summ.append(row)
inB = [(r["caliber"], r["config"]) for r in summ if r["in_B"]]
log("    落入反转边界 B 的配置:%s" % (inB if inB else "无"))

# ---------------------------------------------------------------
# 步骤 6  写出
# ---------------------------------------------------------------
def dump(path, data):
    if not data: return
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        # lineterminator 显式取 LF: csv 模块默认 CRLF, 会随平台漂移;
        # 而校验器的判据是"重算输出与仓库 blob 逐字节一致", 故行尾必须钉死。
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()), lineterminator=chr(10))
        w.writeheader(); w.writerows(data)
    log("    写出 %s  (%d 行)" % (os.path.basename(path), len(data)))

log("\n[6] 写出")
dump(os.path.join(OUT, "analysis_dataset.csv"), rows)
dump(os.path.join(OUT, "paired_effects.csv"), pairs)
dump(os.path.join(OUT, "effect_summary.csv"), summ)
io.open(os.path.join(OUT, "construction_log.txt"), "w",
        encoding="utf-8", newline="").write("\n".join(LOG))
print("\n完成。构造留痕见 construction_log.txt")
