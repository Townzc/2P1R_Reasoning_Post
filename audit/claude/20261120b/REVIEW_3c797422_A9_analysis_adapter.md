# 审查：A9 分析适配器（`3c797422`）

- 日期：2026-11-20（PST）
- 对象：`reports/p012_20261111/amendment9_analysis_review_v1/` 的 `a9_analysis.py`、`CATALOG.json`、`INPUT_TEMPLATE.json`、`test_a9_analysis.py`、`CHECKS.json`
- 依据：修订 9（`ecda0914`）
- 结论：**接受，附两条必须修改（R-1、R-2）**。改完即可运行，不需要再送一次预审；差异随结果包一起送来，我在数值复核时核对。

## 1. 我核对了什么

| 项 | 结果 |
|---|---|
| `analysis/p012_registered.py` 的 sha256 | `b6973ad6…`，与已接受的版本一致；适配器只导入 `bound_file`、`bootstrap_delta`、`differences`、`outcomes`、`two_seed_contrast`、`POLICY`，没有改动 |
| `CATALOG.json` 的 sha256 | `623bb258…`，与源码里的常量一致 |
| 目录条目 | 44 条 = R 部分 6 格 × 2 个种子 + M 部分 4 个设定 × 4 个臂 × 2 个种子 |
| 目录内部一致性 | 每条 `updates = P·K·E / 8`；题数 GSM8K 1,319、MATH 5,000；键里的种子与条目一致 |
| 数据文件 | 同一任务、同一 (P, K) 在所有设定下是同一个哈希；Qwen base 的 (2048, 2, 2) 与其余三个设定相同，符合修订 9 第 2 节；(4096, 1, 1) 与 P 格用同一份数据 |
| 模型版本 | 每个模型只出现一个 revision |
| seed 17 的参照 | R 部分指向修订 8 的 `a8_*` 运行，M 部分的 P、K8、K4 指向主网格运行，PK2 指向修订 8 的 (2048, 2, 2)；Qwen base 的 PK2 两个种子都是新跑的 |
| Tinker 配方常量 | 学习率与此前 4B 的请求文件一致；`source_sha256` 等于当前 `experiments/p012/tinker_lora.py` |
| 14 个合成测试 | 我本地重跑，全部通过 |

## 2. 判定逻辑与修订 9 的对照

| 修订 9 | 适配器 | 一致 |
|---|---|---|
| 残差 = 实测 − 修订 8 预测，预测取 `A9_PREDICTIONS.json` 的值 | `replication()` | 是 |
| 同号：与 seed 17 残差同号 | `b * seed17_residual > 0` | 是 |
| 带外：严格大于判定带 | `abs(b) > band_pp` | 是 |
| 报告平均残差、seed 29 − seed 17 的逐题配对差与区间 | `mean_residual_pp`、`bootstrap_delta(differences(high, low))` | 是 |
| 四个单轮格全部同号；至少三个重复出现 | `single_epoch_*` | 是 |
| R05、R06 都同号且平均残差 ≥ +3 | `interaction_failure_trigger` | 是 |
| M-1：四个设定的 PK2 − P 都不明显 | `two_seed_contrast(PK2, P)` 的 `noticeable` | 是 |
| M-2：K4 − P 的两种子均值在 [−4.5, +0.5] | 闭区间 | 是 |
| M-3：Qwen base 的 PK2 两个种子各自在 [67.2, 72.2] | 闭区间 | 是 |
| M-4：至少三个设定满足 PK2 > K4 > K8 | 两种子均值 | 是 |

## 3. 必须修改

### R-1 允许分批运行

现在 `analyze()` 要求 44 个端点全部到齐才计算任何统计量。修订 9 第 3 节允许「一格不准入就跳到下一格」，所以可能有格子永远不跑；即使都跑，R 部分的结论也要等到 M09 结束。两种情况都不可接受。

改法：

- 把目录分成分析单元：每个 R 编号是一个单元（2 个端点），每个 M 设定是一个单元（8 个端点）。
- 清单里列出本次要分析的单元；`endpoints` 的键必须恰好等于这些单元在目录里的键，多一个少一个都拒绝。单元内部不允许缺端点。
- 每个单元只在一次正式运行里出现；输出文件仍用独占方式写入。
- 汇总判定只在所需单元齐全时计算，否则输出 `null` 并列出缺少的单元：
  - `single_epoch_all_same_sign`、`single_epoch_at_least3_misses_repeat` 需要 R01–R04；
  - `interaction_failure_trigger` 需要 R05、R06；
  - M-1、M-2、M-4 需要四个设定；M-3 只需要 Qwen base。
- 所有身份校验照旧，不放宽。

### R-2 预测文件的哈希写成常量

`manifest['prediction_sha256'] == sha(PRED_PATH)` 的两边都由运行方提供，没有绑定到修订 9。请像 `CATALOG_SHA` 一样写死：

```
PRED_SHA = 'fa3d186069b672c683f6300c174597124af8f970201aacf8bf050b9e57cac3b2'
```

这是 `ecda0914` 里 `audit/claude/20261120a/A9_PREDICTIONS.json` 的 sha256。

## 4. 说明（不阻塞）

- **N-1** 请在 M 部分顺带输出 `K8_minus_P` 的 `two_seed_contrast`。它不参与 M-1 到 M-4，但「固定 4,096 个不同样本」那张表需要这一行。不加也可以，我会自己算。
- **N-2** 预测取两位小数的权威值，这与修订 9 一致。我枚举了全部可能的正确题数：只有 R04 在 3,222 题（64.44%）和 3,347 题（66.94%）这两个取值上，取整与否会改变判定。如果 R04 恰好落在其中之一，请两种读法都报告。其余五格不存在这种取值。
- **N-3** R04 的 seed 17 有 9.2% 的输出撞到长度上限。结果包里请照旧给出 seed 29 的终止统计。
- **N-4** M-1 是「不明显」，不是等价性检验；适配器的 `M1_limitation` 字段已经写明，保留。

## 5. 接受后的步骤

1. 实现 R-1、R-2，补对应的合成测试（缺单元、单元内缺端点、重复单元、预测文件被改）。
2. 把 `ACCEPTED_REVIEW` 填为本审查的提交哈希，冻结输入哈希。
3. 已到齐的单元可以立即运行；每次运行把完整数值输出、输入清单和源码差异送来，我独立重算。
