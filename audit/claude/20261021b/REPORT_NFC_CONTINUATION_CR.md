# P011 OT3 原生 NFC 续作路径 CR

- **审计方**：Claude，2026-10-21 01:20 UTC 前后
- **请求**：`p011-OT3-confirmed-encoding-NFC-continuation-CR-r1`
- **scope**：`p011-OT3-confirmed-encoding-NFC-continuation-CR`
- **目标**：`10738e624300ff125c59fd127e798bc4e5fbdc85`
- **代码 packet MANIFEST**：`5d89938b…f2`
- **失败 packet MANIFEST**：`d7d7f1c6…93`

## 结论：代码层面 PASS-WITH-NOTES

执行还需要负责人的续作批准（见文末）。

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p011-OT3-confirmed-encoding-NFC-continuation-CR` |
| target_commit | `10738e624300ff125c59fd127e798bc4e5fbdc85` |
| source_files | 与 SOURCE_BINDING 的 6 个文件完全一致：<br>`__init__` `ef9c51d5…`<br>`data_contract` `4bcb6227…`<br>`native_nfc_encoding` `c2af5621a2917679dca59220b387cc7d60f2669cb4a40a5354607106d740447e`<br>`prepare_p011_long_inputs` `4468a80d…`<br>`prepare_p011_ot3_4032_inputs` `4546ffad…`<br>`prepare_p011_ot3_nfc_continuation` `c0aae4c117ff7815a552b92124da2e2d8c1bd144441fa6957e603ce36fe3719b` |
| plan / lock / R1R3 / count amendment / proposal | `20d919af…` / `0e78298f…` / `e58e8d72…` / `5d1fa79a…` / `7fc90198…` |
| original_failure_preservation / original_code_acceptance | `662d42e2…` / `54820eeb…` |
| parent_reuse_CR_acceptance / parent_attempt_fence | `521325fd…` / `4a27e880…` |
| failed_encoding_preservation / continuation_proposal | `99539e02…` / `05e6e5ba…` |
| confirmed_rows / remaining_rows / total_unique_rows | 965 / 9115 / 10080 |
| grid | 与 4032 方案相同 |
| 8 个标志 | confirmed_965_encodings_reused_byte_for_byte、same_10080_identities_and_cells、pinned_NFC_only_roundtrip、original_raw_text_retained、both_failed_parents_retained、new_global_attempt_fence、no_refilter_or_new_generation、operational_details_accepted：**均为 true** |
| owner_continuation_sha256 | **负责人批准记录产生后，以一行附录绑定**。附录只填这个 SHA；只有当记录中的 binding 与 OWNER_EXPECTED_BINDING 完全一致时才会填写 |

## 逐行审查要点

**`native_nfc_encoding.encode_complete`**
- 要求固定分词器后端的 normalizer 恰好是 `{'type':'NFC'}`。
- 分段方式（prefix / 回答+`<|im_end|>` / 换行）与原实现完全相同。
- 比对目标改为"各段 NFC 后拼接"，即 `decode == normalized`。分词器本来就会先做 NFC 再做 BPE，所以 **token 本身不变**，只是校验目标改成与分词器的实际行为一致。
- 不使用 NFKC，不去空白，不截断。除 NFC 以外的任何差异仍然失败 ✓。
- 原文、NFC 文本、解码文本各自保存 SHA，并记录是否发生了规范化 ✓。

**诊断与已确认的 965 条**
- 诊断中第 966 条只有两处 `a`+U+0304 被合并成 `ā`，与上述解释一致 ✓。
- 前 965 条在原代码下通过了严格的逐字比对，说明原文本来就是 NFC，规范化标志记为 False 是正确的 ✓。

**`confirm_prefix`**
- 原构建器按 `sorted(unique)` 的顺序写出，所以已确认部分正好是排序后前 965 个 path_id ✓。
- 逐条核对：原文逐对象相等；行尾完整；token 与 label 结构正确；EOS 是 151645；父题哈希一致 ✓。
- 之后按原字节复制，不重新分词 ✓。

**选题与计划**
- `append_remaining` 只对后 9,115 条调用新编码器 ✓。
- 题目和格子完全重建自原批准的 4,032 题顺序：`restore_keys` 和 `select_cells` 原样复用，数据库只读；结果是 10,080 条唯一回答、6 题未使用 ✓。
- 计划：B 取 8 格单遍 token 数的最大值，U = ⌈B/64000⌉，`whole_schedule` 不变；任何失败都会停下来，不提高 B ✓。

**防重跑与失败处理**
- 新的全局 attempt fence，新的 create-only 目录 ✓。
- 两个失败的父目录都只读、只核对哈希 ✓。
- `parent.admit` 会重新核对整条旧链 ✓。

## 注意

1. **测试没有在我这边跑**：本机没有 transformers，Codex 新增的测试无法导入。我对这 12 项测试只看了代码，没有运行。
2. **NFC 对训练和评测的影响**：训练 token 对应 NFC 后的文本。评测时的 prompt 也会被同一个分词器做 NFC，所以前后一致，不需要额外处理。
3. **执行前提**：这是对失败的一次独立续作，**需要负责人直接批准**（原 252/1008/4032 的批准不覆盖失败重试）。批准记录的 binding 必须与 OWNER_EXPECTED_BINDING 完全一致。记录产生后我补发附录，绑定其 SHA。
4. **OT3 完整性规则的诊断**：我已向负责人建议做一个只读诊断，看 90.8% 的剔除是回答本身造成的，还是检查规则误判。负责人尚未答复。这与本续作的代码正确性无关，但可能影响是否继续沿用当前选题，**请负责人在批准续作前先看诊断建议**。
