# 异步代码审查：owner150 长序列路径 + T72 去回退对照

- **审计方**：Claude。以本报告的 git 提交时间为准；在 387bd4e6 上核对
- **依据**：负责人 12:40 PDT 的直接指令，改为异步审查，审查不阻挡派发

## 结论：没有发现影响科学的问题，不叫停

**长序列（`long_owner_*`）**：
- `long_owner_execution.py` 和 `long_owner_evidence.py` 与已审的 `long_lr_r2_*` 相比，只换了 forecast 的 import。训练模块仍是 `long_lr_r2_training`（冻结的 LR 加 1e-12 容差），评测和评分不变。
- `long_owner_numeric.py`：两个 raise 改成 `pass`，同时记录 `exceeds_worker_projection` 和 `exceeds_historical_80percent`。输入有限性校验保留。终止只由硬计时器负责 ✓
- SPEC：11 个 job，与原 SPEC 的 job 相比只有 `limits`、`logical_id` 和 `original_job_id` 不同；worker 上限 A 格 16,200 s、基线和 D 各 9,000 s ✓

**T72 去回退对照**：
- 只去掉保存时标记为 `unverified_fallback=true` 的行：400 题去掉 13 行，剩 387 行；3200 题去掉 83 行，剩 3,117 行。
- 原 token 行复用；1,024 次更新，2,097,148 个 target；LR 向量 sha `14ac59d2…` 与 P010 相同；seed 17 ✓
- 覆盖率的变化已披露（P_cov 分别为 387 / 3,117）。

**提醒**：基线的评测代理值沿用 L15 的 965 s，只记录、不终止，没有影响。
