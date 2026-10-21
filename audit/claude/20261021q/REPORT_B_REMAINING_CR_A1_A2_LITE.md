# B 续跑（剩余 5,120 条）：CR + A1 + A2-lite

- **审计方**：Claude。以本报告的 git 提交时间为准（首版 4e044eac，11:41:24 UTC）
- **请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-B-remaining-generation-complete-path-CR-A1-A2-lite`
- **target_commit**：`5993ccef3da13a68b9c988a173b36de8161e9974`（在 ccb5dfc8 上核对，相关文件未变）

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| spec_sha256 | `3b0bf017ed30803e3bf9c6b20877766e0a71b9a69791c112870df319f383d43b`（`b_remaining_current_runtime_v1/SPEC.json`） |
| source_files | **91 个**，与 SPEC 和 REVIEW_REQUIREMENTS 的 binding 完全相同，HEAD 上逐个 sha 一致。digest `4d9c70bc…`；SOURCE_BINDING 文件 `1f450330…` |
| jobs_sha256 | `6bcd18c7729a1f63d2c5f42512300c0f5475d270a7fa8aa7ab4b8a5b33d153fa` |
| failed_attempt_bindings_sha256 | `698167fa6dddf11d64c6c1e7dafb1761c97c08a418e74cdafbfb87450b36b06f` |
| prospective_students_and_score_window_sha256 | `eef07e3f8e2d688e42f367efee580c32359263937f196b2e84e81a8b495de400` |
| prefix_files | 23 个，与 SPEC 一致（digest `ef596b35…`） |
| owner_B16_sha256 | `2e0c8af11de76ac34368f9188d3731b2ac89d0e47e5870e8684e3d55c4953f60` |
| budget_owner_decision_sha256 | `364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f` |
| delegated_failure_decision_sha256 | `8ca01d6f5d5f5e2dbe58b2e694aaa21685d3398d22d0e1c61d853a01fa92abf8` |
| delegated_failure_erratum_sha256 | `fa73636a836a6fef05eb7620eb992cdb7a719003678d306f9c30f57e1e4466e2` |
| measurement_exceptions | 0 |
| 14 个 flag | **全部 true**：complete_source_closure_accepted、complete_actual_input_A1_accepted、original_P010_tokens_seeds_dose_and_endpoint_rules_unchanged、all_original_complete_timing_sources_accepted、full_state_raw_scoring_window_and_budget_accepted、remote_paths_traced_to_producers、owner_B16_selection_and_actual_Pcov_accepted、current_owner_accounting_and_saved_failed_parent_accepted、original_complete_cycle_interval_proxy_accepted、old1280_raw_and1024_transport_byte_reuse_and_new5120_only_accepted、unmapped_before_EOS_rule_and_all_training_exclusions_accepted、full6400_first_scoring_including_unscored1280_and_denominators_accepted、E3_wall_time_and_two_student_sequential_budget_full_windows_accepted、reported_B48_clause_void_current_protected0_accepted |
| 批准范围 | 续跑生成的派发只能这一次，**在 13:54:30 UTC 之前**完成，并且要先通过新鲜的费率、D1、共享槽位、未使用 fence 和完整窗口检查。之后的 collect、audit，以及对 6,400 条的首次评分（评分上限 7,200 s） |
| 不批准 | B1/B2/B3 学生（另需输入 A1 和数值 A2-lite）；学生输入准备（`student_input.source_authority` 要求另一个 scope `…-selection-complete-path-CR`，以及 `input_preparation_authorized`）；任何重试 |

## CR：16 个新文件，与对应的原文件逐个做 diff 后逐行审阅

- **`b_remaining/transport.py`**：与我的决定 §2.1 逐条一致。
  - 映射行，以及"无 EOS、长度 1024、finish = length"的行，都交给原 P010 函数处理。
  - 其他含未映射 ID 的行：要求第一个原生 EOS 存在，且所有未映射位置都在它之前，否则 fail-closed；记为 `invalid_special_token`，`retained = p+1`，解码只取 `ids[:p]`。
  - 越出模型词表的 ID 一律 fail-closed。
  - `validate_saved` 只做只读检查，不再解码一遍（见注意 2）。
- **`execution.py`**：
  - `copy_prefix` 要求恰好 23 个文件，逐字节复制后核对 sha；同时核对 5 批的 INTENT 成员（first、requests、sampling）、raw 身份，以及前 4 批 ACK 对 raw 和 transport 的 sha。
  - 第 004 批的 transport 只做一次，有独立 fence（`prefix_transport/004`、`…_done/004`）。
  - 新生成只覆盖第 5–24 批，参数切片 `[(n-5)*256:(n-4)*256]` 正确；每批的 fence、ACK、周期计时与原代码相同。
  - FAILED 中写明父任务不变，不重试。
- **`path.py` / `current_path.py`**：
  - logical ID、key（`b/generation_remaining_r2`）、BASE（`b_remaining_runs_r2`）都是新的。
  - 前缀从原 worker 的输出目录 `/evidence/p011-20261020/b_runs_r1/B_generation_t10_400x16_r1/generation` 读取。我核对了原 worker：`out = BASE/logical`，生成在 `out/generation` 下 ✓
  - validate 固定 limits 为 1800/1860/600/7200/14405/16865/3.01，reserve 按 H100、4 CPU、32 GiB 的费率重算。
  - budget_check 采用 protected 0、`available − reserve ≥ 0`、≤180、完整窗口、`now < latest_continuation_dispatch_epoch`，不跨类别。账本合并失败的父任务和 C1，并读取两组 fence。
  - submit 要求原上传收据的 sha 等于 SPEC 中的值，且 job_sha 等于原 job。
  - worker 主体与已接受的 `b_path` 相同。
- **job 配置**：与已接受的 `b_generation_runtime_v1` 原 job 相比，只有 `limits` 和 `prefix_files` 不同；`digest(原 job)` 等于 `original_generation_job_sha256` ✓ 因此输入目录、模型、采样都不变。
- **`loader.py`**：只把 transport 和 selection 换成新版。
- **`selection.py`**：
  - K1 的回退是"按尝试顺序第一条映射行"；16 条全含未映射 ID 时该题缺席。
  - K4/K8 只在映射行中取可用且文本去重的解。可用行本来就要求 native_eos，因此与原规则等价。
  - `denominator_report` 同时给出主口径、剔除未映射行后的敏感性口径，以及每批的计数。
- **`evidence.py`**：完整 6,400 条的文件清单（没有多余文件，也没有 symlink），以及前缀 sha、INTENT、COMPLETED、每批成员、ACK、新批次的 fence 和 forecast 回放。
- **IO**：
  - upload 直接 raise，即不重复上传。
  - audit 本地只核对非权重文件，用于加载分词器。
  - collect、audit、score 的目录都是新的 r2。
  - 评分前要求 oracle passed。
- **`student_input.py`**：训练行里出现未映射行就 raise；K1 期望集合 = 400 − 全未映射题；记录 `unmapped_training_rows: 0` ✓ 本次不批准运行。
- **import 闭包**：从三个入口出发可达 73 个仓库内模块，全部在 91 个文件之内 ✓
- **测试**：3 个测试文件共 25 项，本机全部 OK。

## A1（复用的数据）

- 我自己解开公开归档，核对 23 个前缀文件：sha 和字节数**全部一致**。
- 1,280 条 raw 按 `check_raw` 的口径逐条比对（candidate、problem、prompt、sampling、`source_row_sha256 = None`、`output_count = 1`），**0 条不符**。
- 前 1,024 条原 transport 用 `validate_saved` 做结构检查，全部通过。
- 前 5 批只有 1 行含未映射 ID（`…482::attempt09`，位置 16，EOS 在 374），符合新规则，不会 fail-closed。所有 ID < 151,936；没有 EOS 的行全部属于原来的"跑满 1024"例外。
- 生成输入沿用原生成已接受的实际 A1。

## A2-lite（数值）

- **生成**：1.2 × (20 × 22.95 + 600) ≈ 1,271 s ≤ worker 1,800 ✓ 前缀复制约 20 MB，第 004 批 transport 只是 CPU 解码，可以忽略。
- **评分**：E3 从评分开始到下一依赖阶段开始的记录区间 W = 107.35 s ≤ 360，2W × 10 = 2,147 ≤ 7,200 ✓ 这个区间包含了空闲间隔，偏保守，不是新的实测，接受。
- **预算（B 上限 20，protected 0）**：
  - 失败 3.01 + 续跑 3.01 = 6.02。
  - B1：6.18 ≤ 0.8 × 13.98 = 11.18 ✓
  - B3：6.18 ≤ 0.8 × 7.80 = 6.24 ✓
  - 合计 18.38 ≤ 20 ✓ 其中 6.18 = 4.3952 × 5,060 / 3,600 ✓
  - 余量很窄：B2 实际上已经放不下，B3 的余量只有 $0.06。
- **时间**：续跑 16,865 s + 学生 37,465 s = 54,330 s；1792645200 − 54,330 = 1792590870，即 **13:54:30 UTC** ✓

## 注意

1. **B3 的 80% 余量只有 $0.06**。派发学生时，新鲜费率如果上涨，B3 就会被规则挡住。到那时按规则处理，不另开例外。
2. **audit 不再重新解码**：`validate_saved` 只核对 raw 的 hash 和 stop 结构，不重新解码新的 5,376 条（5,120 条新输出加第 004 批）。我接受这一点作为 A2 的范围，但 **A3 必须从原始 token 独立重新解码并评分**；B 的任何数字在 A3 之前都不得引用。
3. 第 004 批的 255 个映射行在此之前从未做过 transport。如果其中有某种我没预见到的异常，续跑会 fail-closed，按 §五关闭 B，不重试。
