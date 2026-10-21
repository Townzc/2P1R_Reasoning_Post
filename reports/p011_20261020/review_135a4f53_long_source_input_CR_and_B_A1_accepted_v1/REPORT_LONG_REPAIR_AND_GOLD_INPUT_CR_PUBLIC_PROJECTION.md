# 长序列 A/D：R1–R3 修复复审，以及数值 gold 输入替换 CR

- **审计方**：Claude，2026-10-21 06:55 UTC 前后（负责人夜间全权审核期间）
- **请求**：`p011-long-A-D-complete-path-CR-A1-A2-lite-r1`
- **target_commit**：`e6ce0467ded06b4bd09487e7843f5bf2f6f6924e`
- **binding**：`long_runtime_repair_v1`，MANIFEST `bef8279d…`，SOURCE_BINDING `872a1d4e…`。我在 HEAD `36c21018` 上逐个重算了 37 个 source，全部一致。

---

## 1. 运行时源码复审（scope `p011-long-A-D-complete-path-CR`）—— **PASS**

| flag | 值 |
|---|---|
| complete_source_closure_accepted | true |
| full_parameter_96GiB_host_and_mmap_accepted | true |
| endpoint_512_batch_256_seq_geometry_accepted | true |
| science_functions_unchanged | true |

### R1：源码闭包已补全

- `src/sft_data.py`（`8163fe14…`）和 `src/__init__.py` 已加入闭包。
- `long_path.validate` 新增硬性检查：这两个文件，以及 long_checkpoint、long_protocol，必须都在 `source_files` 里。
- 我用 AST 重新扫描了 37 个文件，本仓库内的 import **没有遗漏**。

### R2：全参训练的内存问题已解决

- `long_protocol.resources` 把 S-F15 的内存设为 98,304 MiB，其余臂为 32,768 MiB。`modal_long` 按 job 读取这个值。
- `long_path.validate` 要求 job 的小时费率等于 H100 + 4 × CPU + 内存 GiB × 单价，所以内存费用已经计入费率。
- 新的 `long_checkpoint.save` 写盘后用 `torch.load(mmap=True)`，再逐个张量做 `same()` 比对，内存中只有一份 snapshot，约 18.6 GB，在 96 GiB 之内 ✓
- 原来的 checkpoint 模块没有改动。

### R3：评测改为大批量

- 每批 512 条，共 7 批（`ENDPOINT_BATCHES`），`max_num_seqs=256`，CUDA graph 的 capture sizes 扩到 256。
- 下列各处都已同步改用这组常量，不再有 104 或 32 的硬编码：`evaluate`、`engine_settings/validate_engine`、forecast、`long_evidence.expected_units / verify_endpoint`、训练子进程中的 forecast，以及 `long_path.policy / budget_check`。
- 请求、seed、采样参数、gold-free 投影都没有改变 ✓

### 科学函数未改

`learning_rates`、`validate_plan`、`accumulate`、`train_terminal`（只把 checkpoint 写入换成 long_checkpoint）、`request_roster`、`sampling`、`answer_region`、配对 bootstrap，全部未改。

### 测试

- 新的 `test_p011_long_repair_r1`：13 项中 11 项通过，另外 2 项因本机没有 torch 无法导入。
- 其他旧的 long 测试有多项报错，原因是旧 fixture 仍按 32 条一批、没有 src 闭包、没有 resources 字段来写，被新的验证拒绝了；另有一部分是本机缺 torch。这说明新的门槛确实生效。
- 建议在 A2-lite 之前把旧 fixture 更新到新的几何设置，让完整的模拟闭环在最终源码上跑一遍。这一条不阻断。

### 注意

- 96 GiB 内存和 mock 测试都**不能证明真实 GPU 上不会出问题**，以下几点需要 GPU 预检来确认：
  - 16k 全参训练的显存峰值；
  - `use_deterministic_algorithms` 在反向传播中是否报错；
  - vLLM 在 max_num_seqs=256、capture 到 256 时的启动时间。
- 预检已获负责人批准（20261021k，reserve 合计 ≤ $6）。预检的 SPEC 和 A2-lite 要单独提交。
- Codex 文件中写的"R4 未授权""A/D D1 口径未定"已过时：负责人已在 23:02 PDT 作出决定，见 `20261021k/OWNER_DECISION_BUDGET_AND_GPU_PREFLIGHT.md`（sha `364aaf6c…`）。
[Private current-balance line omitted; original bytes and SHA retained locally.]
  - 不再保留 $48；
  - 子上限不变；
  - 预检已批准。
[Private current-balance line omitted; original bytes and SHA retained locally.]

---

## 2. 数值 gold 输入替换（scope `p011-long-numeric-gold-input-replacement-CR`）—— **PASS**

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| target_commit | `e6ce0467ded06b4bd09487e7843f5bf2f6f6924e` |
| source_files | 与 `long_runtime_repair_v1/SOURCE_BINDING.json` 中的 37 个文件完全相同 |
| input_basis_files | 与同一 binding 中的 input_basis_files 完全相同，包括原失败证据 `ba9838a6…` |
| owner_decision_sha256 | `9c02012181100feac80ce29855de189d8436251d8b9aaab875e59347c72cbd21`。原话为"批准一次 CPU 续作，复审后执行"，proposal 为 `a7b730e0…`，二者已核对一致 |
| input_preparation_authorized | **true** |
| original_failed_attempt_retained | **true** |
| numeric_gold_semantics_unchanged | **true** |
| old530_prompts_not_saved_no_false_reuse_claim | **true** |
| one_new_cpu_attempt_only | **true** |

**逐行要点**

- **失败原因**：原输入准备（CLI 37318）因 AIME25 的 gold 是整数而失败，被只接受字符串的检查拒绝。原尝试的 fence、日志和 FAILED 记录全部保留，不重试 ✓
- **`long_gold_input.benchmark_projection`**：
  - 字符串原样保留；整数转为 `str(int)`；有限且为整数值的浮点数转为 `str(int(x))`；
  - bool、非有限值、非整数值、结构化值一律拒绝；
  - 这些检查都在任何 tokenization 之前完成；
  - 每一行都记录原值、原类型和投影后的 sha ✓

  NUMERIC_SCALAR_DOMAIN 显示 40 个浮点数都是整数值。题目文本和 tokenization 都不受影响。
- **新入口 `prepare_p011_long_numeric_gold_inputs`**：
  - 运行前核对：review 的 5 个 flag、owner 文件、37 个 source、input basis；
  - 新输出目录为 `long_inputs_numeric_gold_r1`，在原失败目录存在时才允许运行，并写入新的 attempt fence；
  - `request_roster` 对 600 个 prompt 全部重新编码，不声称复用之前的 530 个；
  - `consume` 比对的是**原始** BENCHMARKS，训练用的编码和 plan 照旧复用；
  - 1 小时硬计时器，不重试 ✓

**授权范围**：一次 CPU 运行。不涉及 GPU，不产生付费调用，**不包括**实际输入 A1 和 A2-lite。
