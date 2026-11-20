# C1 失败调用与保全：实际复核

- **审计方**：Claude，2026-10-21 06:25 UTC 前后
- **请求 / scope**：`p011-C1-failed-self-calibration-and-preservation-actual-review-r1` / `p011-C1-failed-self-calibration-and-preservation-actual-review`
- **target_commit**：`4413e768e803a9c3e81a5899151ecfde981c77a9`
- **packet MANIFEST**：`1cac807d969e80fa7352b1a9c7388df7b2a5c8a0ae5603b07dbf45a23341aaad`
- **公开投影 tar**：`2df9d5ce…`，共 679 个成员
- **调用身份**：app `ap-EWqcTiOBy7VwDucYhICXgC`，call `fc-01M5EFCS20593539BQ02GTGC1Q`，execution `38d337cd…`；SPEC 为 `416f80bb…`，对应 13 个 source 文件

## 结论：PASS（失败如实保全）

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| original_failed_call_integrity_accepted | true |
| partial_preservation_accepted | true |
| no_scientific_retry | true |
| no_complete_C1_result_claim | true |
| retained_reservation_accepted | true（$3.74 保留，不视为支出） |
| public_projection_limits_disclosed | true |
| C1_completed | **false** |
| automatic_continuation_allowed | **false** |

## 独立核对

- **归档完整性**：解压后的 679 个成员，bytes 和 sha 全部与 ARCHIVE_MEMBERS 一致。其中 677 个与原文件逐字节相同；只有 2 个是投影版本：`remote/ADMISSION.json`，以及 dispatch 对应的 named record。这两个去掉了 budget、provider 和 prior records 三个对象，原 sha 已另行绑定。
- **named records**：共 603 个 key，其中 5 个存在（dispatch、claim、terminal、chunk/00000、chunk_done/00000），598 个不存在，与"只完成了 1 个 chunk"一致。
- **失败路径**：traceback 显示，失败发生在 `run_body` 第一个 chunk 完成后的 `POST_FORECAST`，原因是 `forecast` 的 ValueError（"C1 full-time or original80% C budget forecast exceeded"）。payload 里有 FAILED.json，外层有 FAILURE.json 和 terminal。**没有开始第 2 个 chunk，也没有重试** ✓
- **计时**：
  - 加载在 worker 开始后 27.2 s 完成，满足 900 s 的限制 ✓
  - chunk 0 的完整轮次为 **6.574 s**，其中 body ack 3.296 s。32 条序列的纯前向时间只有 **1.282 s 合计**，约 0.04 s/条。
  - 完整轮次中的其余约 5.3 s，是逐条文件写入、store 读写和 3 次 volume commit 的开销。
- **下界核算**：即使把已用时间设为 0，1.2 × (299 × 6.574 + 300) = 2,718.7 s，仍然大于 2,400 − 30 = 2,370 s；按冻结费率换算为 $4.06，大于 reserve $3.74。数值我已重算，一致 ✓
- **部分结果**：第一个 chunk 的 32 条结果正好是排序后的前 32 个 task_id，全部是有限值。它们**只保存，不做任何解读或汇总**。
- **provider**：STOPPED，0 个容器在运行，观测时间晚于终止时间 ✓

## 原因与教训（我方责任）

自校准机制按设计正常工作：只跑了一个 chunk 就止损，实际花费估计约 $0.5 以内。失败的根本原因有两个：

- 我起草的负责人例外中，worker 上限为 2,400 s，再叠加 1.2 倍系数和 300 s 的预留，**留给 300 个 chunk 的空间太小**；
- 每 32 条序列就做 3 次 commit，**开销是前向计算的 4 倍**。

实测下，C1 的全部前向计算只需约 6.4 分钟。按 32 条一组写日志才是瓶颈。

## 后续（需要负责人决定，本报告不授权）

C1 属于计划中"不可砍"的项目。如果要重做，需要负责人批准**新的一次逻辑尝试**（r2）。我的建议：

- **代码**：只把日志 chunk 从 32 改为 320（共 30 个 chunk）。前向仍然是 batch=1，token、掩码和汇总定义都不变。改动需要做简短 CR。
- **参数与费用**：
  - worker ≤ 1,500 s，reserve 约为 ⌈0.0012209 × (600 + 1,560)⌉ = **$2.64**；
  - 实测推算一个 chunk 约 18 s，1.2 × (29 × 18 + 300 + 加载) ≈ 1,030 s，可以放进 1,470 s；
  - 预计实际花费约 $1。
- **C 类预算**：C 类已保留 3.74，加上 r2 合计约 6.38 ≤ 12。剩下约 5.6，再按 80% 规则，留给 C2 大约 4.5。
