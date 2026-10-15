# P009 最终交接：按预注册规则停止

2026-10-15 PDT。全部已启动工作、完整本地核验和最后实际结果 A4 已闭合。
当前没有活动 GPU/CPU。S1 的首对结果触发原定停止规则，后四项 S1 与 Stage2 均未启动。

| S1 / MATH-500 | 正确数 | 准确率 | 长度截断（计错） |
|---|---:|---:|---:|
| Stage0 学生 base zero-shot | 136/500 | 27.2% | 68 |
| seed17、400 个不同教师答案 | 273/500 | 54.6% | 36 |
| seed17、3,200 个不同教师答案 | 276/500 | 55.2% | 54 |

两个学生均使用相同的1,024步、2,097,148 targets、冻结学习率和完整答案训练，
在同一冻结 vLLM/MATH 终点评测。n3200−n400 为 **+3题 / +0.6个百分点**，
低于预注册的2个百分点继续阈值；91题逐题判定不同。原决定函数只执行一次，
返回 `stop_registered_futility`，最终独立 A4 确认。技术未知均为0。

这次有限流程没有产生可进入 G1/Stage2 的设定。**G1 与 bootstrap 未执行**，
不能写成 G1 通过或失败。NC 的954→967/1319（+13题）未触发其5个百分点停止门；
S2 因原 OLMo zero-shot 的546/1319条长度截断超过15%而未准入，没有用4-shot替代。

## 结果和证据

- [S1 两个完整端点与原停止决定（固定原版本）](https://github.com/Townzc/2P1R_Reasoning_Post/blob/30b906daa81a3c1c5ce1603d701310be0c6e72f2/reports/p009_20261014/stage1_s1_first_pair_handoff_v1/README.md)
- [最终 Claude A4 原报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/b0662285a2b242042a7dd2941c43f7b41c3b397f/audit/claude/20261014cj/REPORT.md)
- [已保存的报告、47条分歧记录及限定接受说明](../review_b0662285_actual_s1_stop_accepted_v1/DISPOSITION.md)
- [NC 配对结果与原失败/替代来源](../stage1_nc_guard_repair_complete_v1/README.md)
- [Stage0 原始结果和科学门](../stage0_complete_a2_v1/README.md)
- [完整 P1 评分、排除和原抽查资料](../p1_complete_scoring_v1/SUMMARY.json)
- [完整运行/审计索引](../../p007_audit/INDEX.json)

原输出、checkpoint 身份、完整本地 state/raw/dose oracle、评分日志、失败父和
代理批准均保留；没有重训、重复生成、重评分或删除 Volume 来完成此交接。
旧 P008 与探索实验材料保持原样。所有后续科学槽位保持未尝试。

## 解释边界与审计范围

这不是两者等效、稳定零效应、能力上限或纯格式/质量机制的证据。只有一个共同
训练/数据顺序 seed；题池只含教师第一次作对的题；固定 targets 下400答案约重复
11–12次、3,200答案约重复1–2次；较大集合的截断也更多。没有跨训练 seed 推断或
bootstrap。P009 效果只使用已审 vLLM 端点，HF638/969仅为历史诊断；原 P0 跨引擎
不一致与事后 internal-only 范围修订仍公开。NC400在替代授权前已知的时间线保留。

最终审计方独立解码两项各500条 raw，检查冻结评分逻辑、剂量，并接受全部25+22
固定分歧。它因 PyPI 连接受限未重跑 math-verify，使用原已保存的 symbolic 结果；
该限制明确保留。它的91题归一化筛查没有发现疑点，不等于证明不存在漏判。
公共 state SHA 不代表外审读取私人 binary。原标签和 null 审查字段未被回写；
独立判定保存在新的审计报告中。

## 费用与关闭状态

最后必要快照为2026-10-15 10:11:06 UTC：两个 S1 app 合计 **$4.02358019** 延迟计量；
整个 workspace 毛计量 **$246.90239056**、现金 billed $0。这不是 P009 全程费用、
最终账单或可用余额。所有失败/setup/build/storage/计量滞后保留；655c/slot是预留，
不是已花费用。详见[原费用快照及来源哈希](../stage1_s1_first_pair_handoff_v1/OBSERVED_COST.json)。
P009批准分配仍为Stage0 $40、Stage1 $70、Stage2 $35、未分配$5；额度不是花费。

科学工作已停止且实际 A4 闭合。本交接普通推送并独立核验远端后暂停 p009；
旧 p007 和 automation-4 保持暂停。自动化实际暂停回执另记于项目关闭状态，
本不可变交接不提前声称工具已经执行。后续研究需要新的任务，当前不启动转向实验。
