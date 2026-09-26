# 数据格式与来源

人口输入为合成人口分配。区县普查总量是硬约束，街区权重来自 WorldPop；以 Hamilton 最大余数法整数化。保持人口、路网、避难所和容量在同一实验中固定，不允许策略修改总人口或绕过容量。

- `chengdu_census_2020_district_population.csv`：20 个区县的人口总量，字段为 adcode、district、population_2020_census。
- `chengdu_census2020/chengdu_census2020_v1.npz`：11 个 NumPy 数组。lon、lat、pop、area、neigh、deg、district 描述 66,546 个街区；s_lon、s_lat、s_cap 描述 1,252 个避难所；adcode 映射区县索引。人口共 20,937,757，情景容量共 2,537,800。
- 同目录 provenance JSON 保留输入和输出哈希、人口构造方法、区县验证和局限。path 以项目根目录为基准；bundled=false 表示输入未提供。

已有 NPZ 可供城市载入器使用，无须重新取得 GeoJSON 才能读取其数组。路由缓存可从其拓扑生成。若要重建人口输入或更换底图，仍需自行提供原始人口缓存、区县边界、街区 GeoJSON 和避难所数据。LLM 实验另需本地推理服务及权重。

街区分配不是街区级普查统计；行政边界不是测绘级地籍边界；避难所容量不是官方台账。本模型用于研究与情景比较，不是已校准的实际应急决策系统。外部数据说明见 [第三方声明](../THIRD_PARTY_NOTICES.md)。
