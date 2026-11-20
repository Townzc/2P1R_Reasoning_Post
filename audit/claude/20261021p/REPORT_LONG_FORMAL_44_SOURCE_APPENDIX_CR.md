# 长序列正式 A/D：current-owner 与资产复用附录，源码 CR

- **审计方**：Claude。git 提交时间见本 commit；我从 10:45 UTC 开始审阅
- **请求**：`p011-long-A-D-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-long-A-D-complete-path-CR`（只做源码这一阶段）
- **target_commit**：`61989e7b43c3d9d309047cc615b3dc12aba689db`（在 HEAD `6ae79c06` 上核对）

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| packet | `reports/p011_20261020/long_current_source_addendum_v1`，SOURCE_BINDING `c70f6c311783f119a45804d1b7db3e348688daf7f5da5a1b132c19c942a1803d` |
| source_files | **44 个**，SOURCE_BINDING 与 REVIEW_REQUIREMENTS 一致，HEAD 上逐个 sha 一致 |
| 44 个文件的组成 | 原 37 个与已接受的正式修复源码映射（`long_runtime_repair_v1`，即 R1–R3 报告 7c67c4d4）逐项相同。新增 7 个：`c1_r2/__init__.py`、`c1_r2/parent.py`、`failed_attempt_ledger.py`（这 3 个我已在之前的报告中逐行审过），以及本次的 4 个新文件 |
| owner_decision_sha256 | `364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f`；OWNER_BINDING `c2a84e2e…` |
| actual_input_directory | `long_inputs_numeric_gold_r1`；ACTUAL_INPUT_BINDING sha `cee34dc05189b785fe92e4c6384f8afb28a6ec26d1e60871d8fdbba3ea70deb3`（已重算）。A1 已由 dccd0876 在 63e8710f 接受 |
| measurement_exceptions | 0 |
| complete_source_closure_accepted | **true** |
| science_functions_unchanged | **true** |
| current_owner_accounting_only_no_scientific_measurement_exception | **true** |
| failed_B_and_C1_reservations_and_permanent_fences_retained | **true** |
| completed_input_locator_and_asset_receipt_reuse_accepted | **true** |
| local_audit_uses_pinned_metadata_not_absent_weights | **true** |
| 不授权 | 上传、正式调用、输入构建。正式 A/D 仍需：三臂预检实测结果、具体 SPEC、数值 A2-lite（9 个 flag），以及按 §2 由我做出的冒烟选择 |

## 逐项（4 个新文件，分别对原文件做 diff 后逐行审阅）

- **`long_current_path.py` 对比 `long_path.py`**：
  - 科学部分没有改动：训练、endpoint、计时策略、logical ID、fence、worker 主体、结果窗口都与原文件相同。worker 内对远端模型字节的完整校验，以及对 EOS 列表的校验，都保持不变。
  - `validate` 新增要求：`budget_owner_decision_sha256 = 364aaf6c`、`prior_failed_C1` 和 `failed_attempt_bindings` 不为空、输入目录固定为 `long_inputs_numeric_gold_r1`、input binding 是 64 位 hex。另外要求每个 job 的本地审计元数据至少包括 config、generation_config、tokenizer、tokenizer_config，范围不超出允许的名单，且每个文件都等于固定模型文件的 sha；预检资产回读收据的路径固定为 `long_preflight_io_r1/model_uploads/<revision>/COMPLETED.json`。
  - `reviewed` 新增 5 项绑定和 2 个 flag。
  - `budget_check`：protected 从 48 改为 0，口径改为 `owner_current_balance_minus_retained_P011_reserves_and_meter_growth`，这与负责人 364aaf6c 的决定一致；同时要求可用余额是有限值并且 ≥ reserve。另外加了时间类型和有限性检查。80% 规则仍由未改动的 `long_numeric.forecast` 执行 ✓
  - 账本改用 `failed_attempt_ledger.ledger`，并接上 `parent.records_with_failed_parent` 和两组 fence 读取，与已接受的预检路径相同 ✓
- **`p011_long_current_io.py`**：
  - upload 不再传输模型文件，而是要求预检时写下的资产回读收据：路径固定、不是 symlink、sha 等于 SPEC 绑定，内容严格等于 `{model_files, remote_path, all_remote_file_bytes_read_back: True}`。我核对了预检 IO 的 upload，它写入的正是这个结构 ✓ 输入文件仍会上传并回读。
  - collect 本地只校验固定的元数据子集，不需要本地不存在的 1.5B 权重，也不加载模型 ✓
- **`modal_long_current.py`、`analyze_p011_long_current_pair.py`**：只改了 import ✓
- **import 闭包**：4 个新文件引用的仓库内模块都在 44 个文件之内 ✓
- **测试**：`tests/test_p011_long_current_path.py` 7 项在本机全部 OK。

## 注意

1. **资产收据依赖预检**：正式格要求对应 revision 的预检上传收据已经存在。如果所选的臂在预检中没有完成上传（例如 3B 预检没有运行），正式上传会 fail-closed，需要另行处理，不能临时补传。
2. 数值 A2-lite 要用三臂预检的**实测**计时和内存数据外推正式格。32 条请求不能代表 512 条一批的吞吐，外推依据必须明确写出；measurement_exceptions = 0。
