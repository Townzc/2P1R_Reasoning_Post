# S-F15 预检本地审计：批准一次本地重跑

- **审计方**：Claude，委托授权（负责人在对话中授权今晚的 P011 审批）。11:40 UTC 前后完成，以 git 提交时间为准
- **对象**：`reports/p011_20261020/long_F15_local_audit_preentry_failure_v1`（位于 ccb5dfc8）
- **job**：`preflight_S-F15_s17_r1`

## 结论：批准一次本地审计调用

- 失败在入口检查 `published()`（"Execution HEAD not published"）就已抛出。当时还没有创建审计目录，也没有写入 ATTEMPT 文件，状态没有加载，oracle 也没有运行，属于操作顺序错误。STATUS 中 `audit_attempt_fence_absent = true`、`model_reloads = 0`。
- 脚本 `scripts/p011_long_preflight_failed_ledger_io.py` 的 sha 为 `95e1c248…`，与已接受的 37 源码 SPEC 一致，未改动。
- **批准**：在已发布的 HEAD 上，对已收集的原始归档（collection CLI 4584）调用一次未改动的本地审计。必须在原截止时间 **2026-10-21T12:50:18.903812Z** 之前完成，不开新的时间窗口。
- **禁止**：重跑 collector、模型、生成、编码或评分；修改源码；自动重试。如果这一次调用失败（例如 oracle FAIL 或超时），F15 预检的状态证明记为缺失或失败，不再补跑。正式 A 的数值审查会把这一点当作 F15 证据不完整来处理。
