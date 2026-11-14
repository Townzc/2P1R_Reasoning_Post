# A7 首次完整分析：独立数值复核包

分析适配器已通过8a8fac5c首次使用审查；本次绑定全部15个端点，bootstrap核心保持169754c4版本。原始统计输出、完整输入清单、来源哈希及运行记录均保留。全部为探索性LoRA/Tinker，不进入H0–H3。

**解读以9B组为主。** 4B的M512 long.jsonl中40/512行只有boxed答案、没有推理；9B没有。4B这些行在concise中反而增加了推理，因此4B是带此限制的重复。冻结数据、标签及原预测均未改动。

| 模型 | 种子 | OMI短解 | 同源concise | 长解 | concise正常输出平均token |
|---|---:|---:|---:|---:|---:|
| 9b | 17 | 72.20% | 80.62% | 91.14% | 367.59 |
| 9b | 29 | 70.76% | 81.26% | 91.22% | 400.49 |
| 4b | 17 | 65.40% | 71.26% | 87.56% | 341.83 |
| 4b | 29 | 63.42% | 70.22% | 87.34% | 331.59 |
| 9b_base | 17 | 70.14% | 76.44% | 87.66% | 355.71 |

| 模型 | 对比 | 两种子均值pp（Base为单种子） | 95%区间 | 两种子同号 |
|---|---|---:|---|---|
| 9b | long_minus_short | +19.70 | [+18.66, +20.75] | True |
| 9b | long_minus_concise | +10.24 | [+9.42, +11.06] | True |
| 9b | concise_minus_short | +9.46 | [+8.45, +10.48] | True |
| 4b | long_minus_short | +23.04 | [+21.92, +24.14] | True |
| 4b | long_minus_concise | +16.71 | [+15.71, +17.71] | True |
| 4b | concise_minus_short | +6.33 | [+5.29, +7.35] | True |
| 9b_base | long_minus_short | +17.52 | [+16.32, +18.72] | 单种子 |
| 9b_base | long_minus_concise | +11.22 | [+10.10, +12.36] | 单种子 |
| 9b_base | concise_minus_short | +6.30 | [+5.04, +7.58] | 单种子 |

区间按题联合重采样，条件于这两个已观察训练种子；不估计训练种子的总体方差。每个种子的点估计、区间、截断率、循环数与正常终止分母都在RESULTS.json。

## 请Claude复核

1. 按8a8fac5c§4复核首次完整真实输出和INPUT_MANIFEST.json的15个训练/数据/权重/输出绑定，独立重算三组配对差、两种子均值、95%区间和同号标记。
2. NEW_ENDPOINTS_FOR_REVIEW.json列出此前未审的6个新A7端点、30,000条输出；逐批独立评分。已通过8a8fac5c及更早的端点不重复。
3. 按22890560判断SC-1至SC-4及S2-1/S2-2，保留4B数据限制和以9B为主的解读。两套concise数据已经全量审过。
4. 4B concise seed17 greedy使用一次基础设施重试；其4510条未完成原输出独立保存在infrastructure_interruption_8a_v1，从未混入本次评分。新完整5000输出使用同一已完成训练权重和同一协议。失败费用仍计入A7。

[输入清单](INPUT_MANIFEST.json) · [来源定位](SOURCE_LOCATIONS.json) · [原始统计输出](RESULTS_NUMERIC.json) · [带数据说明的结果](RESULTS.json) · [运行记录](RUN_RECEIPT.json)
