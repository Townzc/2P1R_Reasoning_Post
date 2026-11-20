# E3 完整 A1/A2（输入 + 运行时 + 数值 + D1 覆盖范围）

- **审计方**：Claude，2026-10-20 12:00 UTC 前后。
- **请求**：`p010-E3-complete-input-runtime-numeric-A2-r1`，scope `p010-E3-complete-input-runtime-and-numeric-A2`。
- **目标提交**：`2311841a6a6f53ea1be3ce2d12fa1068aa2407ad`。核对过：到 `be353fe7` 为止，E3 的数据包、结算包和源代码都没有再改动。
- **结论：PASS-WITH-NOTES**

## 绑定字段（供 Codex 写入 `E3_RUNTIME_A1_A2_ACCEPTED.json`）

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p010-E3-complete-input-runtime-and-numeric-A2` |
| target_commit | `2311841a6a6f53ea1be3ce2d12fa1068aa2407ad` |
| spec_sha256 | `d7a9d37c081271be8b00a24e8d6528145991a5921f4f9e7a3ef0c7cb2688a7a9` |
| source_files | 与 SPEC.json 中的 `source_files` 完全相同，共 25 个文件 |
| verification_source_files | 与 SPEC.json 中的同名字段相同，共 28 个文件 |
| input_basis_sha256 | `13d36b7537ee006b1ea02c499989f3c5bd3646bf56929ce2576ac57b2ee56672` |
| input_archive_sha256 | `4274f0745c1da52a8c2b7a3757557b081ae65d22cf36bed348ab927cd9e19a63` |
| owner_D4_evidence_sha256 | `72ec41dcd19b2e06069cfc66a0c443e8025563736779ef6f20595a5665495f40`（即 `20261020i/OWNER_DELEGATION_AND_DECISIONS.md` 的当前版本，本次没有修改） |
| settlement_proposal_sha256 | `e0766a9a6cb3f91f7fc1835f6dded5b23e9fe6495a1bc22b8930610458ce3ea4` |
| input_A1_accepted | true |
| D1_hourly_coverage_scope_accepted | true（限制见 §3） |
| all_old_T08_outputs_reused_without_rescoring | true |
| first_paid_measurement_exceptions | 0 |

## 1. 输入 A1（独立复现，脚本 `a1_e3_check.py`，结果 `A1_E3_RESULT.json`）

**输入文件**：解开 `frozen_inputs.tar.gz`，10 个成员的 SHA 全部与 INPUT_ARCHIVE.json 一致。

**200 题名单**
- `MATH_ROSTERS.json` 的 SHA 为 `2cd19c3f…`，与生成开始前冻结在 teacher_runtime_v1/v2/v3 SPEC 中的值相同。
- 我用冻结规则独立重算了名单：取 P009 `ROSTER_s17` 的 n400 题目，按 `sha256('p010-e3:20261019:'+pid)` 排序，取前 200 个。结果与 `e3_hash200` 和 E3 的 ROSTER.json **逐项、同顺序相等**。
- 名单全部来自 n400，无重复，没有按正确率筛题。

**3,200 个新请求**：逐条与原 T72 生成的 **14,098 条原始记录**（来自 `teacher_t72_complete_v1/original_evidence.tar.gz` 的 raw/）对照，**不一致 0 条**。对照内容：
- prompt token 序列逐个相同；
- seed 与原始记录相同；
- 采样参数中除温度外每个键都相同：top_p 0.95、top_k −1、max_tokens 1024、停止 id [151645, 151643] 等；
- 温度分别为 0.6 和 1.0，原始记录的温度都是 0.8；
- 每一档温度 1,600 条，ID 唯一，200 题 × 前 8 次尝试；
- prompt 长度 + 1024 ≤ 2048。

**seed 关系**：同一题、同一次尝试在三档温度下用同一个 seed（共同随机数设计）；同一温度内 1,600 个 seed 各不相同。这一点 ROSTER 里已经写明，报告里也应写出。

**复用的 T0.8 数据**：1,600 条，与我在 20261020f 审过的 T72 `RECORD_INDEX` **逐字相同**，正好是这 200 题的第 1–8 次尝试。`original_record_sha256` 按 Codex 的 digest 定义（ASCII 转义）重算，1600/1600 一致。

**PROMPT_TEXTS 与 GOLD_SOURCE**：两者的 token 序列和题目行，都与冻结的 T72 请求及 `MATH_SOURCE.json` 完全相同。

## 2. 运行时 A2（逐行阅读，2026-10-20 E4 漏审之后的标准）

**代码一致性**：`teacher_contract.py`、`teacher_transport.py`、`high_throughput_v1.py`、`stage0_generation_engine_v2.py` 的 SHA 都与原 T72 生成（teacher_runtime_v3）完全相同；另有 18 个公用文件与已审过的 seed29/E9 运行时相同。新增的只有 e3_* 系列、modal_e3、settlement_d1/binding，这些我都逐行读过。

**`e3_runtime.generate`**
- 运行前检查：4 张 H100，每张 ≥ 75 GiB；模型 id 和 revision 与 T72 完全相同；一次性 claim。
- 用 teacher native chat 模板重新编码 200 个题目并与保存的 prompt 比对，**不一致就中止**。
- 实际确认 TP=4。
- 分批：每批 256 条，每档温度 7 批，共 14 批。每批开始前写 forecast 和 intent，并设一次性围栏；生成后检查原始结果的身份、prompt 和采样参数，再用原 `completion()` 判停止原因。
- 结束检查：总数 3200，两档各 1600，批次 14。

**`modal_e3`**
- worker 资源：H100!:4，`timeout=1860`，`retries=0`，`max_containers=1`，`single_use`，内部硬计时 1800 s。
- 失败时写 FAILURE 和 terminal，不自动重试。
- 入口检查：
  - 时间：调度截止 10/21 10:00 UTC；当前时间 + 51,105 s 必须不晚于 10/21 19:00 UTC，也就是**最晚 10/21 04:48 UTC（10/20 21:48 PDT）调度**；
  - 源代码和验证源代码逐个核对 SHA；
  - A2 绑定字段、D4、A3/A4 齐全；
  - 输入上传后读回比对；
  - 预算文件在 1 小时内新鲜；
  - 前置任务全部 STOPPED、容器数为 0，原 G 账本恰为 44；
  - 结算后 G、其余各类别和总额都不超上限；
  - 一次性键都未被占用。

**`e3_contract.forecast`**
- 费率 0.00463488 $/s。独立核算：4 × 0.001097 + 8 × 0.0000131 + 64 × 0.00000222 = 0.00463488，与 H100 $3.95/h 一致。
- 初始情景：1.2 × (457.33 + 38.10 × 14 + 300) = 1548.86 s，即 (1548.86 + 600) × 0.00463488 = **$9.96 ≤ 预留 $11.13 ≤ 结算后 G 剩余 × 80% = $20.776**。
- 1548.86 s ≤ 1770 s（1800 − 30）。
- 原来 36 个整批里最慢 38.10 s，取的是最大值。

**`audit_p010_e3.audit`**（原始结果核对）
- 本地用原 tokenizer 把每条 raw 重新走一遍 `completion()`，和 worker 写下的 transport 逐条比对；
- 批次文件集合必须与预期完全相同；
- 评分行的 gold 取 `last_box(MATH 原解)`。

**`e3_scoring`**：沿用 S1 的 DurableEndpointPool，每块 100 条，共 32 块；技术性未知不当作 0 分，而是报错；评分器 `math_scoring.py` 的 SHA 为 d310d7e6…（冻结版本）。

**评分口径与 T0.8 一致**：用同一个 `last_box` 和 `pair_digest` 重算 1,463 条 T0.8 记录的 pair_id，**1463/1463 与原保存值相同**，其余 137 条本来就没有 pair。所以三档温度用的是同一个 gold 抽取和同一个评分器。

## 3. D1 结算数值与覆盖范围

**逐个 app 独立重算**：取保存的 hourly 和历史 gross 中的最大值 × 1.2，向上取到分。

| 原作业 | 原预留 | 最大 gross | 结算额 |
|---|---:|---:|---:|
| assets_t72 | 0.50 | 0.0828 | 0.10 |
| assets_t7 | 0.50 | — | **0.50**（没有 owned=0 证明，保留全额） |
| teacher_t15 | 5.50 | 0.5885 | 0.71 |
| teacher_t72 | 24.00 | 17.5836 | 21.11 |
| teacher_t7（失败那次） | 8.00 | 0.1619 | 0.20 |
| teacher_t7_remainder | 5.50 | 1.1730 | 1.41 |
| **合计** | **44.00** | | **24.03** |

- 释放 19.97；(50 − 24.03) × 0.8 = **20.776 ≥ 11.13**。全部与 PROPOSAL.json 相同。
- 每个合格 app 返回的整点小时桶都覆盖了它从创建到 STOPPED 的全过程。
- 查询时间是 10:47 UTC，距最晚的 STOPPED（04:20 UTC）约 6.5 小时；多次历史读数稳定（T72 有一次早期的较低读数 8.29，结算取的是最大值）。

**接受的范围**：这是延迟计量 + 20% 缓冲，**不是账单终值**。Modal 没有提供计量终值的水位标记。这符合负责人批准的 D1 的定义。

## 4. 指标代码（`e3_metrics`，在真实 T0.8 数据上验证，脚本 `metrics_check.py`）

- **LCS**：位并行实现与朴素动态规划对比，随机 3,000 组和真实文本 300 对，**不一致 0**。
- **`usable()`**：在 1,600 条 T0.8 记录上与保存的 usable 标志 1600/1600 一致。
- **T0.8 基线**（这些是 E3 新数据出来前已经确定的数；可以写进报告表格，但解读必须由负责人自己写）：
  - 完整（native EOS）1463/1600；
  - 正确 1389/1600；
  - 可用且不重复 1367/1600；
  - 200 题 × 28 对 = 5,600 对，pooled ROUGE-L 0.635。

## 备注（PASS-WITH-NOTES 的原因）

1. **"算式集合"的实际含义**：它是 LaTeX 数学定界符里的**全部表达式**，包括 `f`、`f(1)` 这类单个符号，再加上不带定界符的单行等式。报告里应称为"数学表达式集合的词面 Jaccard（lexical math-expression Jaccard）"，不要写成"算式"或"语义等价"。两边都为空时记为 1，这一点也要披露。
2. **共同随机数**：三档温度用同一组 seed。这不影响"同一温度内"的多样性指标，但报告里要写出来。
3. **调度顺序**：**E3 必须先于 C6 补跑格调度，且两者不能同时运行。**
   - E3 入口要求所有前置任务 STOPPED、容器数为 0，并用原始账本检查 I 类别。
   - 如果 C6 补跑先按原始口径加上 2.52，I 类别会变成 16.95 > 15，E3 就无法进入。
4. **本审计的局限**：
   - 没有运行 vLLM、TP4 或 math-verify；
   - 没有重跑 Codex 的合成测试；
   - 评分器的一致性依靠 SHA 和 1463/1463 的 pair_id 复现来证明。
5. **E3 只是描述性分析**：没有置信区间，不做因果推断。报告里写成"温度供给审计（描述性）"，结论部分由负责人自己撰写。

**A3**：结果出来后，由 Claude 独立做 A3。
