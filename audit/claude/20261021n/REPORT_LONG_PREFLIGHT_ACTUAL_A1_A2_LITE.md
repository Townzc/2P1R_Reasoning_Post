# 长序列三臂工程预检：实际子集 A1 + 数值 A2-lite

- **审计方**：Claude，2026-10-21 09:20 UTC 前后（负责人夜间全权审核期间）
- **请求**：`p011-long-three-arm-engineering-preflight-CR-A1-A2-lite-r1`
- **final scope**：`p011-long-three-arm-engineering-preflight-CR-A1-A2-lite`
- **target_commit**：`67877fc1c26ad2dac391cd9daa72f74dcf0d8a08`（我在 HEAD `4edf3e83` 上核对）

## 结论：PASS（只授权这 3 个工程调用）

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| original_plan_commit | `e0dee182972f9910b707fac68800dcb5a3aff2d3` |
| spec_sha256 | `b62db53109fe72b9418deaea3dce86b7064822122e324f406f5955937fab52f5`（文件 sha 已重算） |
| jobs_sha256 | `d87c67f03a65f7d0d76f6b90bf970414b9ac69a205bce57a824bb3fad9539a29`（digest(jobs) 已重算） |
| source_files | 33 个，与 SPEC、REVIEW_REQUIREMENTS、此前 source CR（`long_preflight_source_v1`，我的 dccd0876）三处完全相同；HEAD 上逐个 sha 一致 |
| owner_decision_sha256 | `364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f` |
| measurement_exceptions | 3（仅这 3 个工程预检调用；正式 A/D 仍为 0） |
| formal_repair_review_sha256 | `7c67c4d4c5afd2a874f1bd3dfc3e6654f369decca35ccede67d53da65bf3ff40` |
| actual_input_binding_sha256 | `80cad9f9…`（已核对） |
| complete_source_closure_accepted | **true** |
| actual_input_A1_accepted | **true** |
| formal_R1_R3_source_CR_accepted | **true** |
| engineering_subset_of_formal_path_accepted | **true** |
| all_three_reserves_at_most6_accepted | **true** |
| full_state_export_join_and_original_engine_accepted | **true** |
| original_failed_parent_retained | **true** |
| current_owner_budget_scope_and_full_window_accepted | **true** |
| no_scientific_result_or_A3_A5_claim | **true** |

## 1. 实际子集 A1（独立脚本 `a1_pf.py`，结果 `A1_PF_RESULT.json`）

- **归档**：`original_subset_inputs.tar.gz` sha `d2ebfcad…` 与 ARCHIVE.json 一致；解出 20 个成员，内部 MANIFEST 19 项逐个 sha 一致。
- **源数据**：我用 OT3 的 ENCODED.jsonl 按 A8 plan 的 `row_path_ids`（4,032 行）独立重建 A8 有序行，digest 等于 A8 ORIGINAL_ROWS 的 `original_row_values_sha256`，也等于子集 plan/proof 中的 `source_encoded_sha256` ✓ endpoint 源 digest 等于原 ENDPOINT_GPU ✓
- **训练子集**：按 (−n_processed, path_id) 独立取前 2 行，与三个臂的 `encoded.json` 逐对象相同：
  - n_processed = 16,340 / 16,333，n_supervised = 16,287 / 16,254（第 3 长为 16,306，选择无歧义）；
  - 掩码 `labels = [-100]*start + ids[start:end] + [-100]*…`、末 token 151645、长度 ≤ 16,384，两行全部通过；
  - plan：U = 2，updates = [[0,1],[0,1]]，seed 17，B = 2 × 32,541 = **65,082** ✓ processed = 65,346 ✓
  - LR：按原 warmup+cosine 公式 U = 2 重算，S-L15/S-L3 为 [1e-4, 1e-5]，S-F15 为 [1e-5, 1e-6] ✓
  - **没有重新 tokenization**，只是对已验收编码的只读切片。
- **评测子集**：按"每个 benchmark 取 sample/seed0、按 prompt 长度降序、取第 ⌊i(n−1)/7⌋ 个，MATH 最后一个换成最长题的 greedy"独立重算，与三个臂的 ENDPOINT_GPU 逐对象相同：
  - 4 个 benchmark 各 8 条，共 32 条（31 sample + 1 greedy），最大 required_context = 17,243 ✓
  - ENDPOINT_GPU 不含 gold，并且正好等于 ENDPOINT_LOCAL 去掉 gold、加上 request_sha256 的投影；ENDPOINT_LOCAL 与原 3,300 条 local 中的对应行相同 ✓
  - ENDPOINT_LOCAL 只出现在 `local_input_files`，不在上传用的 `input_files` 中 ✓
- **跨臂**：encoded、plan、ENDPOINT_GPU 三臂字节相同；只有 rates 和 SUBSET_PROOF 因臂不同而不同 ✓ COMPLETED 中各文件 sha 与实际文件一致，model_calls = 0。

## 2. 数值 A2-lite

| job | 内存 | 小时费率（重算） | reserve = ⌈rate × (600+960)/3600⌉ |
|---|---|---|---|
| preflight_S-L15_s17_r1 | 32 GiB | 3.95 + 4×0.0473 + 32×0.008 = **4.3952** | **1.91** |
| preflight_S-F15_s17_r1 | 96 GiB | 3.95 + 0.1892 + 0.768 = **4.9072** | **2.13** |
| preflight_S-L3_s17_r1 | 32 GiB | **4.3952** | **1.91** |
| 合计 | | | **5.95 ≤ 6** ✓ |

- 费率来源：08:44:25 UTC 的 `modal billing rates` 回执（sha `6bc0006b…`），H100 3.95、CPU 0.0473、GiB 0.008，与 CURRENT_RATES 一致。
- **窗口**：startup 600 + platform 960 + closeout 7,200 = 8,760 s = full_result_window ✓ 最晚派发时间 = 截止 05:00 UTC − 8,760 s = **10/22 02:34 UTC** ✓ worker 内部再次检查 `start + worker + closeout ≤ CUTOFF`。
- **预算口径**：预检记在 A 类。`budget_check` 要求：P011 已保留合计 + 本次 ≤ 180；本次 ≤ 0.8 × (115 − A 已保留)；三个工程预检累计 ≤ 6；可用余额基于负责人"$228 当前可用、不再保留 48"的口径，C1 两次 6.38 和 B 生成 3.01 都保留不释放 ✓
- **模型**：
  - 1.5B-Instruct（revision `989aa798…`）：使用原 producer 的远端路径，worker 内逐文件核对 bytes 和 sha，本地不下载 ✓
  - 3B-Instruct（revision `aa8e7253…`）：9 个文件与已验证的 `QWEN3B_ASSETS_VERIFIED.json`（`617f6c03…`）逐个相同。按 SPEC，**只在本 A2 通过后**上传一次，再由 worker 回读核对 ✓
  - worker 还会核对 generation_config 的 eos 列表等于 [151645, 151643] ✓
- **测量保全**：模型加载、训练每个阶段、checkpoint/export、引擎启动、endpoint 进度都在各自阶段后 commit；即使 900 s 超时，已完成阶段的计时也会保留，失败会写 FAILURE 和 terminal，不自动重试 ✓

## 3. 注意（不阻断）

1. **S-F15 可能超时**：全参训练 + 约 18.6 GB 的完整 state 写盘 + mmap 核对 + 导出，再加上 vLLM 启动和 32 条最长 16k 的生成，900 s 可能不够。这是负责人接受过的风险（总 reserve ≤ 6，没有余量再加时间）。如果超时，失败和 reserve 都保留，**不重试**；S-F15 的 A 格能否运行需要按已保存的分阶段计时另行判断，可能需要负责人决定。
2. **32 条请求不能代表正式 512 条一批的吞吐**。正式 A/D 的派发仍需单独的冒烟（smoke）A2-lite，其中要有明确的外推依据，measurement_exceptions = 0。
3. **并发槽**：B 生成已占 1 个，三个预检再占 3 个，正好 4 个。B 的学生和 C2 要等槽位释放。
4. 本授权只覆盖 3B 资产一次上传 + 3 个预检调用各一次；不包括任何正式 A/D 格、重试或其他上传。
