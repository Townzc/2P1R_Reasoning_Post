# Claude 审计第八轮：第七轮处理记录 + seed23 训练阶段记录 @ `5852ffef`

- 范围：`90ba8859..5852ffef` 的三个 commit。包括 `reports/p007_audit/token_seed17_review_followup_v1/`（manifest 标为 `external_review_of_new_followup: pending`）、`docs/audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md` 的 Round 7 一节、`P007B_TOKEN_SECOND_SEED_{STARTED,TRAINED}.json`、`P007B_TOKEN_SEED17_REVIEWED.json`，以及 RUN_LOG/WORKBOARD 的新增行。
- 不在范围内：seed23 的评测结果（截至此 commit 仍在评测，464/496 条终点输出，尚无最终分数）。

## 结论

| 对象 | 结论 |
| --- | --- |
| 第七轮处理（S7-1、S7-2、S7-3、E2） | **接受**。四条的转述与我的报告一致，没有夸大，也没有缩小范围。 |
| follow-up packet | **PASS**。4 个文件的 SHA-256 与 manifest 一致；`paired_question_scores.json` 的哈希为 `3d6dd8bd…`，与 INDEPENDENT_FOLLOWUP 中的记录一致；运行 `recompute_contrasts.py` 后，5 个对比与区间逐位一致（例如交互项 +2.88097 [−0.22745, 5.98939]）。所引用的我的报告哈希 `8897bb47…` 与 `67901abf` 中的文件一致。 |
| seed23 零题价两格的训练阶段记录 | **PASS（只覆盖记录本身）**。源码为 `90ba8859`；两个 config 的哈希与 `P007B_TOKEN_STUDENT_ADMISSION.json` 中预先登记的 `*_p0_s23` 一致。 |
| seed23 的数据 | 四格都确认：seed23 与 seed17 使用**同一组训练路径**（路径集合相同，分别为 408/474/91/230 条），只在每条路径的曝光次数上有 ±1 的差别。总呈现次数为 1818→1825、1882→1880、1888→1888、1841→1841。 |

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| S8-1 | 中（解读） | 上面的对比说明，seed23 只改变训练随机性（数据顺序和每条路径的曝光次数），**不改变教师轨迹**，每格的可用答案仍是同一批。因此两个 seed 的差异只估计训练方差，不估计"再采购一次"的方差。在 breadth_p4 这类只有 91 条答案的格子里，后者可能更大。 | 中期汇报时，把"2 seeds"写成"2 training seeds, 1 teacher trace per cell"；"跨 seed 一致"只能说明结果对训练随机性稳健，不能说明对采购随机性稳健。packet 中已有"single trace"的局限，这里只是提醒：seed23 出来后不要把它写成更强的结论。 |
| S8-2 | 信息 | 我核对了曝光数：1818/408 = 4.456，1882/474 = 3.970，1888/91 = 20.747，1841/230 = 8.004，与 follow-up 中的 `mean_answer_exposure` 一致（这些是 seed17 的值；seed23 的 breadth_p0 为 1825/408 = 4.473，depth_p0 为 1880/474 = 3.966）。 | 无需改动。 |

## seed23 结果出来后我会做的事

与第七轮相同：从用户电脑上的原始 token 独立重新评分（512 截断按答错，E2 单独统计），复算 8 个模型的主对比，并检查跨 seed 的方向一致性。
