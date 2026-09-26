# 实验样例数据字典

这里保存 48 份既有实验样例及其参考分析表，用于离线分析回归核验；不代表新项目已经重新执行过城市实验。样例数值、种子、配置和数组保持原样。

## 文件与输入口径

- runs_raw/*.json：逐次运行 summary，含 totals、queue_series、eva_series，LLM 运行还包含 llm 诊断。
- analysis_dataset.csv：48 行，tag 唯一标识运行；caliber 区分 chengdu831、chengdu_official、chengdu_census2020。三种口径的几何和人口不同，不能混为相同输入。
- paired_effects.csv：同口径、同随机种子下各配置减去基准。基准分别是 cov30、off、c20_cov030。
- effect_summary.csv：配对差的中位数、种子方向一致性、效应与种子极差之比；in_B 表示早晚安全效果符号相反。
- traceability.json：运行标签、参数、输入口径和生成样例时的环境；脚本名与哈希是样例溯源标识，不表示当前脚本哈希。
- caliber.json、data_provenance.json：输入定义、来源、哈希和限制。标记 bundled=false 的文件未随附。
- requirements-lock.txt：生成样例时的环境包清单，含特定 ROCm 构建；不能用作当前机器的安装清单。

## 字段与单位

| 分组 | 字段 | 含义 |
| --- | --- | --- |
| 自变量 | frac_knows_one、broadcast_reach | 初始知识覆盖率、广播到达率，均为 0–1 |
| 自变量 | road_damage | 随机切断的街区邻接链接比例，不是实测道路损毁率 |
| 自变量 | llm_enabled、leader_comm、seed | LLM 开关、领导之间的通信比例、随机种子 |
| 安全 | Safe15/30/60/120 | 对应 share_safe_by_*min，已避难人数除以总人口，单位为分数 |
| 拥堵 | Queue_max | queue_max，单步到达满员避难所而被拒的人数峰值 |
| 容量 | Overflow、sheltered、shelter_util | 超容避难所数、已避难人数、容量利用率 |
| 公平 | EquityGap | shelter_occupancy_gini，避难所占用的基尼系数 |
| 行为 | n_destinations、walk_median_m、walk_mean_m | 目的地数量、已避难者步行距离中位数与均值（米） |
| 行为 | rethink、rejections、switch_share | 累计重决策次数、累计满员拒入次数、曾换目标的比例 |
| 行为 | gave_up、giveup_exhaust、giveup_nopath | 放弃人数、其中力竭和无路可达的人数 |
| 时间 | t_p50_min、t_p90_min | 已避难者用时分位数（分钟） |
| 控制 | n_agents、n_blocks、capacity、steps | 人口、街区数、避难所总容量、步数 |
| 有效性 | cons_error、accounted、Overflow | 人口守恒误差必须为 0，accounted 必须等于 n_agents，超容必须为 0 |
| LLM 有效性 | applied_share、hallucinated_shelter、sent_to_full_shelter | 执行比例、虚构避难所数量、指向已满避难所数量 |
| 元数据 | wall_s、ms_per_step、device、peak_vram_gib | 执行时间、设备与资源占用 |

派生变量和源字段的完整逐项映射见 scripts/matrix/build_analysis_dataset.py。J_raw 是四个分量各按自然尺度归一后等权相减的辅助量，不能替代分量报告。sheltered、shelter_occupancy、n_with_time 描述同一个量，不能重复计数；百分数与分数不能直接混算。

人口守恒、容量限制、LLM 候选编号和满员过滤属于模型安全边界。相关检查必须保留。种子方向一致与中介变量共变不等于实测校准或因果机制已得到证明。
