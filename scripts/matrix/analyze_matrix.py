# -*- coding: utf-8 -*-
"""按固定实验参照系判读矩阵结果。

三件事:
 1. J(theta) 的四个分量分别报出。指标定义要求"J 不作为唯一排名;分别保存各分量,
    防止以牺牲晚期安全或公平换取早期收益",且 alpha/beta/gamma/eta 未给定,
    故此处给一组透明权重 + 敏感性,不给单一排名。
 2. 复现判据 Sum 1[sign(Delta_k)=sign(Delta_Theta)] >= 2 —— 至少 2/3 种子方向一致。
 3. 反转边界 B = {theta | Delta_15 * Delta_120 < 0}。
"""
import io, json, os, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.environ.get("PULSE_MATRIX_DIR", os.path.join(ROOT, "results", "matrix"))
rows = json.load(io.open(os.path.join(OUT, "matrix_results.json"), encoding="utf-8"))
BASE = "cov30"                      # 基准配置

by = {}
for r in rows:
    by.setdefault(r["config"], []).append(r)
for k in by:
    by[k].sort(key=lambda r: r["seed"])

def med(cfg, key):
    v = [r[key] for r in by[cfg] if r[key] is not None]
    return statistics_median(v) if v else None
def statistics_median(v):
    return st.median(v)

L = []
def P(s=""): L.append(s); print(s)

P("# 疏散实验矩阵 —— 参照系判读")
P()
P("基准配置 `%s`;每配置 %d 个随机种子。" % (BASE, len(by.get(BASE, []))))
P()

# ---------- 0 硬门槛 ----------
P("## 0. 硬门槛(规则要求人口守恒误差为 0)")
P()
bad = [r["config"]+"_s"+str(r["seed"]) for r in rows if r["conservation_error"] != 0]
over = [r["config"]+"_s"+str(r["seed"]) for r in rows if r["Overflow"] != 0]
P("- 运行数:**%d**" % len(rows))
P("- 人口守恒误差非 0 的运行:**%s**" % (bad if bad else "无 —— 全部为 0 ✅"))
P("- 避难所超容的运行:**%s**" % (over if over else "无 —— 全部为 0 ✅"))
P()

# ---------- 1 分量表 ----------
P("## 1. J(θ) 四分量(按配置取种子中位数)")
P()
P("| 配置 | 说明 | Safe15 | Safe120 | Queue_max | Overflow | EquityGap(gini) |")
P("|---|---|---|---|---|---|---|")
for cfg in by:
    d = by[cfg][0]["desc"]
    P("| `%s` | %s | %.5f | %.5f | %s | %s | %.4f |" % (
        cfg, d, med(cfg,"Safe15"), med(cfg,"Safe120"),
        format(int(med(cfg,"Queue_max")), ","), int(med(cfg,"Overflow")),
        med(cfg,"EquityGap_gini")))
P()
P("> Queue_max 的定义:本模型无显式排队态(`S_QUEUED` 定义了但全代码未使用),")
P("> 机制是到达即判容量、超出者被拒并须再走一段。故瞬时门前队列的可辨识对应物 =")
P("> **该步到达但未获接纳的人数**,Queue_max 为其全程峰值。该定义随结果一并声明。")
P()

# ---------- 2 复现判据 ----------
P("## 2. 复现判据:至少 2/3 种子方向一致")
P()
P("对每个配置,取其相对基准 `%s` 的 ΔSafe15 与 ΔSafe120,逐种子配对比较。" % BASE)
P()
P("| 配置 | ΔSafe15 逐种子 | 同号数 | ΔSafe120 逐种子 | 同号数 | 判定 |")
P("|---|---|---|---|---|---|")
def sgn(x): return 0 if x == 0 else (1 if x > 0 else -1)
verdict = {}
for cfg in by:
    if cfg == BASE: continue
    d15, d120 = [], []
    for r in by[cfg]:
        b = [x for x in by[BASE] if x["seed"] == r["seed"]]
        if not b: continue
        d15.append(r["Safe15"] - b[0]["Safe15"])
        d120.append(r["Safe120"] - b[0]["Safe120"])
    if not d15: continue
    m15, m120 = sgn(st.median(d15)), sgn(st.median(d120))
    a15 = sum(1 for x in d15 if sgn(x) == m15)
    a120 = sum(1 for x in d120 if sgn(x) == m120)
    ok = (a15 >= 2 and a120 >= 2)
    verdict[cfg] = (d15, d120, a15, a120, ok)
    P("| `%s` | %s | **%d/%d** | %s | **%d/%d** | %s |" % (
        cfg, ", ".join("%+.5f" % x for x in d15), a15, len(d15),
        ", ".join("%+.5f" % x for x in d120), a120, len(d120),
        "通过" if ok else "**未通过**"))
P()

# ---------- 3 反转边界 ----------
P("## 3. 反转边界 B = {θ | Δ₁₅·Δ₁₂₀ < 0}")
P()
P('早期收益与晚期收益方向相反者落入 B —— 即“改善了 15 分钟安全率,却损害了 120 分钟”。')
P()
P("| 配置 | 中位 ΔSafe15 | 中位 ΔSafe120 | 乘积 | 是否落入 B |")
P("|---|---|---|---|---|")
inB = []
for cfg, (d15, d120, a15, a120, ok) in verdict.items():
    m15, m120 = st.median(d15), st.median(d120)
    prod = m15 * m120
    hit = prod < 0
    if hit: inB.append(cfg)
    P("| `%s` | %+.5f | %+.5f | %+.3e | %s |" % (
        cfg, m15, m120, prod, "**是**" if hit else "否"))
P()
P("落入反转边界的配置:**%s**" % (", ".join("`%s`" % c for c in inB) if inB else "无"))
P()

# ---------- 4 曲线可用性 ----------
P("## 4. §4.1 要求的两条曲线")
P()
n_q = n_e = 0
for cfg in by:
    for r in by[cfg]:
        p = os.path.join(OUT, "%s_s%d" % (cfg, r["seed"]), "summary.json")
        if not os.path.exists(p): continue
        d = json.load(io.open(p, encoding="utf-8"))
        n_q += 1 if d.get("queue_series") else 0
        n_e += 1 if d.get("eva_series") else 0
P("- 队列曲线 `queue_series`(逐步):**%d/%d** 次运行已产出" % (n_q, len(rows)))
P("- 疏散曲线 `eva_series`(每 5 步):**%d/%d** 次运行已产出" % (n_e, len(rows)))
P()

io.open(os.path.join(OUT, "ANALYSIS.md"), "w", encoding="utf-8").write("\n".join(L))
print()
print("已写出", os.path.join(OUT, "ANALYSIS.md"))
