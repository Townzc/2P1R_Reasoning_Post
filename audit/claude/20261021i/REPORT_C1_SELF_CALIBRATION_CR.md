# C1 有界自校准：源码简短 CR

- **审计方**：Claude，2026-10-21 04:45 UTC 前后
- **共享请求**：`p011-C1-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-C1-complete-path-CR`

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| target_commit | `a253452a24368a34532e5c761b7bdb24cd634748` |
| binding packet | `c1_self_calibration_preflight_v1`，13 个 source 文件，在 target 上重算全部一致 |
| 变更 | 只有 `c1_admission` → `9e56c028…`、`c1_execution` → `2fad7192…`、`c1_outer` → `eb750bb4…` 三个文件；其余 9 个源码与 0c37b5a0 相同 |
| owner_decision_sha256 | `a08ba1abec5108b7ed583175151116f6a074626093c51148e783a5c1020506f0`。包内副本与我在 a2817992 提交的原文逐字节相同 |
| measurement_exceptions | 1（仅限 C1 的这一次逻辑尝试） |

REVIEW_REQUIREMENTS 中的 **6 个 source_flags 全部成立**：

| flag | 值 |
|---|---|
| `actual_tokens_masks_summary_unchanged` | true |
| `bounded_in_run_self_calibration_accepted` | true |
| `first_completed_cycle_immediately_forecast` | true |
| `load_watchdog_from_original_worker_start900s` | true |
| `no_historical_proxy_in_self_calibration` | true |
| `original_once_only_fences_retained` | true |

## 逐行要点

- **`validate_spec`（自校准分支）**：以下条件全部满足才放行：
  - `complete_chunk_seconds == []`，`measurement_basis_accepted is False`；
  - owner 文件已列入 source_files 且 sha 一致；
  - worker ≤ 2400，platform = worker + 60，startup = 600，allowance = 300，load 截止 = 900；
  - reserve **严格等于** ⌈rate × (startup + platform)⌉ 且 ≤ $4。

  原代理路径仍然要求非空的实测计时，并要求 accepted=true ✓
- **`initial_admission`**：只检查 reserve、窗口和类别：prior + reserve ≤ 12，reserve ≤ 80% × (12 − prior)。不做任何预测 ✓
- **`forecast`**：自校准时**完全忽略** spec 中的计时，只使用本次运行的完整轮次时长；没有实测值时拒绝预测 ✓
- **`run_body`**：
  - 加载看门狗的截止时间 = min(deadline, worker_start + 900)，计时器复用 worker 的 `os._exit` 计时器；加载完成后再检查一次截止时间，并写 LOAD_WINDOW ✓
  - 第 0 个 chunk 的 FORECAST 只做 initial_admission；之后每个 chunk 开始前都用实测轮次做 forecast ✓
  - **每一轮结束后（包括第 1 轮和最后一轮）立即做 POST_FORECAST**。如果预测超过 worker − 30，或者预测费用超过 reserve，就抛出异常并写 FAILED，下一个 chunk 不会开始 ✓
  - 由于 reserve = rate × (600 + worker + 60)，且预测秒数 ≤ worker − 30，费用条件与时间条件自洽 ✓
- **`check_body`**：只读回放，覆盖 initial、LOAD_WINDOW、每轮的 FORECAST 和 POST_FORECAST。剩余 chunk 数的两种写法我做了对照，包括最后一个只有 26 条的不满 chunk，结果一致 ✓
- **`fresh_budget`**：新鲜预算中的 `usd_per_second` 必须与 spec 中的费率完全相等，这把 reserve 绑定到实际费率上 ✓
- **`reviewed_path`**：自校准时，review 还必须包含 `owner_decision_sha256` 和 `bounded_in_run_self_calibration_accepted=true` ✓

## 测试

- 新增 8 项，加上 whole-iteration 4 项、io_window 3 项，共 15 项全部通过。
- 旧测试我用补丁后的 fixture 重跑了 51 项，结果与上次相同：只有 1 项因为没有 torch 无法导入，另 1 项是我补丁造成的假失败。

## 注意

1. 加载看门狗或 worker 硬计时器触发 `os._exit` 时，来不及写 FAILED。partial 和 claim 会保留，这次尝试视为已消耗。这一点已经在设计中说明。
2. 第 1 个 chunk 期间没有预测保护，只有硬计时器；最坏损失就是 reserve（≤ $4），这在负责人批准的范围内。
3. 本 PASS **不授权上传或派发**。A2-lite 还需要在同一请求下绑定以下内容：
   - 实际 SPEC 文件；
   - 新鲜费率和预算证据，其中 `usd_per_second` 与 spec 相等；
   - 原 6 个 admission 标志；
   - `measurement_exceptions=1`；
   - owner sha，以及 `bounded_in_run_self_calibration_accepted=true`。

   Codex 提交后，我会尽快给出结论。
