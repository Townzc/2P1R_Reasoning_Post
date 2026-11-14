# 新增结果、A7 concise 与分析适配：审查通过

本包冻结 6 个新端点、30,000 条完整 MATH greedy 输出；同时提交两套 concise 数据的全部 1,024 行与 1,026 次生成尝试。既有 6af18b72 及更早已审端点仅作对照，不重复请求数值审查。全部为探索性 LoRA / Tinker，不进入 H0–H3。

| 模型 / 臂 / 种子 | MATH 5,000 | MATH-500 | 截断率 | 循环数 | 正常终止正确数 / 分母 |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-4B / P / 29 | 60.94% | 60.60% | 5.80% | 177 | 3047/4710 |
| Qwen3.5-4B / R / 29 | 46.80% | 45.60% | 3.04% | 73 | 2340/4848 |
| Qwen3.5-4B / K8 / 29 | 59.18% | 60.40% | 6.62% | 219 | 2959/4669 |
| Qwen3.5-4B / short / 29 | 63.42% | 63.80% | 6.56% | 208 | 3171/4672 |
| Qwen3.5-9B / long / 29 | 91.22% | 91.00% | 6.34% | 6 | 4556/4683 |
| Qwen3.5-9B / short / 29 | 70.76% | 71.00% | 4.08% | 117 | 3538/4796 |

## 已通过的复核范围

1. 按 P012 §12 对本包新端点独立评分，复核完整 MATH / MATH-500 正确数、截断、循环及正常终止分母。ENDPOINTS.json 绑定原始档案、标签和训练证据。
2. 按修订 7 的事后全量审查，对两套 concise 的 1,024 行和全部 1,026 次尝试核对原模板、字面替换、N 四舍五入、seed=7000+行号×4+次数、首个合格选择、最后 boxed 判分、终止与特殊符号。每套均 513 次尝试、0 回退。全部提示词 token、原输出、逐次合格记录、预测 UTC/哈希、选取清单都在 construction_evidence.zip。没有逐题长度门槛。
3. 核对 pre-training 数据报告 465bf2c1 与报告送达记录：数据哈希、0 回退和三学生 token 统计先报告，三个 concise seed17 臂随后才在 fd78a182 准入。9B/Base 的 concise/OMI=0.9432、concise/long=0.3724；4B 分别为0.8346、0.3696。
4. 首次使用前审查 [A7 分析适配器](../a7_analysis_candidate_v1/README.md)：12 项合成检查通过，bootstrap 核心哈希保持169754c4版本。新增部分绑定 Tinker 训练证据与固定15个端点；真实统计分析尚未执行。两个种子按题联合重采样，Base只做一个种子。ANALYSIS_INPUTS_PREPARED.json 明确区分已完成与待完成输入，真实运行前再冻结完整清单。
5. 对照22890560的 SC-1至SC-4、S2-1和S2-2。当前包中的不完整模型组合不用于抢先判断未完成的预测。所有新 A7 端点评分前记录含 UTC；原 T 轨 P/R/K8 沿用先前已经冻结并运行中的队列，原记录不补改。

## 证据入口

- [端点与哈希](ENDPOINTS.json)、[本地核验](VALIDATION.json)、[来源定位](SOURCE_LOCATIONS.json)、[预算快照](BUDGET_SNAPSHOT.json)。
- [两套 concise 数据报告](../a7_1_concise_data_v1/README.md)，包括每套 construction_evidence.zip；新构造源代码为 experiments/p012/a7_concise_data.py。
- 构造原 REQUEST.code_commit 保留准备基线67c155e5；实际新构造代码与模板在213ee3e5发布，早于两次启动，源哈希与请求一致。这一来源说明不改动原请求。
- [当前队列](BACKGROUND_STATUS.json)。已授权 A7 和 A6-3 继续；数据事后复核和结果复核不阻塞训练。新统计适配器已通过8a8fac5c首次使用审查；15个端点齐后运行并送首次数值输出复核。

审查依据：P012 §12 要求每批抽10%原输出独立重评，以及每条新分析路径首次运行前审查一次；修订7明确豁免改写构造的预审并要求事后全量复核。既有主网格统计和已审数据保持不变。

审查8a8fac5c接受全部6端点、两套concise全量复核和分析适配器。

4B M512 long.jsonl contains40 of512 rows with only a boxed answer and no reasoning;9B contains none. Interpret SC-1/SC-2 primarily using9B;4B is a repetition with this limitation. Frozen data,labels and predictions remain unchanged.
