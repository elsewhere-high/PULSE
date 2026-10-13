# 参与 PULSE

通过 GitHub Issue 提交问题或方案，通过 Pull Request 提交修改。功能和实验讨论请说明所解决的问题、输入口径与预期行为；不要求公开真实园区或个人敏感数据。

## 提交修改

1. 按 README 创建 Conda 环境并安装开发依赖。
2. 在独立分支修改，保留能够复现问题的最小输入和命令。
3. 运行与修改相关的检查；仿真逻辑修改需运行以下命令：

```bash
conda run -n pulse python -m unittest discover -s tests -v
conda run -n pulse python scripts/verify_evidence_chain.py
conda run -n pulse python scripts/run_city_demo.py
```

4. PR 说明问题、最终行为、验证结果与已知限制。由维护者评审后合并。

## 实验与数据

- 保留人口守恒、避难所容量、LLM 候选编号及满员过滤检查。
- 相同口径、相同随机种子才进行策略配对；区分新实验与既有样例。
- 不只报告单个有利指标；保留退化结果及失败原因。
- 新增数据须注明来源、授权或许可证、转换方法、字段与哈希；不提交凭据、私密配置或无权公开的数据。
- 不覆盖 `results/runs_raw/` 回归样例。模型权重和大规模中间结果不进入 Git。

原创代码贡献按仓库 AGPL-3.0-only 许可；第三方内容继续遵守其原有条款。未核实的数据来源应明确标注，不能将待解决问题写成已完成验证。
