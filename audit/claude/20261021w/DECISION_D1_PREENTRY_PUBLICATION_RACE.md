# D1 派发前的发布竞争失败：委托例外

- **决定方**：Claude，委托授权。以本记录的 git 提交时间为准
- **请求 / scope**：`p011-D-first-preentry-publication-failure-exception-r1` / `p011-D-first-preentry-publication-failure-exception`
- **target_commit**：`a3a5da834f7ec726e14370b6c5958cb5537d5558`；MANIFEST `c0f5ec6e…`；FAILURE_BINDING `d38a4c94b4b23738f7944d4a524a657f7e5031a2c5274de8fd9425c274b9a2d7`（已重算）
- **原路径**：exact62 target `68701107…`；SPEC `438a120f…`；审查报告 `26d7fe97…`

## 结论：批准一次额外的 D1 进入

**完整性**：
- CLI 16928 在 `published()` 处报 "Execution HEAD not published"（traceback 第 194 行，在 `exact_source` 之前）后退出。
- 当时还没有读取审查和预算，没有 dispatch 目录、intent 或预留，也没有调用 `worker.spawn`；app 已确认 STOPPED0。
- 两个上传（75810 / 1974）已完成。原因是 Codex 在镜像构建期间推送了 B 的元数据。这是操作顺序问题，与源码和科学无关。

**处置**（5 个 flag 全部 true）：
- `one_additional_D1_preentry_invocation_explicitly_authorized`
- `original_failure_no_model_dispatch_and_zero_reservation_accepted`
- `unchanged_exact62_SPEC_and_prior17flag_review_accepted`
- `both_completed_uploads_reused_without_repeat_and_D2_first_entry_accepted`
- `publication_fixed_until_submission_fresh_gates_pair_window_accepted`

**条件**：
- 先完成发布并核对，再进入 D1。从 D1 进入开始，直到 SUBMITTED（或终止回执）为止，HEAD 都不能变，期间不推送任何东西；D2 同样如此。
- 进入时要做新鲜的费率、D1、两格的预测 80% 和硬上限、槽位、fence 和窗口检查，最晚 22:40:35 UTC。
- 两格都做或都不做；上传不得重复。
- 如果再失败，保留现场，不再补跑，D 记为未完成。
