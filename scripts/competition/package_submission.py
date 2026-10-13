"""Package the verified PDF, video, evidence and submission links for a release."""

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/os2026"
PDF = ROOT / "output/pdf/PULSE_OS2026_Project_Introduction.pdf"
REPO = "https://github.com/elsewhere-high/PULSE"
TAG = "os2026-submission-v1"
RELEASE = REPO + "/releases/tag/" + TAG
DOWNLOAD = REPO + "/releases/download/" + TAG + "/"


def sha(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def timestamp(sec):
    return f"{int(sec)//60:02d}:{int(sec)%60:02d}"


def build():
    shutil.copyfile(PDF, OUT / PDF.name)
    video = json.loads((OUT / "video_chapters.json").read_text())
    evidence = json.loads((OUT / "evidence.json").read_text())
    for name, expected in evidence["files"].items():
        if sha(OUT / name) != expected:
            raise ValueError(f"Captured evidence changed: {name}")
    if not all(r["exit_code"] == 0 for r in evidence["commands"]):
        raise ValueError("A recorded command failed")
    evidence_zip = OUT / "PULSE_OS2026_Evidence.zip"
    evidence_paths = [OUT / "evidence.json", OUT / "video_chapters.json"]
    evidence_paths += [OUT / f"{r['name']}.txt" for r in evidence["commands"]]
    evidence_paths += [OUT / name for name in evidence["files"]]
    with zipfile.ZipFile(evidence_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(evidence_paths):
            z.write(path, str(Path("PULSE_OS2026_Evidence") / path.relative_to(OUT)))
    main_files = [OUT / PDF.name, OUT / "PULSE_OS2026_Demo.mp4", OUT / "PULSE_OS2026_Demo.zh-CN.srt", evidence_zip]
    checksums = "\n".join(f"{sha(path)}  {path.name}" for path in main_files) + "\n"
    links = f"""PULSE - 2026 上海开源软件应用创新大赛参赛材料

作品名称：PULSE - AI 辅助疏散策略仿真与评估
参赛赛道：AI+ 工业软件（自主选题）
材料日期：2026-10-13（Asia/Shanghai）

代码仓库：{REPO}
完整发布页：{RELEASE}
作品介绍 PDF：{DOWNLOAD}{PDF.name}
作品演示视频：{DOWNLOAD}PULSE_OS2026_Demo.mp4
中文字幕：{DOWNLOAD}PULSE_OS2026_Demo.zh-CN.srt
运行证据：{DOWNLOAD}{evidence_zip.name}

介绍文档：9 页，嵌入简体中文字体，包含背景、架构、场景、创新、验证与发展计划。
演示视频：{timestamp(video['duration_seconds'])}，1920x1080，H.264/AAC，中文配音和画面内字幕。
演示范围：真实命令输出、策略比较、1,600 人合成场景回放、AI 回复拒绝测试、既有样例核验。
当前为研究原型，未完成真实园区校准；大规模样例未在本次重新执行，未启动新的 LLM 推理。

官网要求（2026-10-13 核对）：{chr(10)}https://www.oschina.net/os2026/
材料截止：2026-10-16 24:00；组委会邮箱：oscc@oschina.cn。
具体提交按报名确认邮件指引办理。本材料包不代表已向组委会发送或完成作品提交。

主要发布文件 SHA-256：
{checksums}
"""
    (OUT / "submission_links.txt").write_text(links, encoding="utf-8")
    submission = OUT / "PULSE_OS2026_Submission.zip"
    with zipfile.ZipFile(submission, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(OUT / PDF.name, PDF.name)
        z.write(OUT / "submission_links.txt", "参赛链接与材料说明.txt")
        z.writestr("主要文件校验值.txt", checksums)
    checksums += f"{sha(submission)}  {submission.name}\n"
    (OUT / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    chapter_lines = "\n".join(f"- {timestamp(c['start'])} {c['title']}" for c in video["chapters"])
    notes = f"""PULSE 面向工业园区应急规划，提供 AI 辅助疏散策略仿真与评估。本版本用于参加 2026 上海开源软件应用创新大赛的 **AI+ 工业软件赛道（自主选题）**。

- [作品介绍 PDF（9 页）]({DOWNLOAD}{PDF.name})
- [演示视频（{timestamp(video['duration_seconds'])}，1080p，中文配音与字幕）]({DOWNLOAD}PULSE_OS2026_Demo.mp4)
- [参赛附件包：PDF 与提交链接]({DOWNLOAD}{submission.name})
- [运行证据：真实命令输出、仿真数据与输出哈希]({DOWNLOAD}{evidence_zip.name})

视频展示真实 CLI 输出与保存的仿真数据回放，不对应网页前端。包含安装启动、20 个候选策略比较、需求扫描、1,600 人 CPU 合成场景、AI 回复拒绝测试和 48 份既有样例核验。

本次验证：8 项单元测试、9 项证据校验通过；合成场景人口守恒误差为 0，超容避难所数为 0。原始计算源码基线为 `{evidence['source_commit']}`。

当前为研究原型，尚未完成真实园区校准。大规模样例本次仅核验，未重新运行；视频没有新的 LLM 推理。机理搜索包含预置参考控制。第三方数据来源与限制见仓库 `THIRD_PARTY_NOTICES.md`。

视频章节：

{chapter_lines}

完整重建说明见 `docs/COMPETITION.md`；原创代码采用 AGPL-3.0-only。发布文件校验值见附件 `SHA256SUMS.txt`。
"""
    (OUT / "release_notes.md").write_text(notes, encoding="utf-8")
    print("Packaged", len(main_files)+2, "release assets")
    for path in main_files + [submission, OUT / "SHA256SUMS.txt"]:
        print(path.name, path.stat().st_size)


if __name__ == "__main__":
    build()
