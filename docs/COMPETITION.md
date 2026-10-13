# OS2026 参赛材料

参赛作品：PULSE - AI 辅助疏散策略仿真与评估。赛道：AI+ 工业软件，自主选题。作品面向工业园区应急规划，当前为可运行的研究原型。

## 官方要求

根据 [2026 上海开源软件应用创新大赛官网](https://www.oschina.net/os2026/)（2026-10-13 查阅），需提供完整可运行的代码仓库、包含背景/架构/场景/创新点的介绍文档，以及展示核心功能与使用流程的演示视频。官网公布的材料截止时间为 2026-10-16 24:00，材料提交地址为 oscc@oschina.cn，具体按报名确认邮件指引办理。

评审权重为技术创新 30%、场景落地 30%、开源治理 20%、长期发展 20%。本项目材料同时说明已实现功能、验证结果、数据限制和后续计划。

## 发布文件

统一入口：[os2026-submission-v1](https://github.com/elsewhere-high/PULSE/releases/tag/os2026-submission-v1)。

| 文件 | 内容 |
| --- | --- |
| `PULSE_OS2026_Project_Introduction.pdf` | 9 页中文作品介绍，嵌入中文字体 |
| `PULSE_OS2026_Demo.mp4` | 1920 × 1080，H.264/AAC，中文配音和画面内字幕 |
| `PULSE_OS2026_Demo.zh-CN.srt` | 可单独加载的中文字幕 |
| `PULSE_OS2026_Evidence.zip` | 真实命令输出、JSON/CSV/SVG、合成场景 NPZ、输出哈希、视频章节 |
| `PULSE_OS2026_Submission.zip` | PDF、提交链接说明与发布文件哈希，便于作为参赛附件 |
| `SHA256SUMS.txt` | 本次发布主要文件的 SHA-256 |

## 演示内容与证据边界

1. 运行 `pulse-explore`，比较 20 个候选并查看队列与需求扫描。第 3 个候选是预置参考控制，不能称为 AI 自主发现。
2. 运行 1,600 人 CPU 合成场景，回放保存的街区采样帧，检查守恒和容量约束。
3. 运行 AI 回复拒绝测试；本次未启动新的 LLM 推理。
4. 核验 48 份既有大规模样例与分析表，不将样例核验写成重新执行大规模实验。

视频是实际命令输出和数据的剪辑回放，包含展示用途的图表与说明版式；项目本身提供 CLI、Python API 和结果文件，没有网页前端。旁白由 macOS 中文语音合成生成。

既有 LLM 配对样例包含总体效果退化的情况；报告同时展示距离和最终避难比例，不承诺 AI 必然改善结果。当前没有真实园区客户案例或已完成的实测校准。外部数据来源限制见 [第三方声明](../THIRD_PARTY_NOTICES.md)。

## 重建材料

先按 README 安装项目。所有 Python 命令均在 `pulse` Conda 环境执行：

```bash
conda run -n pulse python -m pip install -r scripts/competition/requirements.txt
conda run -n pulse python scripts/competition/collect_evidence.py
conda run -n pulse python scripts/competition/build_pdf.py
conda run -n pulse python scripts/competition/build_video.py
conda run -n pulse python scripts/competition/package_submission.py
```

PDF 写入 `output/pdf/`，运行证据和视频写入 `output/os2026/`，视频中间文件写入 `tmp/os2026_video/`。这些生成目录不进入 Git。

PDF 脚本默认使用 macOS 的 Arial Unicode 中文字体，可通过 `PULSE_CJK_FONT` 指向其他覆盖简体中文的 TrueType 字体。视频脚本使用 macOS `say` 的 Tingting 中文语音，并使用系统 Arial / Menlo 字体。仅重建 PDF 和证据不依赖语音工具。

为更新旁白重建视频时，应先清理 `tmp/os2026_video/scene_*.wav`，再运行生成脚本。发布前渲染检查 PDF 各页、检查视频画面及音轨、验证文件哈希与公开下载地址。
