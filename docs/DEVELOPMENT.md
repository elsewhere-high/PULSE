# PULSE 开发说明

## 代码与接口

| 位置 | 用途 |
| --- | --- |
| `src/pulse/model.py` | 纯标准库机理模型，Control、Metrics、simulate |
| `src/pulse/experiment.py` | 候选搜索、跨种子检查、CSV/JSON/SVG 导出和 CLI |
| `src/pulse/simulator/` | 街区流量、居民数组、路由、容量接纳、LLM 协调和避难点选址 |
| `src/pulse/demo.py` | 无外部数据的小型合成场景 |
| `scripts/` | 城市运行、缓存构建、样例分析和绘图 |
| `tests/` | 原机理回归检查与 CPU、路由、LLM 回复拒绝检查 |
| `data/` | 人口输入及来源元数据 |
| `results/` | 带口径的实验样例，生成结果目录由 Git 忽略 |

包的最小 API：

```python
from pulse import Control, Metrics, simulate
from pulse.model import reference_control
from pulse.experiment import run_all
from pathlib import Path

metrics, series = simulate(1000, reference_control(), seed=7)
assert metrics.conservation_error == 0
summary = run_all(Path("results/demo"))
```

`Control` 控制信号偏移、三条路径的分配权重和出发延迟。权重必须非负且总和为 1；模型会验证控制范围和人口守恒。`Metrics` 同时保留完成率、队列、振荡、回溢、均速及稳定性，不能只挑一个有利指标。

城市模块使用 `pulse.simulator.*` 导入。安装基础包不会自动加载 PyTorch；城市调用需要 `city` 可选依赖，绘图需要 `plots`。wheel 包含全部 Python 模块；较大的样例数据和源代码脚本包含在源码分发包中。

## 验证

```bash
conda run -n pulse python -m unittest discover -s tests -v
conda run -n pulse python scripts/verify_evidence_chain.py
conda run -n pulse python scripts/run_city_demo.py
conda run -n pulse python -m pip check
conda run -n pulse python -m build --no-isolation
```

安装验证应从源码目录之外安装 wheel，再执行 `pulse-explore`，避免源代码路径掩盖打包缺失。城市 Demo 需要源码包中的脚本。日常开发可使用 README 中的 editable 安装。

## 数据和约束

保留固定随机种子、数据字段和输入哈希。人口守恒必须成立，避难所接纳不得超过容量；LLM 仅影响信息和策略，不能修改总人口或绕过物理约束。候选编号和已满避难所过滤必须保留。

`results/runs_raw/` 和三个参考 CSV 是回归样例，不应被新的实验覆盖。CSV 的换行由 `.gitattributes` 固定；证据校验器在临时目录重建表格并逐字节比较。

运行日志、Conda 环境、缓存、模型权重和私密配置不进入 Git。第三方数据来源和格式版本必须保留，项目许可证不替代数据自身条款。
