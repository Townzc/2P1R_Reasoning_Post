# C1 r2 实际结果 A3

- **审计方**：Claude，2026-10-21 09:00 UTC（负责人夜间全权审核期间）
- **请求**：`p011-C1-r2-complete-original-token-NLL-actual-A3-r1`
- **scope**：`p011-C1-r2-complete-original-token-NLL-actual-A3`
- **target_commit**：`bf0ca6de753a1788db31887f9523f4a29ac1bc27`
- **packet**：`c1_r2_complete_results_v1`，MANIFEST `ab609ac3…`，DESCRIPTIVE_SUMMARY `0a5cc7d5…`
- 脚本 `a3_c1.py`、结果 `A3_C1_RESULT.json` 随本目录提交

## 结论：PASS

**核对范围**：把两段 archive 按顺序拼接，得到的 sha 为 `b508f798…`（50,589,568 bytes），与 ARCHIVE 中记录的一致。我完整解压后做了以下独立核对。

| 核对项 | 结果 |
|---|---|
| COMPACT_MEMBERS 列出的 19,316 个成员，逐个比对 sha | 0 个不一致 ✓ |
| **用原始 18 个输入文件（我在 20261021f 中 A1 过的副本）独立重建任务**：digest(input_ids, labels)、prompt 长度；6 组共 10,800 条成员关系（path_id、sequence_sha、兜底标志）与 MEMBERSHIPS.json 逐条相同 | 6/6 ✓ |
| INTENT.task_ids 等于排序后的全部 9,594 条序列；chunk_size 为 320；共 30 个 chunk（29 个 320 + 1 个 314）；每个 chunk 的 ack 顺序与 intent 一致 | ✓ |
| 9,594 个 RESULT 的文件 sha 与 ack 一致；每个向量长度都等于原监督 token 数，target_positions 等于 range(prompt, n)；全部为有限非负值；nll_sum 和 mean 与 fsum 一致 | 0 违规 ✓ |
| **用逐 token 向量独立重算描述性汇总**（6 组 × all/nonfallback/fallback）：answers、监督 token 数、token 加权 NLL、7 个回答均值分位数，与原 worker 的 DESCRIPTIVE_SUMMARY **全部一致**（误差 < 1e-12）；没有兜底的子集为 null，answers 为 0 | 0 差异 ✓ |
| 模型：Qwen2.5-1.5B，revision `8faed761…`，9 个文件的 sha 与 P010 相同；BF16 + sdpa，FP32 损失；没有优化器、没有 adapter、没有新的 tokenization；H100 80GB | ✓ |
| 计时：加载在 worker 开始后 25.3 s 完成；30 个完整轮次在 15.0–25.4 s 之间，合计 498.6 s；ALL_CONFIRMED 记录的 elapsed 为 526.1 s，在 1,500 s 之内 | ✓ |

## 描述性结果（只陈述数字，不做解读）

token 加权 NLL（nats/token）；括号内为回答数 / 监督 token 数。

| 组 | all | nonfallback | fallback |
|---|---|---|---|
| T1.5 n3200 | 0.1350 (3200 / 1,494,755) | 同 all | 无 |
| T7 n3200 | 0.1853 (3200 / 1,566,436) | 0.1350 (3118 / 1,494,922) | 1.2371 (82 / 71,514) |
| T72 n3200 | 0.2441 (3200 / 1,529,639) | 0.1502 (3117 / 1,457,023) | 2.1265 (83 / 72,616) |
| T1.5 n400 | 0.1372 (400) | 同 all | 无 |
| T7 n400 | 0.1370 (400) | 0.1359 (388) | 0.1557 (12) |
| T72 n400 | 0.2151 (400) | 0.1533 (387) | 1.1876 (13) |

**解读时需要注意的限制**（请负责人自行判断，并自己撰写报告文字）：

- 这三组题都是"T1.5 attempt01 答对"的 S1 题；T7/T72 混有重试和未验证兜底，兜底子集的 NLL 远高于其余回答，"all"列主要受兜底拉高。
- BF16 logits 下单 token 的分辨率约为 0.01。
- 结果只是描述性的：没有做统计检验，不代表总体，也不能作为因果证据。

## 限制与成本

- 私有的完整 dispatch、账本和余额记录，我只核对了 sha 的绑定关系，**没有**读取原始字节。
- **成本对账**：目前没有新的账单数据，只能估算。按完整费率计，启动 600 s + 运行约 526 s，约 $1.4 上限，实际 GPU 占用约 9–10 分钟；r2 预留 $2.64，r1 预留 $3.74，都只是保留，不代表支出。实际费用要等延迟到账的账单数据来对账。
