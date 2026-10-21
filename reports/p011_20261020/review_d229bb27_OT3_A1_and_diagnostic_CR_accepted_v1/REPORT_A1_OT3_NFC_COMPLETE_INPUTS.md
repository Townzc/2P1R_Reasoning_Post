# P011 OT3 NFC 完整输入与剂量：实际 A1

- **审计方**：Claude，2026-10-21 03:10 UTC 前后
- **请求**：`p011-OT3-NFC-complete-input-and-dose-A1-r1`
- **scope**：`p011-OT3-NFC-complete-input-and-dose-A1`
- **target_commit**：`20044d50cee1acbef0b1aa17ed559e8f0311d98a`
- 脚本 `a1_ot3.py`、结果 `A1_OT3_RESULT.json` 随本目录提交

## 结论：PASS-WITH-NOTES

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES`（实际输入 A1，不同于代码 CR） |
| public_manifest_sha256 | `fcf5e0fa969531437549b38f06e6fcca6f01fb69c216ca11da06ab1101d23f19`（我在 target 上重算一致） |
| original_manifest_sha256 | `96894f8f72941d3dbe6b8341dca02c4caa44b8b59c51cd92c0f0c5318f389b55`（解压后重算一致；17 个成员逐个核对 bytes 与 sha，全部一致） |
| archive_readback_sha256 | `39c1600a780dd9d173fd2725b3f07aa5b9839626e2f113e943c7f3b86c57bffa`（文件重算一致） |
| archive | 10 段按字典序拼接，419,240,400 bytes，拼接后 sha `884519c159f22921fe1185b93b79c4d0c893c963ffbc0050fe2f8c074a75aaf1` |
| source_files（在 target 上重算） | `__init__` `ef9c51d5…`；`data_contract` `4bcb6227…`；`native_nfc_encoding` `c2af5621…`；`prepare_p011_long_inputs` `4468a80d…`；`prepare_p011_ot3_4032_inputs` `4546ffad…`；`prepare_p011_ot3_nfc_continuation` `c0aae4c1…`。与 INTENT.source_files 和 NFC CR 一致 |
| 链 | source lock `0e78298f…`；R1/R3 `e58e8d72…`；count amendment `5d1fa79a…`；NFC owner `26f14213…`；plan `20d919af…`；NFC CR = d85bd142 原报告（`c506e458…`）+ 3f298f2e 附录。INTENT 中各字段与这些值一致 |
| B / U | 41,813,212 / 654（A8 单遍最大） |
| grid | A1 (252,1)、A2 (252,2)、A3 (252,4)、A4 (252,8)、A5 (252,16)、A6 (1008,1)、A7 (4032,1)、A8 (1008,4) |
| 不授权 | 运行时、训练、付费预算、模型准入 |

## 独立核对（全部基于完整的原始 archive，脚本流式读取 1.09GB 的 ENCODED）

**身份与顺序**
- SELECTED_RAW、ENCODED、NATIVE_NORMALIZATION 各 10,080 行，path_id 唯一；三者行序相同，且按 path_id 排序 ✓
- `all_confirmed_hashes` 等于原失败包 PARENT_DISPOSITIONS 中 4,038 个合格父题按候选顺序排列；`selected` 是其前 4,032 个；未用尾部恰为最后 6 个 ✓
- 原始数据中的父题集合恰好等于这 4,032 个 ✓

**格子与嵌套**
- 8 格都严格等于"前 P 个父题 × 每题前 K 条回答"；各格大小正确；8 格并集正好是 10,080 条 ✓
- 每题回答数：252 题 16 条，756 题 4 条，3,024 题 1 条（252·16 + 756·4 + 3024 = 10,080）✓
- 对 16 条全部在包内的 252 个父题，我按 `ORDER BY source_file,row_index` 排序后，用 `Random(sha256(key+'p011')[:16])` 重新打乱：**252/252 与包内顺序一致** ✓
- 其余父题的回答顺序只能核对前缀嵌套（K=1 ⊂ 4），已通过；完整的 16 条顺序需要私有 SQLite，无法重算

**965 条复用**
- 新 SELECTED_RAW 前 965 行与原 4032 失败包的 965 行逐字节相同；新 ENCODED 前 965 行逐行 SHA 相同 ✓
- 失败包正好 965 行，`encoding_reused` 标志恰好是前 965 条 ✓
- 没有重新过滤或生成：父题来自原 disposition，回答全部来自原始行

**完整性与去污染**
- 10,080 条全部满足冻结的完整性规则 ✓
- 对 BENCHMARKS（与原失败包逐字节相同：math500 500、aime24 30、aime25 30、amc23 40）独立重算精确匹配加 13-gram：**0 命中** ✓
- difficulty 字段 10,080/10,080 缺失

**编码结构**（逐行 10,080 条）
- prefix 全部为 −100；监督区间连续，等于 ids，长度等于 n_supervised；区间末尾是 151645，内部不再出现 151645；最后一个 token 是不监督的 198；n_processed ≤ 16,384（最长 16,382，监督最短 1,108）：**0 个违规** ✓
- parent_sha256 等于 sha256(NFKC+strip(question))：0 个不一致 ✓
- 每个父题只有一种 prefix token 序列；所有 prefix 以 `151644 8948 198 …`（`<|im_start|>system\n`）开头 ✓

**NFC 证明记录**（我独立写出 Qwen2.5 默认 system 模板，不调用分词器）
- 9,115 条新编码：raw_native_text_sha 与我构造的原生文本一致，normalized sha 与"逐段 NFC 后拼接"一致；decoded sha 等于 normalized sha；question/response sha、字符数、`normalization_changed_text` 标志均一致：**0 个不一致** ✓
- 965 条复用：原生文本本身就是 NFC（0 例外），标志为 False ✓
- 5 条 NFC 改动全部在回答部分（不在 prompt 中），原因都是 COMBINING MACRON（a+U+0304 → ā 一类），字符数减少 2–67；`raw_text_rewritten=false`，SELECTED_RAW 中保留原文 ✓

**剂量与计划**
- 8 格单遍 token 数独立重算，与 FROZEN_DOSE 完全一致；B = max = A8；U = ⌈B/64000⌉ = 654 ✓
- 每格：row 顺序 = 格子；token 总数 = B；q = ⌊B/单遍⌋，即 16/8/4/2/1/4/1/1；每条曝光 q 或 q+1 次，所有回答至少一次；前 q 遍等于 `Random('17:pass:e')` 的打乱结果；extras 无重复，且总和**正好**等于 B − q·单遍；654 次更新都非空；exposures 字段一致 ✓
- extras 条数：A1 105、A2 120、A3 94、A4 108、A5 88、A6 4、A7 39、A8 0
- 用已 CR 的 `whole_schedule` 对 8 格重放，结果与包内计划**逐字段完全相等** ✓
- 每次更新的 token 数在 50,698–77,166 之间（目标 63,934）

**失败保留**
- 4096 充足性 FAIL：`FAILED.json` 原样保留，`automatic_retry_allowed=false` ✓
- 4032 严格往返 FAIL：原样保留（ValueError "Segmented native chat tokens must recover the exact original text"，00:51:57 UTC）✓

## 注意（需要披露）

1. **5 条回答没有闭合 `</think>`**：都以 `<think>` 开头，全文没有 `</think>`，按"最后 2,000 字符"规则判为完整。它们是：
   - `00042:8177`（A6/A7/A8）
   - `00045:5181`（A5）
   - `00047:6516`（A8）
   - `00059:9838`（A5）
   - `00109:4021`（A5）

   在 10,080 条中占 0.05%，影响很小。但学生在这几条上学到的是"思考不闭合就直接给出 boxed"。这与诊断请求中 N2 类规则的适用范围有关。

2. **强筛选子集**：只保留了 16 条回答全部完整的题，占 53,107 个候选中的 7.6%，并且 difficulty 不可用。A 网格的结论只适用于这个子集。只读诊断（target 980dd073，CR 已 PASS）还没有结果，**它不能改变这个已冻结的输入包**；如果触发预先约定的规则，由负责人决定是否重选。

3. **A1 格每条回答训练 16–17 次**：A1 有 252 题、每题 1 条回答，固定剂量下每条要训练 16 或 17 次；A2 是 8–9 次。这是固定 token 剂量设计的直接后果，过拟合风险需要在报告中写明。

4. **无法独立完成的部分**：
   - **分词器解码**：本机没有 transformers/tokenizers，也无法访问 HF。decode == NFC 文本这一点，我只核对了记录内的 sha 自洽，以及我构造的模板文本 sha 一致，**没有真正跑分词器**。
   - **私有 SQLite**（约 43GB）：其余 3,780 个父题的完整 16 条回答顺序、父键反查，都需要它，无法重算。
   - **私有验收文件**：`136a6750…` 是 Codex 本地的私有验收文件；公开的 ACCEPTED.json 是 `c0052769…`，省略了本地路径字段。我无法复现前者的哈希。

5. **剂量差异**：A5/A7/A8 的单遍量分别为 40.9M/41.4M/41.8M，A5、A7 有少量 extras。不同格之间同一条回答被看到的次数并不相同，这是设计本身的结果。
