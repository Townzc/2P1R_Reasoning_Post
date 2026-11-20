# Claude 审计 + 代码审查：C-B1 处理与 token 计价候选（2026-10-12 第二轮）

- 审计的 commit：`36bfa8c5`（`codex/icml-acl-2027`）。本地 `.local/midpoint_20261011/audit_followup_20261012/` 中未提交的生成脚本也一并读过。
- 复现：在仓库根目录检出 `codex/icml-acl-2027` 的 `36bfa8c5` 后运行 `python3 <本分支>/audit/claude/20261012b/replay_policy_check.py`（只用 CPU；脚本读取该 commit 中的 packet）。
- 范围：`docs/audit/P007_COST_METRIC_REVIEW_20261012.md`、`reports/p007_audit/cost_metric_review_v1/`、`experiments/sft_allocation_acquisition/{policy_contract,policy_runtime,wallet,contract,student_contract,student_runtime}.py`、本地 `token_budget_diagnostic.py`。首批两个学生的结果尚未出来，不在本轮范围内。

## 结论

| 对象 | 结论 |
| --- | --- |
| Codex 对 C-B1 的复核 | **接受**。四格的 ms/token 与我的结果一致，"高价方向相反"是新信息，不归因于硬件的表述也正确。 |
| token 计价候选的前缀一致性 | **PASS**。用冻结的 `Policy` 类重放四条保存轨迹：每个候选前缀内，每一批的新购题数都等于当时可用的空位，因此在这些前缀内，token 钱包与原来的时间钱包会做出完全相同的购买决定。批次名单逐批一致。 |
| 候选的结束规则与剩余预算 | **PASS-WITH-NOTES**（T2） |
| 候选用于 8 个学生的科学设计 | **需要 owner 决定**（T3，高） |
| 可复现性 | **FAIL，修复很简单**（T1） |

## 发现

| ID | 严重度 | 观察到的事实 | 建议 |
| --- | --- | --- | --- |
| T1 | 中（可复现性） | 生成 `token_candidate.json` 与 524,287 计划的脚本（`token_budget_diagnostic.py`、`preflight_token_candidate*.py`）只在本地 `.local`，没有提交；packet 里也没有给出生成命令。 | 提交这些脚本，并在 manifest 中写明生成命令和输入哈希。 |
| T2 | 中 | 诊断脚本要求每批都是完整的 16 行，并按 16 × 1,024 的最大输出预留；预留不足时直接停止。冻结设计（P007B 校准修订）写的是"a final smaller purchase is allowed"。四格剩余预算为 6.14% / 6.88% / 12.26% / 10.90%，**全部超过设计自己规定的 5% 阈值**（超过就"do not describe results as an exact-spend comparison"）。尾部那一批无法从保存轨迹中模拟（批次组成不同，随机数也不同），所以这是保存轨迹方法本身的限制。 | 文中按设计规则写明"cap comparison with ≤12.3% unspent"，不写"等预算"；或者改成"按实际花费取最长前缀"（事后模拟不需要预留），剩余可降到一批的粒度。breadth_p4 一批约占上限的 14%，粒度仍然很粗，见 T3。 |
| T3 | **高（科学设计）** | 学生训练量固定为 524,287 个 target，候选语料的每对平均曝光：breadth_p0 4.46、depth_p0 3.97、**depth_p4 8.0、breadth_p4 20.77**（只有 91 个可用答案）。P007 主实验中，13.6 次曝光的 Repeat 比 3.4 次曝光的臂低 10.8pp。时间计价版本同样有这个问题，只是程度较轻（breadth_p4 8.61，depth_p4 4.17）。 | 价格交互项 (depth − breadth)@p4 − (depth − breadth)@p0 会大部分反映重复造成的损伤，而不是采购策略本身的价值。这是"固定训练算力"这个估计对象的固有性质，可以保留，但必须在 owner 决定前讲清楚。可选方案：(a) 提高上限，使 p4 两格都有约 400 个以上可用答案。保存的轨迹不够（breadth_p4 全部只有 215 个），需要新的教师生成；按 P007A 的速度，每格约十几分钟 H100。(b) 增加一个按固定曝光次数训练的第二剂量（例如每对约 4 次），把"数据多少"和"重复多少"分开。(c) 至少在结论里把交互项表述为"在固定训练算力下，包含重复效应"。 |
| S1 | 低（代码） | 524,288 写死在 7 处：`student_contract.py:14`、`student_runtime.py:23,55`、`scripts/audit_acquisition_student.py:38,44,62`、`scripts/summarize_acquisition_students.py:94`。改用 524,287 时如果漏改一处，preflight 会直接拒绝（不会出错地静默运行），但审计脚本可能与运行代码不一致。 | 改成一个由版本化配置读取的常量，审计脚本从 plan 文件中读取目标值，不要另写一个字面量。 |
| S2 | 信息 | P007B 学生训练的是 Qwen2.5-Math-1.5B-Instruct 的完整输出（平均约 280 token，带 `\boxed{}`）；P007 主实验用的是 OMI2 答案（约 150 token）。 | 两个实验的绝对准确率不能直接比较，汇报时分开讲。 |

## 代码审查中确认没有问题的地方

- `Wallet.admit`：先预留、再购买；超出上限时既不购买也不尝试；`settle` 超时或超支时会抛错，不会被原谅。时钟使用单调整数纳秒，取整向上。
- `Policy.complete`：返回的名单和顺序必须与提案一致；usable 只能是 true、false 或未知，不会被悄悄改写。
- `choose_action`：按冻结顺序选最大可负担的新购数，过程中不看任何结果。
- `completion()`：在第一个原生 EOS 处截断，EOS 之后出现非 pad token 会报错。
- `student_contract.training_rows`：拒绝未知 usable、尝试序号缺口、重复的候选，以及违反采购契约的答案；参考答案只作元数据，不进入训练目标。

## 未检查

首批两个学生的训练与评测输出；恢复运行（`recovery_runtime.py`）的逐行代码；高价 breadth 故障批次 50 秒收费重建所依据的服务商时间戳。
