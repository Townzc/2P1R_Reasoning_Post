# 异步代码审查：关闭 app 后的收集 / 审计 / 评分路径（`scripts/p011_long_owner_closed_io.py`）

- **审计方**：Claude。以本报告的 git 提交时间为准；在 61b41a8b 上核对
- **结论**：没有发现影响科学的问题，不叫停

与已审的 `p011_long_d_pair_io.py`（同一套 collect / audit / score 逻辑）相比：
- 输出目录改为 `long_owner_closeout_r1`；去掉了 upload 模式（上传已经完成）✓
- 评分时间上限改为 `min(7200, 原绝对截止时间 − 5 s)`。原绝对截止时间 = min(05:00 UTC, worker 开始 + worker 上限 + closeout)。这里只是不让评分超过原窗口，没有延长窗口 ✓
- `prior_stage` 只允许基线（baseline）的 collect 在一种情况下基础设施重跑一次：原 collect 报"call 节点缺少容器身份"，并且目录里只有 ATTEMPT 和 FAILED。其他情况一律拒绝 ✓
- 运行前核对脚本本身已发布 ✓
- oracle、解码和评分调用的都是原函数，没有改动。已撤回的 `p011_long_owner_call_io.py` 不能再使用（Codex 已记录）。
