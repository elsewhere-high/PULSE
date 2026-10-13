"""Build the Chinese OS2026 project brief from captured evidence (Conda only)."""

from pathlib import Path
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/os2026"
PDFDIR = ROOT / "output/pdf"
ASSETS = OUT / "assets"
for p in [PDFDIR, ASSETS]:
    p.mkdir(parents=True, exist_ok=True)
FONT = Path(os.environ.get("PULSE_CJK_FONT", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"))
pdfmetrics.registerFont(TTFont("CJK", str(FONT)))
pdfmetrics.registerFontFamily("CJK", normal="CJK", bold="CJK", italic="CJK", boldItalic="CJK")
FP = FontProperties(fname=str(FONT))
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "text.color": "#17333D", "axes.labelcolor": "#17333D"})
MECH = json.loads((OUT / "mechanism/summary.json").read_text())
CITY = json.loads((OUT / "city/summary.json").read_text())
EVIDENCE = json.loads((OUT / "evidence.json").read_text())
REPO = "https://github.com/elsewhere-high/PULSE"
RELEASE = REPO + "/releases/tag/os2026-submission-v1"
TAG = "os2026-submission-v1"
NAVY, TEAL, ORANGE = "#122F3B", "#087F80", "#C77636"
INK, MUTED, PAPER, LINE = "#203B46", "#60747C", "#F5F8F8", "#DCE5E7"


def plot_fonts(ax):
    for item in [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()]:
        item.set_fontproperties(FP)
    ax.grid(axis="y", color=LINE, alpha=.85)
    ax.set_axisbelow(True)


def charts():
    with (OUT / "mechanism/queue_series.csv").open() as f:
        rows = list(csv.DictReader(f))
    t = np.array([float(r["time_s"]) for r in rows]) / 60
    fig, ax = plt.subplots(figsize=(9, 3.4), layout="constrained")
    for key, title, color in [("baseline_queue", "无干预基准", ORANGE), ("selected_queue", "选中策略", TEAL)]:
        ax.plot(t, [float(r[key]) for r in rows], lw=2.6, color=color, label=title)
    ax.set(xlabel="仿真时间（分钟）", ylabel="队列（辆）", ylim=(0, None))
    plot_fonts(ax)
    ax.legend(prop=FP, frameon=False, loc="upper right")
    fig.savefig(ASSETS / "queue.png", dpi=200, facecolor="white")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 3.5), layout="constrained")
    scan = MECH["demand_scan"]
    ax.plot([r["demand"] for r in scan], [r["completion_rate"] * 100 for r in scan], "o-", lw=2.5, color=TEAL)
    ax.axvspan(1100, 1300, color=ORANGE, alpha=.13)
    ax.set(xlabel="输入需求（辆）", ylabel="完成率（%）", ylim=(60, 106), xticks=[r["demand"] for r in scan])
    plot_fonts(ax)
    fig.savefig(ASSETS / "demand.png", dpi=200, facecolor="white")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 3.5), layout="constrained")
    eva = np.array(CITY["eva_series"])
    ax.stackplot((eva[:, 0] + 1) / 6, eva[:, 3], eva[:, 2], eva[:, 1],
                 labels=["已避难", "在途", "未出发"], colors=[TEAL, ORANGE, "#CDD9DF"], alpha=.92)
    ax.axhline(960, color=NAVY, ls="--", lw=1.3)
    ax.set(xlabel="仿真时间（分钟，含预热）", ylabel="人数", ylim=(0, 1700))
    plot_fonts(ax)
    ax.legend(prop=FP, frameon=False, loc="upper right", ncol=3)
    fig.savefig(ASSETS / "city.png", dpi=200, facecolor="white")
    plt.close(fig)


W, H = 595.276, 841.89
C = None
PAGE = 0


def fill(color):
    C.setFillColor(colors.HexColor(color))


def rect(x, y, w, h, color, radius=0):
    fill(color)
    C.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=0)


def text(x, y, s, size=11, color=INK, font="CJK"):
    fill(color)
    C.setFont(font, size)
    C.drawString(x, H-y-size, s)


def para(s, x=44, y=160, w=507, size=11, color=INK, leading=None):
    p = Paragraph(s, ParagraphStyle("p", fontName="CJK", fontSize=size, leading=leading or size*1.65,
                                   textColor=colors.HexColor(color), wordWrap="CJK"))
    _, height = p.wrap(w, 900)
    if y+height > 786:
        raise ValueError(f"Page {PAGE}: text overflows: {s[:60]}")
    p.drawOn(C, x, H-y-height)
    return y+height


def label(s, x, y, color=TEAL):
    text(x, y, s, 9, color)


def box(x, y, w, h, title, body, accent=TEAL):
    rect(x, y, w, h, PAPER, 8)
    rect(x, y, 4, h, accent, 2)
    text(x+16, y+15, title, 13, accent)
    para(body, x+16, y+42, w-32, 10.4)


def metric(x, y, w, value, title, detail="", dark=False):
    rect(x, y, w, 97, "#1C4350" if dark else PAPER, 8)
    text(x+16, y+12, value, 25, "#FFFFFF" if dark else TEAL, "Helvetica-Bold")
    text(x+16, y+47, title, 10.6, "#E5F2F3" if dark else INK)
    if detail:
        text(x+16, y+70, detail, 8.6, "#AFC9D1" if dark else MUTED)


def begin(section, title, subtitle):
    global PAGE
    if PAGE:
        C.showPage()
    PAGE += 1
    rect(0, 0, W, H, "#FFFFFF")
    text(44, 25, "PULSE  /  OS2026", 9, TEAL, "Helvetica-Bold")
    text(355, 25, "AI+ 工业软件赛道 · 作品介绍", 8.5, MUTED)
    rect(44, 51, 507, 1, LINE)
    label(section, 44, 72)
    text(44, 93, title, 25, NAVY)
    para(subtitle, 44, 133, 507, 10.5, MUTED)
    rect(44, 798, 507, 1, LINE)
    text(44, 809, "2026.10.13  |  v0.1.0  |  开源仿真与策略评估", 8, MUTED)
    text(512, 807, f"{PAGE:02d} / 09", 9, MUTED, "Helvetica")


def image(path, x, y, w, h):
    C.drawImage(str(path), x, H-y-h, width=w, height=h, preserveAspectRatio=True, anchor="c", mask="auto")


def table(y, cols, widths, rows, row_h=38):
    x = 44
    rect(x, y, sum(widths), 31, NAVY, 5)
    for title, width in zip(cols, widths):
        text(x+10, y+9, title, 9.5, "#FFFFFF")
        x += width
    for i, row in enumerate(rows):
        x = 44
        yy = y+31+i*row_h
        rect(x, yy, sum(widths), row_h, PAPER if i % 2 == 0 else "#FFFFFF")
        for value, width in zip(row, widths):
            para(str(value), x+10, yy+9, width-20, 9.5, leading=14)
            x += width
    return y+31+len(rows)*row_h


def build():
    global C, PAGE
    charts()
    path = PDFDIR / "PULSE_OS2026_Project_Introduction.pdf"
    pending = path.with_suffix(".pending.pdf")
    C = canvas.Canvas(str(pending), pagesize=(W, H), pageCompression=1)
    C.setTitle("PULSE | AI 辅助疏散策略仿真与评估 | 2026 上海开源软件应用创新大赛")
    C.setAuthor("PULSE 开源项目 / Ustinian5")
    C.setSubject("AI+ 工业软件赛道作品介绍：背景、架构、场景、创新、实跑验证与开源治理")
    PAGE = 1
    rect(0, 0, W, H, NAVY)
    for i in range(5):
        for j in range(4):
            x, y = 370+i*35, 260+j*35
            if i < 4:
                rect(x, y, 35, 1, "#2A5360")
            if j < 3:
                rect(x, y, 1, 35, "#2A5360")
            rect(x-3, y-3, 7, 7, TEAL if (i+j)%3 else ORANGE, 3)
    label("2026 上海开源软件应用创新大赛", 44, 48, "#D6E9EA")
    text(42, 117, "PULSE", 76, "#FFFFFF", "Helvetica-Bold")
    text(46, 221, "AI 辅助疏散策略", 29, "#FFFFFF")
    text(46, 265, "仿真与评估", 29, "#FFFFFF")
    para("面向工业园区应急规划的开源研究工具<br/>用可复现实验检验策略收益、容量瓶颈与 AI 决策边界。", 46, 344, 500, 12.2, "#C0D8DF", 22)
    rect(46, 427, 263, 32, TEAL, 5)
    text(59, 435, "AI+ 工业软件赛道  /  自主选题", 10.5, "#FFFFFF")
    metric(46, 512, 159, "20", "候选控制策略", "机理实验实跑", True)
    metric(218, 512, 159, "1,600", "合成场景居民", "CPU 端到端实跑", True)
    metric(390, 512, 159, "48", "既有实验样例", "守恒与容量核验", True)
    para("作品形态：Python 包、命令行、结构化结果与可视化图表。<br/>当前阶段：研究原型，已提供可运行演示；园区接入与实测校准列入后续计划。", 46, 650, 503, 10.4, "#C0D8DF")
    text(46, 751, "AGPL-3.0-only  |  2026.10.13  |  PULSE v0.1.0", 10, "#C0D8DF", "Helvetica")
    text(46, 777, "github.com/elsewhere-high/PULSE", 10, "#FFFFFF", "Helvetica")
    C.linkURL(REPO, (46, H-795, 330, H-775), relative=0)

    begin("01 / 项目背景与应用场景", "把应急预案变成可检验的实验", "面向工程流程与决策问题，服务工业园区人员疏散和应急资源规划。")
    para("制造园区、能源基地与仓储物流园区需要比较分流、广播、集结点容量和道路受损等方案。仅凭距离最短或单次模拟，难以看清拥堵转移、信息不充分和资源不足带来的后果。PULSE 将这些问题拆成固定输入、可控策略、多指标结果与可追溯证据。", y=179)
    box(44, 286, 244, 137, "预案评估", "比较出发时序、路径权重和信息覆盖；观察完成率、队列峰值与回溢。适用于方案形成前的情景筛选。")
    box(303, 286, 248, 137, "容量与通路压力测试", "在给定容量下观察未避难人数；用道路损伤参数构造受阻情景，识别资源或拓扑瓶颈。", ORANGE)
    box(44, 440, 244, 137, "AI 协调策略验证", "对比规则策略与本地大模型协调；同时追踪早晚期避难比例、满员拒入、换目标和步行距离。")
    box(303, 440, 248, 137, "科研与教学复现", "CPU 合成场景开箱运行；使用随机种子、输入口径和结果表复核结论，支持实验课程与算法研究。")
    para("场景落地方式", y=612, size=15, color=TEAL)
    para("由场景方提供经授权的园区路网、分区人数和集结点容量，转换为统一数组输入；在离线仿真中筛选方案，再用演练记录校准。当前随附的是合成 Demo 与城市实验样例，尚无已验证的园区客户案例。", y=646)
    para("能力边界：尚未实现 CAD/BIM、工业互联网平台接入、室内烟气模型或真实应急调度。", y=741, size=9, color=MUTED)

    begin("02 / 技术架构", "双层仿真引擎，共用证据输出", "机理模型负责低成本策略筛选；居民级引擎负责个体行为、网络与容量约束。")
    box(44, 179, 507, 84, "输入层", "控制量与随机种子  /  NPZ 街区、人口、拓扑、避难所与容量  /  来源与输入哈希")
    text(287, 266, "↓", 18, TEAL)
    box(44, 294, 244, 153, "机理模型 · 标准库", "model.py + experiment.py<br/>信号偏移、路径权重、出发延迟<br/>20 次候选比较、3 个种子、需求扫描<br/>输出完成率、队列、振荡与回溢")
    box(303, 294, 248, 153, "居民级引擎 · NumPy / PyTorch", "AgentSwarm + SwarmStepper<br/>街区路由、居民状态、知识传播<br/>容量接纳、满员拒入、轨迹与事件<br/>CPU 小场景 / GPU 大规模实验")
    box(44, 465, 507, 102, "AI 协调层 · 可选，仅接入居民级引擎", "LeaderTier → 本地 llama.cpp /completion → 候选编号语法约束 → 回包校验 → 更新居民信念。AI 改变信息与偏好，人口状态推进和容量接纳仍由仿真器执行。")
    text(287, 574, "↓", 18, TEAL)
    box(44, 603, 507, 101, "实验与证据层", "JSON / CSV / SVG / NPZ → 同口径同种子配对 → 多指标分析 → 守恒、容量与可再生性校验。既有样例与本次新运行结果分别保存。")
    para("接口：pulse-explore、Python API、scripts/bench_swarm.py。基础包无第三方依赖；城市与绘图依赖按需安装。当前没有网页前端。", y=729, size=10, color=MUTED)

    begin("03 / 核心功能与使用流程", "从安装到验证，一条可复现路径", "所有 Python 命令均在 Conda 环境执行；小型 Demo 无须外部地图或模型权重。")
    steps = [
        ("1  建立运行环境", "conda env create -f environment.yml", "conda run -n pulse python -m pip install -e '.[city,plots,dev]'", "已有 pulse 环境时跳过创建步骤。"),
        ("2  比较控制策略", "conda run -n pulse pulse-explore", "", "生成 summary.json、trials.json、两份 CSV 与两张 SVG。"),
        ("3  运行居民级场景", "conda run -n pulse python scripts/run_city_demo.py", "", "生成城市汇总、6 个街区采样帧与 100 人抽样轨迹。"),
        ("4  验证实验与样例", "conda run -n pulse python scripts/verify_evidence_chain.py", "", "检查守恒、容量、48 份样例、分析表再生和配对结论。"),
    ]
    for i, (title, command, cmd2, body) in enumerate(steps):
        yy = 183+i*138
        rect(44, yy, 507, 123, PAPER, 8)
        text(58, yy+11, title, 13, TEAL)
        text(58, yy+40, command, 8.1, INK, "Courier")
        if cmd2:
            text(58, yy+58, cmd2, 7.7, INK, "Courier")
        para(body, 58, yy+83, 479, 9.4, MUTED)
    para("本次演示使用 output/os2026/ 保存独立输出，未覆盖随附回归样例。大规模城市与真实 LLM 推理需要另外配置硬件、输入和本地服务。", y=749, size=9, color=MUTED)

    begin("04 / 机理模型实跑", "多指标比较，检查策略适用范围", "输入需求 1,000 辆；搜索种子 2026，评估种子 7，验证种子 7 / 17 / 29。")
    b, m = MECH["baseline"], MECH["best_trial"]["metrics"]
    table(181, ["指标", "无干预基准", "选中策略"], [203, 152, 152], [
        ["完成率", f"{b['completion_rate']*100:.2f}%", f"{m['completion_rate']*100:.2f}%"],
        ["峰值队列（辆）", f"{b['max_queue']:.2f}", f"{m['max_queue']:.2f}"],
        ["回溢 / 守恒误差", "是 / 0", "否 / 0"],
    ])
    image(ASSETS / "queue.png", 42, 340, 511, 200)
    reduction = (1-m["max_queue"]/b["max_queue"])*100
    para(f"该设置下峰值队列降低 {reduction:.2f}%，完成率提高 {(m['completion_rate']-b['completion_rate'])*100:.2f} 个百分点。选中的是第 3 个候选，即代码中预置的参考控制：信号偏移 8 / 22 秒、路径权重 0.34 / 0.33 / 0.33、出发延迟参数 0.70。", y=550, size=10.5)
    box(44, 644, 507, 108, "把模型有效性与工程收益分开", "这些结果来自简化的排队机理模型。候选中包含人工参考控制，不能称为 AI 自主发现；三个种子结果相同也不等于外部场景验证。需求扫描显示 1,100 辆仍稳定、1,300 辆不稳定，仅得到区间内的候选边界。", ORANGE)
    para("证据：output/os2026/mechanism/summary.json、queue_series.csv、demand_scan.csv。", y=769, size=8.5, color=MUTED)

    begin("05 / 居民级仿真实跑", "容量不足，会明确体现在结果中", "4 × 4 合成街区，每区 100 人、60 个避难名额；CPU，seed=42，180 步加 3 步预热。")
    metric(44, 184, 160, "960 / 1,600", "已避难 / 总人数", "避难容量利用率 100%")
    metric(218, 184, 160, "640", "尚未避难", "637 人在途，3 人未出发")
    metric(392, 184, 159, "0 / 0", "守恒误差 / 超容数", "最终仿真时刻 30.5 分钟")
    image(ASSETS / "city.png", 42, 309, 511, 214)
    para("演示结果表明：仿真器遵守 960 人的接纳上限，不会因策略或传播信息而制造额外容量。16 个避难所均未超容；960 + 637 + 3 = 1,600，全部居民均可核算。", y=545)
    box(44, 629, 507, 105, "输出可复核、可复用", "summary.json 保留人数状态与配置；frames.npz 保存街区采样帧；traj3d.npz 保存 100 人抽样轨迹。视频由本次实际运行的这些输出生成回放。合成场景用于程序与流程验证，不代表真实园区疏散效率。")
    para("本次 CPU Demo 未启用 LLM。进程总耗时包含导入与初始化，视频不将其换算为跨设备性能承诺。", y=755, size=9, color=MUTED)

    begin("06 / AI 协调与结果审计", "让 AI 建议接受物理约束与效果检验", "已实现本地大模型接口、分区协调、候选语法约束与决策诊断。")
    box(44, 182, 507, 104, "AI 工作流", "分区观测与邻区交流 → 整理有容量的候选避难所 → 请求本地模型排序 → 校验候选编号和回复 → 更新广播与居民信念 → 仿真器继续推进与接纳。模型权重单独获取，不随仓库分发。")
    para("本次可直接复验的 AI 边界", y=307, size=15, color=TEAL)
    para("实际运行 test_invalid_leader_reply_cannot_change_belief：候选为 [1, 2] 时，编号 999 被计为非法；无结构回复被计为不可解析；两次回复的执行数均为 0。该演示验证回包校验路径，未进行新的模型推理。", y=342, size=10.7)
    para("既有 LLM 实验提示：局部收益可能伴随总体损失", y=440, size=14, color=TEAL)
    table(478, ["同口径配对指标", "c20_llm - c20_cov030"], [285, 222], [
        ["已避难者步行距离中位数", "-198.56 米"],
        ["120 分钟避难比例", "-1.456 个百分点"],
        ["已避难总人数", "-303,998 人"],
    ], row_h=34)
    para("表中为 chengdu_census2020 口径、种子 42 / 43 / 44 的配对差中位数，来自既有样例，三项方向均为 3/3 一致。它说明应同时评估距离与最终避难效果，不能据此概括所有 LLM 策略，也不能当作新的实测结果。", y=625, size=10.4)
    para("规模口径：该输入含 20,937,757 名合成居民、66,546 个街区、1,252 个避难所。大规模样例本次仅核验，未重新执行。", y=719, size=9.5, color=MUTED)
    para("证据：results/effect_summary.csv、DATA_DICTIONARY.md；src/pulse/simulator/llm_leaders.py。", y=771, size=8.2, color=MUTED)

    begin("07 / 创新点与开源治理", "把策略、约束和证据放在同一流程", "创新主张以现有代码和可复核实验为依据，不作首创或行业领先的无证据比较。")
    for y, title, body in [
        (183, "01  分层验证，降低实验门槛", "标准库机理模型先检查控制逻辑，居民级引擎再表达网络、信息与容量。小场景 CPU 运行，大场景使用 PyTorch；不同精度层各自保留假设。"),
        (309, "02  AI 影响行为，物理约束独立执行", "分区领导协调与局部信息传播作用于居民信念；候选编号检查和容量接纳共同限定执行范围，避免将语言模型直接作为物理状态修改器。"),
        (435, "03  支持反例的实验工作流", "固定口径、配对种子、多指标输出与逐字节表格再生。既记录正向结果，也保留 AI 策略造成效果退化的样例，让失败可以被复核。"),
    ]:
        box(44, y, 507, 111, title, body)
    para("开源交付与协作", y=570, size=15, color=TEAL)
    para("原创代码采用 AGPL-3.0-only，包含安装、运行、开发说明和贡献指南。通过 Issue 描述可复现问题，通过 PR 评审修改；贡献应保持人口守恒、容量边界、数据来源和配对实验口径。Release 固定展示文件、原始输出与校验摘要。", y=603, size=10.5)
    para("第三方边界：OSM 与 WorldPop 保留各自署名和条款；模型权重不打包。既有避难所坐标被记录为 AMap 衍生，但精确来源署名尚未澄清；容量为情景假设。该问题是数据来源待完善项，不能宣称全部外部数据权属已完成确认。", y=702, size=9.5, color=MUTED)

    begin("08 / 后续发展与评审入口", "从可运行研究原型走向园区验证", "后续计划按验证目标推进；以下均为计划项，不作为已交付功能。")
    table(180, ["阶段", "工作与验收目标"], [100, 407], [
        ["输入与校准", "补齐外部数据署名，接入获授权的小型园区路网、人数与容量；用演练记录校准关键参数。"],
        ["算法与接口", "补充 AI 策略消融与跨场景评估；探索 SUMO/TraCI 和园区平台数据适配，报告有效范围。"],
        ["工程与社区", "建设持续集成与版本化基准；完善可视化审阅入口、贡献评审和发布机制。"],
    ], row_h=61)
    para("评审复现入口", y=427, size=15, color=TEAL)
    para(f'代码仓库：<link href="{REPO}" color="{TEAL}">github.com/elsewhere-high/PULSE</link><br/>参赛 Release：<link href="{RELEASE}" color="{TEAL}">{TAG}</link><br/>演示视频：PULSE_OS2026_Demo.mp4（中文配音与字幕）<br/>源码基线：{EVIDENCE["source_commit"][:12]}；本次运行日期：2026-10-13。', y=461, size=10.4)
    para("关键证据与官方依据", y=582, size=15, color=TEAL)
    para("[1] README.md、docs/RUNNING.md、docs/DEVELOPMENT.md：运行与架构。<br/>[2] src/pulse/model.py、experiment.py、simulator/：功能实现。<br/>[3] output/os2026/evidence.json：本次命令、退出码、耗时与输出哈希。<br/>[4] results/DATA_DICTIONARY.md、effect_summary.csv：样例口径与效果。<br/>[5] THIRD_PARTY_NOTICES.md、data/DATA_SOURCES.md：数据来源与限制。", y=616, size=9.3, leading=16)
    para(f'[6] 大赛官方：<link href="https://www.oschina.net/os2026/" color="{TEAL}">www.oschina.net/os2026/</link>（查阅于 2026-10-13）。<br/>按官网要求提供代码、作品介绍和核心功能演示；当前公布的材料截止时间为 2026-10-16 24:00。具体提交以报名确认邮件指引为准。', y=717, size=9.3, leading=16)
    C.save()
    pending.replace(path)
    print(path)


if __name__ == "__main__":
    build()
