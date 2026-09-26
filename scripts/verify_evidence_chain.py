# -*- coding: utf-8 -*-
"""核验机理模型和附带实验样例的数据一致性。

用法(仓库根目录,零第三方依赖,无需 GPU,约 10 秒):

    python scripts/verify_evidence_chain.py

逐项核验:
  [1] A 层机理切片可运行:20 次试验,人口守恒误差全部为 0
  [2] 单元测试 通过
  [3] B 层硬门槛:48 份原始 summary(results/runs_raw/)的
      conservation_error 与 overfilled_shelters 全部为 0
  [4] 两条曲线 48/48 产出(queue_series 长 1083,eva_series 长 217)
  [5] 追溯表与 48 份 raw summary 一一对应
  [6] 平表可再生:runs_raw -> build_analysis_dataset.py 的输出
      与仓库提交的 analysis_dataset.csv 逐字节一致,且恰为 48 行(历史 33 + 规范化成都 15)
  [7] 反转边界反例:chengdu_official/offcov100 落入 B(Delta15*Delta120<0,3/3 同号)
  [8] 机理定量关系:中位步行降幅之比 1.66 与晚期安全损害之比 1.64,由平表两列独立重算

任何一项失败即退出码非 0。本脚本只读 results/ 与 runs_raw/,不修改任何提交文件。
"""
import csv
import io
import json
import os
import shutil
import statistics as st
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
RESULTS = os.path.join(REPO, "results")
RUNS_RAW = os.path.join(RESULTS, "runs_raw")

FAILED = []
TOTAL = 0


def check(name, ok, detail=""):
    global TOTAL
    TOTAL += 1
    mark = "PASS" if ok else "FAIL"
    print("[%s] %s%s" % (mark, name, ("  —— " + detail) if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    print("=" * 72)
    print("PULSE 实验样例校验  (repo: %s)" % REPO)
    print("=" * 72)

    # [1] A 层机理切片
    tmp = tempfile.mkdtemp(prefix="pulse_verify_")
    try:
        r = subprocess.run([PY, os.path.join(REPO, "run_experiment.py"), "--output", tmp],
                           cwd=REPO, capture_output=True, text=True, timeout=300)
        trials_p = os.path.join(tmp, "trials.json")
        ok = r.returncode == 0 and os.path.exists(trials_p)
        n = 0
        cons_ok = False
        if ok:
            trials = json.load(io.open(trials_p, encoding="utf-8"))
            n = len(trials)
            cons_ok = all(t["metrics"]["conservation_error"] == 0 for t in trials)
        check("A 层机理切片运行 + 守恒", ok and n == 20 and cons_ok,
              "%d 次试验, conservation_error 全 0: %s" % (n, cons_ok))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # [2] 单元测试
    r = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=REPO, capture_output=True, text=True, timeout=300)
    ok = r.returncode == 0 and "OK" in (r.stderr + r.stdout)
    check("单元测试", ok, (r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) else "")

    # [3][4] B 层硬门槛与曲线 —— 逐份原始 summary
    def dig(o, k):
        if isinstance(o, dict):
            if k in o:
                return o[k]
            for v in o.values():
                r2 = dig(v, k)
                if r2 is not None:
                    return r2
        return None

    files = sorted(f for f in os.listdir(RUNS_RAW) if f.endswith(".json"))
    ce_bad, ov_bad, q_bad, e_bad = [], [], [], []
    for f in files:
        d = json.load(io.open(os.path.join(RUNS_RAW, f), encoding="utf-8"))
        if dig(d, "conservation_error") != 0:
            ce_bad.append(f)
        if dig(d, "overfilled_shelters") != 0:
            ov_bad.append(f)
        qs, es = dig(d, "queue_series"), dig(d, "eva_series")
        if not qs or len(qs) != 1083:
            q_bad.append(f)
        if not es or len(es) != 217:
            e_bad.append(f)
    check("B 层硬门槛 48/48", len(files) == 48 and not ce_bad and not ov_bad,
          "%d 份; 守恒非0: %s; 超容非0: %s" % (len(files), ce_bad or "无", ov_bad or "无"))
    check("两条曲线 48/48", not q_bad and not e_bad,
          "queue_series!=1083: %s; eva_series!=217: %s" % (q_bad or "无", e_bad or "无"))

    # [5] 追溯表覆盖：文件名、run tag 与声明数量必须完全闭合
    trace = json.load(io.open(os.path.join(RESULTS, "traceability.json"), encoding="utf-8"))
    raw_tags = {os.path.splitext(f)[0] for f in files}
    trace_tags = {r.get("tag") for r in trace.get("runs", [])}
    missing = sorted(raw_tags - trace_tags)
    extra = sorted(trace_tags - raw_tags)
    trace_ok = (trace.get("n_runs") == 48 and len(trace.get("runs", [])) == 48
                and not missing and not extra)
    check("追溯表覆盖 48/48 raw summaries", trace_ok,
          "n_runs=%s, runs=%d, 缺失=%s, 多余=%s"
          % (trace.get("n_runs"), len(trace.get("runs", [])), missing or "无", extra or "无"))

    # [6] 平表可再生(输出到临时目录,与提交版逐字节比对)
    tmp2 = tempfile.mkdtemp(prefix="pulse_table_")
    try:
        r = subprocess.run([PY, os.path.join(REPO, "scripts", "matrix", "build_analysis_dataset.py"),
                            "--runs", RUNS_RAW, "--out", tmp2],
                           cwd=REPO, capture_output=True, text=True, timeout=300)
        same = {}
        for f in ("analysis_dataset.csv", "paired_effects.csv", "effect_summary.csv"):
            a, b = os.path.join(tmp2, f), os.path.join(RESULTS, f)
            if not os.path.exists(a):
                same[f] = "重算未产出"   # 与"内容不一致"分开报,脚本崩溃不该被误读成数据问题
            elif io.open(a, "rb").read() == io.open(b, "rb").read():
                same[f] = "一致"
            else:
                same[f] = "不一致"
        generated_rows = 0
        generated_csv = os.path.join(tmp2, "analysis_dataset.csv")
        if os.path.exists(generated_csv):
            generated_rows = sum(1 for _ in csv.DictReader(
                io.open(generated_csv, encoding="utf-8-sig")))
        ok5 = (r.returncode == 0 and all(v == "一致" for v in same.values())
               and generated_rows == 48)
        detail = ", ".join("%s:%s" % kv for kv in same.items())
        detail += ", analysis_dataset:%d 行" % generated_rows
        if r.returncode != 0 and r.stderr:
            detail += " | 构造脚本错误: " + r.stderr.strip().splitlines()[-1][:120]
        check("平表由 runs_raw 逐字节再生", ok5, detail)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # [7][8] 从平表独立重算两条核心主张
    rows = list(csv.DictReader(io.open(os.path.join(RESULTS, "analysis_dataset.csv"),
                                       encoding="utf-8-sig")))
    def med(cal, cfg, col):
        v = [float(r[col]) for r in rows if r["caliber"] == cal and r["config"] == cfg]
        return st.median(v) if v else None

    def deltas(cal, cfg, base, col):
        out = []
        for seed in ("42", "43", "44"):
            a = [float(r[col]) for r in rows
                 if r["caliber"] == cal and r["config"] == cfg and r["seed"] == seed]
            b = [float(r[col]) for r in rows
                 if r["caliber"] == cal and r["config"] == base and r["seed"] == seed]
            if a and b:
                out.append(a[0] - b[0])
        return out

    d15 = deltas("chengdu_official", "offcov100", "off", "Safe15")
    d120 = deltas("chengdu_official", "offcov100", "off", "Safe120")
    in_b = st.median(d15) * st.median(d120) < 0
    agree = all(x > 0 for x in d15) and all(x < 0 for x in d120)
    check("反例: offcov100 落入反转边界 B", in_b and agree,
          "中位 ΔSafe15=%+.5f, ΔSafe120=%+.5f, 3/3 同号: %s"
          % (st.median(d15), st.median(d120), agree))

    walk_a = (med("chengdu831", "llm", "walk_median_m") /
              med("chengdu831", "cov30", "walk_median_m") - 1)
    walk_b = (med("chengdu_official", "offllm", "walk_median_m") /
              med("chengdu_official", "off", "walk_median_m") - 1)
    s120_a = (med("chengdu831", "llm", "Safe120") /
              med("chengdu831", "cov30", "Safe120") - 1)
    s120_b = (med("chengdu_official", "offllm", "Safe120") /
              med("chengdu_official", "off", "Safe120") - 1)
    r_walk = walk_a / walk_b
    r_s120 = s120_a / s120_b
    ok = abs(r_walk - 1.66) < 0.02 and abs(r_s120 - 1.64) < 0.02
    check("机理: 1.66 与 1.64 可从平表重算", ok,
          "步行降幅之比 %.2f (%.1f%%/%.1f%%), 损害之比 %.2f (%.1f%%/%.1f%%)"
          % (r_walk, 100 * walk_a, 100 * walk_b, r_s120, 100 * s120_a, 100 * s120_b))

    # [9] 第三口径复现(规范化成都):
    #     LLM 伤害 3/3 同号;"步行中位降幅/晚期安全损害"的比值与 chengdu831 一致(均约 2.0);
    #     且 offcov100 型反转在规范化实例上不出现(c20_cov100 的 ΔSafe120 非负)。
    c_h = deltas("chengdu_census2020", "c20_llm", "c20_cov030", "Safe120")
    w_c = (med("chengdu_census2020", "c20_llm", "walk_median_m") /
           med("chengdu_census2020", "c20_cov030", "walk_median_m") - 1)
    h_c = (med("chengdu_census2020", "c20_llm", "Safe120") /
           med("chengdu_census2020", "c20_cov030", "Safe120") - 1)
    ratio_c = w_c / h_c
    ratio_a = walk_a / s120_a
    d120_c = deltas("chengdu_census2020", "c20_cov100", "c20_cov030", "Safe120")
    no_rev = st.median(d120_c) >= 0
    ok9 = (len(c_h) == 3 and all(x < 0 for x in c_h)
           and abs(ratio_c - ratio_a) < 0.15 and no_rev)
    check("第三口径复现: LLM 伤害 + 机理比值 + 反转不出现", ok9,
          "ΔSafe120(llm) 3/3 为负: %s; 中介/结果比值 c20=%.2f vs 831=%.2f; "
          "ΔSafe120(cov100)=%+.5f (非负: %s)"
          % (all(x < 0 for x in c_h), ratio_c, ratio_a, st.median(d120_c), no_rev))

    print("=" * 72)
    if FAILED:
        print("结果: %d 项失败 -> %s" % (len(FAILED), FAILED))
        sys.exit(1)
    print("结果: 全部 %d 项通过" % TOTAL)


if __name__ == "__main__":
    main()
