"""Create a narrated demo using real command outputs and simulation samples.

This is an edited CLI-output replay, not a recording of a nonexistent web UI.
Requires macOS say; all Python execution runs in the pulse Conda environment.
"""

from pathlib import Path
from functools import lru_cache
import csv
import json
import math
import os
import re
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/os2026"
WORK = ROOT / "tmp/os2026_video"
WORK.mkdir(parents=True, exist_ok=True)
FONT = os.environ.get("PULSE_CJK_FONT", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
LATIN = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 4
BG, PANEL, TEAL, ORANGE = "#0D2631", "#163642", "#47D3C3", "#F4B073"
WHITE, GRAY = "#F0F7F8", "#B5CDD5"
E = json.loads((OUT / "evidence.json").read_text())
M = json.loads((OUT / "mechanism/summary.json").read_text())
C = json.loads((OUT / "city/summary.json").read_text())
FRAMES = dict(np.load(OUT / "city/frames.npz"))
with (OUT / "mechanism/queue_series.csv").open() as f:
    QUEUES = list(csv.DictReader(f))

SCENES = [
    {"kind": "intro", "title": "PULSE", "subtitle": "AI 辅助疏散策略仿真与评估", "badge": "作品演示",
     "voice": "这是 PULSE，一个开源的疏散策略仿真与评估工具，参赛方向是 AI 加工业软件。面向工业园区应急规划，它帮助比较分流、信息传播和容量约束。本视频展示真实命令执行结果，以及由运行输出生成的可视化回放。"},
    {"kind": "setup", "title": "01  安装与启动", "subtitle": "Conda 环境 / Python 包 / 命令行入口", "badge": "使用流程",
     "voice": "首先，在 Conda 环境中安装项目。基础机理模型不需要显卡或模型权重；城市演示使用 NumPy 和 PyTorch。运行版本命令，可以确认当前为零点一版本。下面从策略实验开始。"},
    {"kind": "mechanism", "title": "02  运行策略比较", "subtitle": "真实命令输出节选 / 20 个候选策略", "badge": "本次实跑",
     "voice": "执行 pulse explore，程序自动运行基准和二十个候选策略，并导出 JSON、CSV 和图表。选中的是预置参考策略，随后使用三个随机种子检查结果。这一步是机理实验，不是大模型自动生成控制策略。"},
    {"kind": "queue", "title": "03  读取结果，比较收益与代价", "subtitle": "1,000 辆输入需求 / 共同坐标尺度", "badge": "本次实跑",
     "voice": "在这一千辆需求的简化模型中，完成率由百分之七十二点二五提高到百分之百；峰值队列由六百点六零降至三百二十六点六七辆，且不再出现回溢。这是模型内的比较结果，不能直接解释为真实园区收益。"},
    {"kind": "boundary", "title": "04  扫描需求，识别适用范围", "subtitle": "固定选中策略 / 需求从 500 辆增加到 1,500 辆", "badge": "本次实跑",
     "voice": "继续查看需求扫描。同一策略在一千一百辆需求时仍然稳定，一千三百辆时完成率降到百分之八十五点五四，一千五百辆出现回溢。因此，工具不仅展示一个成功案例，也帮助识别策略失效的范围。"},
    {"kind": "city", "title": "05  运行居民级场景", "subtitle": "4 × 4 合成街区 / 1,600 人 / 960 个名额", "badge": "本次实跑",
     "voice": "运行城市演示后，画面按保存的街区采样帧加速回放。每个街区一百人，避难容量六十人。最终九百六十人避难，六百三十七人在途，三人未出发。人口守恒误差和超容避难所数均为零，容量不足被明确保留在结果中。"},
    {"kind": "ai", "title": "06  AI 协调与输出约束", "subtitle": "本地模型接口已实现 / 本段演示回复拒绝测试", "badge": "本次测试",
     "voice": "AI 层通过本地模型给出候选避难所排序，再更新居民信念。仿真器独立执行人口和容量约束。这里实际运行回复拒绝测试：不存在的候选编号和无结构回复都不能改变信念。本次没有启动新的模型推理。"},
    {"kind": "evidence", "title": "07  核验样例，保留反例", "subtitle": "同口径、同种子配对 / 48 份既有样例", "badge": "样例核验",
     "voice": "最后执行证据核验，九项检查全部通过。既有大规模样例还显示，某个 AI 策略虽然缩短了已避难者的步行距离，却降低了最终避难比例。保留这类反例，才能判断 AI 建议是否真正改善整体结果。这些样例本次未重新运行。"},
    {"kind": "end", "title": "PULSE  /  开源、运行、复核", "subtitle": "2026 上海开源软件应用创新大赛 · AI+ 工业软件赛道", "badge": "交付入口",
     "voice": "以上完成了从运行策略实验、查看结果、居民级仿真，到 AI 约束和证据核验的完整流程。代码、介绍文档、视频和运行证据统一发布在 GitHub。当前项目是可复现的研究原型，下一步是园区数据接入与实测校准。"},
]
LAST_CONTENT = None


@lru_cache(None)
def font(size, kind="cjk"):
    return ImageFont.truetype({"cjk": FONT, "latin": LATIN, "mono": MONO}[kind], size,
                              layout_engine=ImageFont.Layout.BASIC)


def txt(d, xy, value, size=30, color=WHITE, kind="cjk"):
    d.text(xy, str(value), fill=color, font=font(size, kind))


@lru_cache(maxsize=2048)
def wrap(s, width, size=30, kind="cjk"):
    lines, line = [], ""
    f = font(size, kind)
    for ch in str(s):
        if ch == "\n":
            lines.append(line)
            line = ""
        elif f.getlength(line+ch) > width:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def paragraph(d, x, y, s, width, size=30, color=WHITE, spacing=1.55):
    for line in wrap(s, width, size):
        txt(d, (x, y), line, size, color)
        y += int(size*spacing)
    return y


def card(d, x, y, w, h, title, value, detail=""):
    d.rounded_rectangle((x, y, x+w, y+h), radius=20, fill=PANEL)
    txt(d, (x+26, y+20), title, 26, GRAY)
    value_kind = "cjk" if any(ord(ch) > 127 for ch in value) else "latin"
    value_size = 48
    while font(value_size, value_kind).getlength(value) > w-52:
        value_size -= 1
    txt(d, (x+26, y+64), value, value_size, TEAL, value_kind)
    if detail:
        paragraph(d, x+26, y+128, detail, w-52, 23, GRAY)


def terminal(d, x, y, w, h, command, lines, progress=1.0, size=26):
    d.rounded_rectangle((x, y, x+w, y+h), radius=20, fill="#071C25", outline="#2A4D59", width=2)
    for i, col in enumerate(["#E88577", "#EBCB77", "#77C6A1"]):
        d.ellipse((x+24+i*24, y+20, x+35+i*24, y+31), fill=col)
    txt(d, (x+112, y+10), "PULSE  ·  CLI 输出回放", 20, GRAY)
    command_lines = wrap("$ "+command, w-48, size, "mono")
    yy = y+60
    for line in command_lines:
        txt(d, (x+24, yy), line, size, TEAL, "mono")
        yy += size+12
    yy += 14
    visible = max(1, min(len(lines), math.ceil(len(lines)*progress)))
    for line in lines[:visible]:
        # CJK fallback handles real Chinese CLI output.
        for subline in wrap(line, w-48, size):
            if yy+size > y+h-18:
                return
            txt(d, (x+24, yy), subline, size, WHITE)
            yy += size+10


def base(scene, index):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    txt(d, (72, 35), "PULSE  /  OS2026", 25, TEAL, "latin")
    d.rounded_rectangle((1645, 28, 1848, 78), radius=12, fill=PANEL)
    txt(d, (1675, 37), scene["badge"], 27, TEAL)
    txt(d, (72, 113), scene["title"], 54, WHITE, "latin" if scene["kind"] == "intro" else "cjk")
    txt(d, (75, 191), scene["subtitle"], 29, GRAY)
    d.line((72, 250, 1848, 250), fill="#2E4B57", width=2)
    txt(d, (72, 1028), "真实命令输出与数据回放 · 中文配音 · 2026.10.13", 21, GRAY)
    txt(d, (1775, 1028), f"{index+1:02d} / 09", 21, GRAY, "latin")
    return im


def render(index, p, subtitle):
    global LAST_CONTENT
    scene = SCENES[index]
    updates = {"intro":1,"setup":10,"mechanism":20,"queue":90,"boundary":12,"city":6,"ai":20,"evidence":20,"end":1}[scene["kind"]]
    key = (index, int(p*updates))
    if LAST_CONTENT is not None and LAST_CONTENT[0] == key:
        return decorate(LAST_CONTENT[1].copy(), p, subtitle)
    im = base(scene, index)
    d = ImageDraw.Draw(im)
    kind = scene["kind"]
    if kind == "intro":
        paragraph(d, 76, 302, "让每个应急策略\n都能接受可复现实验的检验", 1090, 60)
        txt(d, (80, 517), "策略比较  →  居民级仿真  →  AI 约束  →  证据核验", 33, TEAL)
        for x, title, value, detail in [(76, "候选控制策略", "20", "标准库机理模型"), (661, "合成场景居民", "1,600", "CPU 端到端运行"), (1246, "既有实验样例", "48", "独立口径与配对分析")]:
            card(d, x, 610, 550, 202, title, value, detail)
        for row in range(4):
            for col in range(4):
                x, y = 1420+col*96, 318+row*66
                if col < 3:
                    d.line((x,y,x+96,y), fill="#345B68", width=3)
                if row < 3:
                    d.line((x,y,x,y+66), fill="#345B68", width=3)
                d.ellipse((x-8,y-8,x+8,y+8), fill=TEAL if (row+col)%3 else ORANGE)
    elif kind == "setup":
        terminal(d, 76, 291, 1772, 291, E["commands"][0]["command"], [E["commands"][0]["output"].strip()], min(1,p*5), 32)
        txt(d, (92, 625), "首次安装命令", 33, TEAL)
        for yy, line in [(682,"conda env create -f environment.yml"),(736,"conda run -n pulse python -m pip install -e '.[city,plots,dev]'")]:
            txt(d, (92, yy), line, 29, WHITE, "mono")
        txt(d, (92, 809), "已有 pulse 环境可直接运行；小型演示无须外部地图或推理服务。", 26, GRAY)
    elif kind == "mechanism":
        obj = {"baseline": {k:M["baseline"][k] for k in ["completion_rate","max_queue","spillback"]}, "best_trial": {"trial":M["best_trial"]["trial"],"control":M["best_trial"]["control"]}}
        lines = [
            '"baseline": '+json.dumps(obj["baseline"],ensure_ascii=False),
            '"best_trial": {',
            '  "trial": '+str(obj["best_trial"]["trial"])+',',
            '  "control": {',
            '    "signal_offsets": '+json.dumps(obj["best_trial"]["control"]["signal_offsets"])+',',
            '    "route_weights": '+json.dumps(obj["best_trial"]["control"]["route_weights"])+',',
            '    "departure_delay": '+str(obj["best_trial"]["control"]["departure_delay"]),
            '  }',
            '}',
        ]
        terminal(d, 76, 285, 1130, 566, "conda run -n pulse pulse-explore --output output/os2026/mechanism", lines, min(1,.15+p*2.4), 25)
        card(d, 1246, 289, 600, 221, "结果文件", "JSON / CSV / SVG", "汇总、候选、需求扫描、队列时序")
        paragraph(d, 1272, 556, "控制量\n信号偏移：8 / 22 秒\n路径权重：0.34 / 0.33 / 0.33\n出发延迟参数：0.70", 548, 29)
        txt(d, (1272, 797), "第 3 个候选为预置参考控制", 26, ORANGE)
    elif kind == "queue":
        d.rounded_rectangle((76,286,1240,842),radius=20,fill=PANEL)
        left, top, right, bottom = 184, 348, 1190, 758
        for val in range(0,701,100):
            y=bottom-val/700*(bottom-top)
            d.line((left,y,right,y),fill="#34525E",width=1)
            txt(d,(left-68,y-17),str(val),24,GRAY)
        tmax=max(float(r["time_s"]) for r in QUEUES)
        for val in [0,5,10,15,20,25,30]:
            x=left+val*60/tmax*(right-left)
            if x<=right+1:
                txt(d,(x-8,bottom+16),str(val),24,GRAY)
        txt(d,(145,302),"队列（辆）",23,GRAY)
        txt(d,(872,799),"仿真时间（分钟）",25,GRAY)
        n=max(2,int(len(QUEUES)*min(1,.1+p*1.5)))
        for key,col,label,xx in [("baseline_queue",ORANGE,"无干预基准",570),("selected_queue",TEAL,"选中策略",884)]:
            pts=[(left+float(r["time_s"])/tmax*(right-left),bottom-float(r[key])/700*(bottom-top)) for r in QUEUES[:n]]
            d.line(pts,fill=col,width=5)
            d.line((xx,317,xx+40,317),fill=col,width=5)
            txt(d,(xx+52,298),label,26,WHITE)
        card(d,1280,289,566,213,"完成率","72.25% → 100%","同一模型、同一输入需求")
        card(d,1280,525,566,213,"峰值队列（辆）","600.60 → 326.67","下降 45.61%；回溢由有变无")
        txt(d,(1305,789),"简化模型结果，尚未实测校准",26,ORANGE)
    elif kind == "boundary":
        left,top,right,bottom=195,349,1187,747
        for val in [60,70,80,90,100]:
            y=bottom-(val-60)/45*(bottom-top)
            d.line((left,y,right,y),fill="#355460",width=2)
            txt(d,(left-83,y-19),str(val)+"%",26,GRAY)
        pts=[]
        for r in M["demand_scan"]:
            x=left+(r["demand"]-500)/1000*(right-left)
            y=bottom-(r["completion_rate"]*100-60)/45*(bottom-top)
            pts.append((x,y))
            txt(d,(x-36,bottom+24),str(r["demand"]),25,GRAY)
        d.line(pts,fill=TEAL,width=5)
        for i,(x,y) in enumerate(pts):
            if p*7>=i:
                d.ellipse((x-10,y-10,x+10,y+10),fill=TEAL)
                txt(d,(x-44,y-53),f"{M['demand_scan'][i]['completion_rate']*100:.1f}%",24,WHITE)
        txt(d,(151,295),"完成率",28,TEAL)
        txt(d,(806,813),"输入需求（辆）",26,GRAY)
        for i,(demand,result) in enumerate([(1100,"稳定"),(1300,"不稳定"),(1500,"出现回溢")]):
            card(d,1290,294+i*177,556,156,f"需求 {demand:,} 辆",result)
    elif kind == "city":
        j=min(len(FRAMES["t_min"])-1,int(p*len(FRAMES["t_min"])))
        txt(d,(91,277),f"采样帧 {j+1}/6 · 仿真 {FRAMES['t_min'][j]:.2f} 分钟",27,TEAL)
        x0,y0,dx,dy=207,395,221,122
        for row in range(4):
            for col in range(4):
                k=row*4+col
                x,y=x0+col*dx,y0+row*dy
                if col<3:d.line((x,y,x+dx,y),fill="#335461",width=7)
                if row<3:d.line((x,y,x,y+dy),fill="#335461",width=7)
                n=int(FRAMES["sheltered"][j,k])
                d.rounded_rectangle((x-76,y-44,x+76,y+44),radius=13,fill=TEAL if n>=60 else "#2B6870")
                txt(d,(x-46,y-23),f"{n}/60",29,BG if n>=60 else WHITE,"latin")
                txt(d,(x-55,y+49),f"街区 {k+1:02d}",19,GRAY)
        txt(d,(92,839),"每格为该街区已避难人数 / 避难名额；使用保存的采样值。",24,GRAY)
        terminal(d,1113,283,732,235,E["commands"][2]["command"],["PULSE city demo passed: 1,600 residents", "output: <PROJECT>/output/os2026/city"],1,21)
        card(d,1113,537,732,153,"最终状态 / 30.5 分钟","960 已避难","637 在途 + 3 未出发 = 640 尚未避难")
        card(d,1113,703,732,153,"人口守恒误差 / 超容避难所数","0 / 0")
    elif kind == "ai":
        boxes=[("局部观测", "分区居民 / 容量信息"),("本地 LLM", "对候选避难所排序"),("校验与广播", "检查编号 / 更新信念"),("物理引擎", "状态推进 / 容量接纳")]
        for i,(title,detail) in enumerate(boxes):
            x=76+i*448
            d.rounded_rectangle((x,294,x+417,436),radius=18,fill=PANEL)
            txt(d,(x+24,314),title,33,TEAL)
            txt(d,(x+24,376),detail,25,GRAY)
            if i<3:txt(d,(x+423,337),"→",28,TEAL)
        lines=[s for s in E["commands"][3]["output"].splitlines() if s.strip()]
        terminal(d,76,475,1772,297,E["commands"][3]["command"],lines,min(1,.25+p*3),24)
        txt(d,(90,809),"候选 [1, 2] → 拒绝编号 999；无结构回复被拒绝；applied = 0",29,ORANGE)
        txt(d,(90,858),"验证接口拒绝路径；本次未启动真实模型推理。",23,GRAY)
    elif kind == "evidence":
        lines=[s for s in E["commands"][4]["output"].splitlines() if s.startswith("[PASS]")]
        short=[s.split("  ——")[0] for s in lines]+["结果: 全部 9 项通过"]
        terminal(d,76,290,1040,555,E["commands"][4]["command"],short,min(1,.2+p*2),25)
        txt(d,(1160,303),"一个需要保留的反例",35,TEAL)
        paragraph(d,1160,374,"c20_llm 相对 c20_cov030\n同口径、种子 42 / 43 / 44\n配对差中位数",664,27,GRAY)
        card(d,1155,531,688,163,"已避难者步行距离中位数","-198.56 m")
        card(d,1155,710,688,147,"120 分钟避难比例","-1.456 个百分点")
    elif kind == "end":
        paragraph(d,80,302,"运行得起来\n结论查得到\n边界说得清",750,65)
        txt(d,(85,675),"AGPL-3.0-only  ·  CLI + Python API",33,TEAL,"latin")
        txt(d,(85,735),"当前阶段：研究原型；园区数据接入与校准为后续计划。",27,GRAY)
        d.rounded_rectangle((996,305,1846,838),radius=24,fill=PANEL)
        txt(d,(1037,347),"代码与参赛材料",40,TEAL)
        txt(d,(1037,422),"github.com/elsewhere-high/PULSE",31,WHITE,"latin")
        paragraph(d,1037,500,"Release: os2026-submission-v1\n\n作品介绍 PDF\n中文演示视频与字幕\n命令输出、仿真结果与校验摘要",760,30)
    LAST_CONTENT = (key, im.copy())
    return decorate(im, p, subtitle)


def decorate(im, p, subtitle):
    # Burn in exactly the same timed captions as the companion SRT.
    d = ImageDraw.Draw(im)
    d.rectangle((0,920,W,1010),fill="#071B23")
    lines=wrap(subtitle,1740,34)
    if len(lines)>2:raise ValueError("Subtitle exceeds two lines")
    yy=937 if len(lines)==1 else 918
    for line in lines:
        xx=(W-font(34).getlength(line))/2
        txt(d,(xx,yy),line,34,WHITE)
        yy+=42
    d.rectangle((72,1009,1848,1014),fill="#2C4B58")
    d.rectangle((72,1009,72+1776*p,1014),fill=TEAL)
    return im


def run(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)


def srt_time(t):
    ms=round(t*1000)
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"


def build():
    chapters=[]
    captions=[]
    duration_total=0.0
    rebuild = os.environ.get("PULSE_REBUILD_VIDEO_SCENES")
    rebuild_ids = {int(i) for i in rebuild.split(",")} if rebuild else None
    for i,s in enumerate(SCENES):
        stem=WORK/f"scene_{i:02d}"
        stem.with_suffix(".txt").write_text(s["voice"],encoding="utf-8")
        if not stem.with_suffix(".wav").exists():
            run(["say","-v","Tingting","-r","215","-f",str(stem.with_suffix(".txt")),"-o",str(stem.with_suffix(".aiff"))])
            run([FFMPEG,"-y","-i",str(stem.with_suffix(".aiff")),"-ar","48000","-ac","1",str(stem.with_suffix(".wav"))])
        with wave.open(str(stem.with_suffix(".wav"))) as wav:
            speech=wav.getnframes()/wav.getframerate()
        duration=math.ceil((speech+1.2)*FPS)/FPS
        pieces=[t for t in re.findall(r"[^。！？；]+[。！？；]?",s["voice"]) if t.strip()]
        chunks=[]
        for piece in pieces:
            # Split very long sentences at Chinese commas for readable captions.
            if len(piece)>62:
                part=""
                for bit in re.findall(r"[^，]+，?",piece):
                    if len(part)+len(bit)>55 and part:
                        chunks.append(part);part=""
                    part+=bit
                if part:chunks.append(part)
            else:chunks.append(piece)
        weights=[len(t) for t in chunks]
        local=[]
        cursor=.25
        for text_,weight in zip(chunks,weights):
            end=cursor+speech*weight/sum(weights)
            local.append((cursor,end,text_))
            captions.append((duration_total+cursor,duration_total+end,text_))
            cursor=end
        chapters.append({"start":round(duration_total,3),"duration":duration,"title":s["title"],"narration":s["voice"]})
        out=stem.with_suffix(".mp4")
        if rebuild_ids is not None and i not in rebuild_ids and out.exists():
            duration_total += duration
            continue
        print(f"Rendering {i+1}/{len(SCENES)} {duration:.1f}s",flush=True)
        proc=subprocess.Popen([FFMPEG,"-y","-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",str(stem.with_suffix(".wav")),"-af","apad","-t",str(duration),"-c:v","libx264","-preset","ultrafast","-threads","2","-crf","20","-r","24","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",str(out)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=(WORK/f"encode_{i:02d}.log").open("wb"))
        for frame in range(round(duration*FPS)):
            t=frame/FPS
            sub=next((v for a,b,v in local if a<=t<b), local[-1][2] if t>=local[-1][0] else "")
            img=render(i,t/duration,sub)
            proc.stdin.write(img.tobytes())
            if frame==round(duration*FPS*.55):
                img.save(WORK/f"preview_{i:02d}.png")
        proc.stdin.close()
        if proc.wait():raise RuntimeError(f"ffmpeg scene {i} failed")
        duration_total+=duration
    concat=WORK/"concat.txt"
    concat.write_text("\n".join(f"file '{(WORK/f'scene_{i:02d}.mp4').as_posix()}'" for i in range(len(SCENES))),encoding="utf-8")
    target=OUT/"PULSE_OS2026_Demo.mp4"
    run([FFMPEG,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy","-movflags","+faststart",str(target)])
    srt=OUT/"PULSE_OS2026_Demo.zh-CN.srt"
    srt.write_text("\n\n".join(f"{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{v}" for i,(a,b,v) in enumerate(captions))+"\n",encoding="utf-8")
    (OUT/"video_chapters.json").write_text(json.dumps({"format":"1920x1080 H.264/AAC", "fps":24,"render_fps":FPS,"duration_seconds":round(duration_total,3),"kind":"Edited replay of actual CLI outputs and saved simulation samples", "chapters":chapters},ensure_ascii=False,indent=2),encoding="utf-8")
    print(target, f"{duration_total:.1f} seconds",flush=True)


if __name__=="__main__":
    build()
