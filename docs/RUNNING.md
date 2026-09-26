# PULSE 运行说明

在项目根目录执行下列命令；先按 README 建立 Conda 环境并安装依赖。

## 机理模型与样例分析

```bash
conda run -n pulse pulse-explore --output results/demo
conda run -n pulse python scripts/plot_demo.py --input results/demo --output results/demo/pulse_demo.png
conda run -n pulse python scripts/verify_evidence_chain.py
conda run -n pulse python scripts/plot_chengdu_census2020.py
```

最后一个命令从既有样例重绘成都分析图，写入 `results/figures/`。输入的三种人口/几何口径必须分别分析，不能把跨口径差异解释为单个策略的效果。

## 居民级城市引擎

```bash
conda run -n pulse python scripts/run_city_demo.py
conda run -n pulse python scripts/bench_swarm.py --help
```

自备小型 NPZ 输入后，可以直接运行并导出事件、街区帧和抽样轨迹：

```bash
conda run -n pulse python scripts/bench_swarm.py \
  --device cpu --cache data/external/my_city.npz \
  --route-cache results/cache/my_city_routing.npz \
  --run-dir results/city_run --steps 180 --seed 42 \
  --frames-every 30 --traj3d-every 30 --traj3d-n 100
```

缓存需包含 lon、lat、pop、area、neigh、deg、s_lon、s_lat、s_cap。邻接补位为 -1；输入必须使用相同街区索引。当前居民信念模型使用 16 个候选槽，场景至少提供 16 个避难所。`--no-events` 可关闭事件文件；`--verify-at 0,30` 导出指定步的状态数组。

无缓存时，`--base` 指定包含 `<目录名>_blocks.geojson` 和 `<目录名>_block_evacuation.json` 的目录，载入器会构建缓存。随附成都缓存可直接读取，路由缓存可根据其拓扑生成。请使用匹配该网络的路由缓存；更换输入后使用新的缓存路径。

默认 `--device cuda` 适用于 CUDA/ROCm PyTorch。无兼容 GPU 时程序会提示使用 CPU。`--road-damage` 改变街区邻接，模拟器会单独重建受损路由。

## 批量实验

`run_chengdu_census2020_matrix.py` 使用相同人口和几何执行四档覆盖率 × 三个种子；`run_chengdu_census2020_llm.py` 执行三个配对 LLM 实验。两者只把同时满足固定人口、步数、守恒和容量约束的结果作为完成项。

| 配置 | 默认位置或用途 |
| --- | --- |
| `PULSE_BASE` | `data/chengdu_census2020/base`，缓存缺失时的底图 |
| `PULSE_CACHE` | `data/chengdu_census2020/chengdu_census2020_v1.npz` |
| `PULSE_ROUTING` | `results/cache/chengdu_census2020_routing_v1.npz` |
| `PULSE_COVERAGE_DIR` | `results/chengdu_census2020/coverage_v1` |
| `PULSE_LLM_DIR` | `results/chengdu_census2020/llm_v1` |
| `PULSE_MATRIX_DIR` | `results/matrix`，一般矩阵脚本的输出 |
| `PULSE_LLAMA_BIN` | 本地 llama-server 可执行文件路径 |
| `PULSE_LLM_MODEL` | 本地 GGUF 权重路径 |

覆盖率矩阵和 LLM 实验面向大内存 GPU，不属于小型 CPU Demo：

```bash
conda run -n pulse python scripts/run_chengdu_census2020_matrix.py
conda run -n pulse python scripts/run_chengdu_census2020_llm.py
```

LLM 脚本先检查 `http://127.0.0.1:8080/health`，推理请求发送到本地 `/completion`。`run_chengdu_census2020_pipeline.sh` 在覆盖率矩阵完成后启动本地推理服务，要求先激活 Conda 环境并设置 `PULSE_LLAMA_BIN`、`PULSE_LLM_MODEL`；退出时结束它自己启动的服务。

从零构建人口输入需要额外提供源人口缓存、区县边界和普查 CSV。`build_chengdu_census2020_cache.py --help` 显示必需参数；默认拒绝覆盖已有输出。

`results/requirements-lock.txt` 仅记录实验样例产生时的 ROCm 环境，不用于当前项目安装。
