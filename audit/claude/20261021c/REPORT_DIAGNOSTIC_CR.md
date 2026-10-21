# OT3 完整性只读诊断：简短 CR

- **审计方**：Claude，2026-10-21 02:35 UTC 前后
- **scope**：`p011-OT3-readonly-completeness-diagnostic-CR`
- **target_commit**：`980dd073dd597fa511341ee08294695530463d10`
- **packet MANIFEST**：`78362f33fda7d42d67bce470bbbc96dd5b5775c61bd490c57efa10aa7e05a601`

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| source_files | `experiments/p011/__init__.py` `ef9c51d51d8ce9f6523be02a6d2c80266d431b6dbd25f816249946158789021d`；`experiments/p011/data_contract.py` `4bcb6227770d7db845527712ad3b08a26127e96c02ec46439ae0650bc7e42204`；`experiments/sft_allocation_midpoint/common.py` `4063c6d39640752d4946e473fa4b9f5b94c5fa033859f2ac81962a536b21242c`；`scripts/diagnose_p011_ot3_completeness.py` `ef7fe9197ebb2c62464ca7be2ff4a76cc271b1182735c7c37143168b15037c7a` |
| request_sha256 | `4e8157658c1e521dae9a42323d25226859381dd0a283b7bd38c2a5606567e3a6`（与我提交的请求文件逐字节一致） |
| owner_reported_decision_sha256 | `e47594cd3acb095750d9db4658f4c457f416b4ef77dd1f3ff1b69c4562198c67`。负责人 18:43 PDT 在 claude.ai 对话中直接回复"做"，我可以证实 |
| preservation_sha256 | `662d42e2b68f207e0a2946a4d9b11d21df25784dd0b91a51f4f010c0c6c89849` |
| plan_sha256 | `20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22` |
| expected_parents / expected_responses | 53107 / 849712 |
| local_hard_seconds | 3600 |
| output | `.local/p011_20261020/r1/ot3_completeness_diagnostic_r1` |
| no_new_eligibility_selection | true |
| 7 个标志 | original_complete_function_called、readonly_immutable_database、all_cardinality16_responses_included、original_length_unknown_retained、no_tokenizer_selection_generation_or_scoring、deterministic_samples_and_quantiles_accepted、reporting_threshold_semantics_accepted：**均为 true** |

## 逐行审查要点

**`describe`**
- `complete` 直接调用已冻结的 `rules.complete`，没有另写判定。
- N1–N5 按请求规定的顺序归类，各类互斥：N3 要求最后一个 `</think>` 之前有 boxed，N4 要求全文都没有 boxed。
- R′ 定义为"t≥1 时看最后一个 `</think>` 之后；t=0 时看全文"，与请求一致 ✓。

**`Summary.parent`**
- 逐个父题用原 disposition 交叉核对：`incomplete` 标志必须等于"16 条中完整数 < 16"，`eligible` 也必须与原判定一致。任何一处不一致就报错。这一步顺带独立验证了原构建中完整性判定的正确性，很好 ✓。

**阈值语义**（接受 Codex 的显式写法）
- 触发标志采用 R′ 下"16 条全完整、尚未计入长度与去污染"的父题数，这是**更敏感的上界**。
- 另外还报告"已知合格数"和"可能合格上界"，以及 MET / NOT_MET / UNKNOWN 三种状态。
- N2 阈值用整数判定：`10·N2 ≥ 不完整数`。
- 无论哪个触发，**都只是"报告负责人"**，不授权任何重选。这与我的请求意图一致，判读时我会同时看三个数。

**其他**
- 只读：`mode=ro&immutable=1`，并回读确认 `query_only`；读取前核对原 SQLite 和 disposition 的 SHA ✓。
- 防重跑：设有永久 fence，输出目录 create-only，失败不重试 ✓。
- 时限：3600 秒（SIGALRM 加逐行检查），同时受 P011 截止 2026-10-22 05:00 UTC 约束 ✓。
- 分位数：线性插值，位置取 (n−1)p ✓。
- 样例：每类独立的 `Random(20261021)` 蓄水池抽样，按父题/文件/行号的字典序遍历 ✓。
- 本地测试：新增 12 项测试已在本机跑过，全部通过。

## 注意

- **时限有失败风险**：85 万条回答约 25GB 文本，预计 10–20 分钟能跑完。一旦超过 3600 秒就会失败，并且不会重试。
- **只能描述，不能下因果结论**：N1–N5 是字符串层面的分类，不能证明回答被截断的原因，也不能判断答案是否正确。结果出来后我按预先冻结的规则判读，并立即报告负责人。
