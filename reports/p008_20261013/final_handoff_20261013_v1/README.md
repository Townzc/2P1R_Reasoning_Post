# P008 最终结果与材料交接

交接时间：2026.10.13 23:16:24 PDT（2026-10-14T06:16:24.840605+00:00）。这是 21:00 PDT 冻结后的独立补充，不回写原材料。

**有限实验及必要核验已全部完成。** 两次采购、18 个逻辑学生（74 训练单位）和 base 均完整核验并释放资源；19 个模型结果、注册统计、3 张图及最终 CPU 证明均已取得独立 G3 PASS。最后 CPU 外审发布于 23:04:06 PDT，固定报告见下。p007 按用户指令在此次交接发布后暂停，应用暂停回执另行记录。

## 主要结果

所有格子的分母均为 1,319；breadth 为多购题目，depth 为每题多购回答。B、T 分别表示冻结设计中的采购预算和训练量档位。下表抄录已审主表，没有重评分或重新运行统计。

| 主比较条件 | D1 breadth | D1 depth | D2 breadth | D2 depth |
|---|---:|---:|---:|---:|
| B1 / T1，题价 0 | 969 | 965 | 968 | 970 |
| B1 / T1，题价 4m | 954 | 945 | 951 | 943 |
| B8 / T8，题价 0 | 967 | 965 | 956 | 971 |
| B8 / T8，题价 4m | 945 | 939 | 935 | 990 |

Base 为 **638/1319（48.370%）**。两项 D1/B8/题价0/T1 桥接为 breadth **942**、depth **949**。18 个学生的观测准确率范围为 **70.887%–75.057%**。

目前没有跨采购 draw 稳定复现的策略赢家。在高预算、题价4m条件下，depth−breadth 在 D2 为 **+4.17pp [1.82, 6.52]**，D1 为 **−0.45pp [−2.88, 1.90]**；D2 的正差异没有在 D1 复现。31 个点态条件区间中 27 个包含0；其余4个使用 D2 结果及其同模型均值，不是4次独立重复。区间包含0不等于等效。

## 可直接使用的材料

- [完整19格、31对比、采购费用和限制](../registered_primary_results_v1/FACTS_AND_LIMITS.md)；[逐格CSV](../registered_primary_results_v1/ALL_CELLS.csv)；[全部对比CSV](../registered_primary_results_v1/ALL_CONTRASTS.csv)。原文件标题中的 pending 是发布当时状态，现行审计状态以本交接和独立报告为准，原字节未改。
- 三张已审原图：[预算与训练共同变化](../registered_primary_results_v1/allocation_joint_scaling.png)、[注册交互对比](../registered_primary_results_v1/registered_interactions.png)、[条件桥接](../registered_primary_results_v1/conditional_bridge.png)。同目录保留 SVG。
- [21:00 PDT 不可变中期材料](../midpoint_freeze_20261013_2100PDT_v1/READINESS.md)：科学内容均来自截止前原字节；快照元数据实际在21:01:18写入，二者明确区分。当时待审状态按历史原样保留。
- [冻结后结果解读](../post_freeze_results_review_v1/FACTS_ADDENDUM.md)，措辞已获 dbb0bcff 审计接受。该原补充中的 CPU pending 亦保留为历史状态。
- [最终 CPU 原证明包](../final_cpu_integrity_v1/README.md)；[最后外审与范围](../review_24ef9fd7_accepted_v1/DISPOSITION.md)；[Claude 固定原报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/24ef9fd7dda8d710d4b945f10523b8a41d553b7a/audit/claude/20261014aq/REPORT.md)。
- [P007B 中期事实与限制](../../sft_allocation_midpoint_20261011/P007B_MIDPOINT_EVIDENCE.md)：独立的前一实验，不并入 P008 两次采购或当作第三次重复。
- [工作总表](../../../docs/WORKBOARD.md)、[执行日志](../../sft_allocation_midpoint_20261011/RUN_LOG.md)、[AI 使用记录](../../../AI_USE_LOG.md)、[审计索引](../../p007_audit/INDEX.json)。没有制作 AI slides；个人演示、解读和讲述由研究者完成。

## 完整性与审计范围

最终 CPU 原调用核验24物理来源、21逻辑来源、26份完整 state、3个保留失败父任务及9条 T8 时长修订记录，随后实际本地 finalizer 通过。独立外审接受公开 proof 与原始包的字节绑定；这不表示外审读取了私有 state 二进制。原 call/app/log 的对应关系由已审本地 finalizer 核对，外审未从公开字节再次复现。所有资源已在原调用完成后退出，没有新调用或自动重试。

两项原 T1 训练前失败、原 D2 失败父任务、独立替代与续跑、原上传故障及有界补缺记录全部保留。原 Volume 证据不删除。没有为本交接重跑模型、raw/state oracle、bootstrap、图或已完成测试。

## 费用及保留限制

最近必要费用快照是 **2026.10.13 22:29:36–37 PDT**：[原快照](../BILLING_UPDATE_2230.json)。工作区延迟 meter **$224.36194750**，其中 P008 前缀记录 **$136.69620596**；未归入这些标签的残余 **$87.66574154** 可能包含延迟或未标记 P008 项。残余加完整阶段预留 **$266.44** 为 **$354.10574154 < $450**，保留至少 $50 项目保护。预留、延迟计量和发票是不同口径；CPU 行 $0.01500961 不是最终 CPU 成本，原 $5 预留不回收。所有失败、构建、设置和存储仍计入记录。

- 原18学生包含16个主比较格和2个D1桥接，没有完整 B×T 交互；不能把共同增加数据和训练的变化唯一归因给其中一个因素。
- 两次采购共享初始化 seed17；数据还会改变训练路径，因此 draw 差异不是纯采购方差。
- 区间为固定模型、数据、parser 和已见 benchmark 下的共享题目配对 bootstrap 点态区间，不是训练 seed 或采购总体区间，也不是全族多重比较区间。
- 长度截断仍按主规则判错；最终答案正确不证明推理过程正确，且研究者此前已见过该测试集。
- 原 N2 计时门确实失败；owner 和独立审计在 T8 结果前批准了9600秒的事后工程修订。运行实际较快不改变原 FAIL。
- **A3 全量统一次级 parser 敏感性分析依协议明确 deferred，尚未执行。** 不选择性修正个别样本，不改变冻结主分。

本交接只归纳已有、已审事实及最后 CPU 结果审计，未产生新的科学结果。
