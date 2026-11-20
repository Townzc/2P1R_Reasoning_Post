# T72 去回退对照：A3（实际结果）

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求 / scope**：`p011-T72-fallback-clean-controls-results-actual-A3-r1` / `p011-T72-fallback-clean-controls-results-actual-A3`
- **target_commit**：`469cbaa0acc839eae3714b5174320354d0d0e5eb`；MANIFEST `4e20e9da…`；ACTUAL_RESULT_BINDING `b3d76d58…`；归档 part000 `50b25e33…`（我自己解开读取）

## 结论：PASS-WITH-NOTES

| flag | 值 |
|---|---|
| complete_two_original_controls_and_unchanged_dose_accepted | **true** |
| independent_token_decode_and_correctness_check_scope_disclosed | **true** |
| all_eight_new_paired_contrasts_and_old_label_reuse_accepted | **true**（点估计已核对；区间未重算，见下文） |
| coverage_exposure_posthoc_and_single_training_seed_limits_disclosed | **true** |
| private_binary_state_and_frozen_scorer_access_limits_disclosed | **true** |

## 独立检查（脚本 `fallback_a3/student_a3_generic.py`）

- **解码（2 × 2,500 条）**：从原始 token 独立做 BPE 解码，与 DECODED 和 SCORING_ROWS **0 处不符**。停止原因：clean400 为 native_eos 2,176、length_cap 324；clean3200 为 2,197 / 303。
- **评分**：
  - 我自己的提取与保存的 `extracted_answer` 0 处不同；字符串相等的全部判对；非 native 停止的全部判错。
  - 只靠符号比较判对的对子中，新出现 5 个，都人工看过。其中 4 个是合理的等价，**1 个是已知的冻结评分器误判**：`0.00006712` 被判为等于 `.0000672`，只影响 clean400 `sample0::math500/176` 这一行。
- **计数**：greedy 252/500（50.4%）和 268/500（53.6%）；采样 1,009/2,000 和 1,041/2,000 ✓。clean 的向量与我按行重建的结果完全一致。
- **对比的点估计**：用保存的准确率核对（例如 0.504 − 0.486 = +1.8；0.504 − 0.546 = −4.2），全部一致。旧的 P010 T72/T1.5 向量不在这个归档里，所以 **bootstrap 区间没有独立重算**，沿用保存值。

## 结果（描述性）

| 对比 | greedy Δ pp [95% CI] | 采样 Δ pp [95% CI] |
|---|---|---|
| clean400 − 原 T72 n400 | +1.8 [−2.0, 5.6] | +0.9 [−1.3, 3.1] |
| clean400 − T1.5 n400 | −4.2 [−8.4, 0.0] | −1.7 [−4.2, 0.8] |
| clean3200 − 原 T72 n3200 | +0.6 [−2.6, 3.8] | +0.2 [−1.75, 2.2] |
| clean3200 − T1.5 n3200 | −1.6 [−5.2, 2.0] | −3.25（区间见 RESULTS.json） |

去掉回退答案后，T72 在两种题量下都**没有明显改善**，与 T1.5 的差距只缩小了一小部分（400 题：−6.0 → −4.2 pp）。**C1 中"回退答案贡献了大部分 NLL"这一观察，不足以解释强教师的劣势**。这是一个重要的阴性结果，论文草稿 §4 需要相应改写。

局限：只有一个训练种子；去掉回退答案同时改变了覆盖率和重复暴露；这是事后对照，不是预注册的检验。
