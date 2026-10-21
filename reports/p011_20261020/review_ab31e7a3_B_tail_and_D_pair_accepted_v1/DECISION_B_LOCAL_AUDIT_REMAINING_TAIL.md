# B1/B3 本地 oracle 因环境失败：委托例外 + 101 源码 CR

- **决定方 / 审计方**：Claude，委托授权。以本报告的 git 提交时间为准
- **scope**：`p011-B-first-local-audit-remaining-tail-exception-CR`
- **target_commit**：`30e5a71ba4c74cb49af42b95d34b80c0c42c5e38`
- **SOURCE_BINDING**：`92a2748b6672021fbccba413b50f780d592b80862159ea7c6dd4c29b35e83de3`（101 个源码 = 原 100 个不变 + `scripts/continue_p011_b_student_local_audit.py`；sha 全部一致）
- 其余绑定：failure_binding_digest `c0f88374…`；original_acceptance_file `f9f24534…`；original_failure_packet_manifest `8846dd07…`；original_jobs_digest `a4c5fc8f…`；original_model_spec `4270e923…`

## 结论：PASS，并批准例外：每个 job 只在本地跑一次剩余的 oracle

**失败完整性**：
- B1/B3 的模型（94581/44421）和收集（8411/10573）都已完成，并确认 STOPPED0。
- 本地审计（44679/32774）在 `from transformers import AutoTokenizer` 处因解释器缺少依赖失败。按原 audit 函数的顺序，失败之前的步骤都已执行并通过：命名记录、派发和预算回放、解包、身份和计时、输入和本地元数据校验。
- 之后的分词器加载、状态和轨迹 oracle、解码都**从未执行**。这是运行环境选错了，不是科学失败。

**CR**：
- 我逐行对照了 `remaining_tail` 与原 `audit()` 中学生分支在 import 之后的代码：gold sha 和 500 行检查、`verify_training`、`verify_endpoint`、DECODED / SCORING_ROWS / COMPLETE_PROOF 的内容**逐项一致**。只多了两处：用只能新建的写入（`open('x')`），以及在 proof 中附加例外的绑定 ✓
- 进入前的检查：
  - 失败必须恰好是这个 ModuleNotFoundError，且没有任何输出文件；
  - 解包元数据与收据一致；
  - 原绝对截止时间不重置；
  - 新的永久 fence `b_audit_remaining_r1/<job>`；
  - 源码和绑定必须已发布；
  - 原审查与本审查都必须通过 ✓
- 原 FAILED.json 保留，不删也不覆盖 ✓
- 测试在本机 OK。

## 7 个 flag：全部 true

one_remaining_local_audit_per_original_B_job_explicitly_authorized、original_failed_audits_and_extractions_retained_without_repeat、unchanged_original_state_token_scientific_checks_accepted、new_permanent_continuation_fences_and_original_absolute_windows_accepted、append_absent_proof_files_only_original_FAILED_retained_accepted、unchanged_first_score_and_analysis_paths_with_correct_interpreters_accepted、original_input_A1_model_CR_and_complete_collections_accepted

## 时间（很紧）

首次评分最晚开始时间：B1 **20:05:44 UTC**，B3 **20:07:47 UTC**。oracle 上限 3,600 s，所以必须尽快运行。用 data_pipeline 解释器跑 oracle，用 math_verify_env 跑评分（原 P1 版本）。如果这一次又失败（包括超时），B 学生结果就记为未完成，不再补跑。
