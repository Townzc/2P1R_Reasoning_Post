# Claude 审计第四轮：token v2 附加材料 + 两个时间计价先导学生 @ `7bfdeb3e`

范围：`cace6b49`（审计处理、`token_tariff_v2`、复现脚本、常量修改）、`9750eb1e`/`05be5032`（`operational_pair_v1`）、`7bfdeb3e`（启动记录）。

## 结论

| 对象 | 结论 |
| --- | --- |
| token v2：8 个训练计划的公开复现、曝光统计、K1 修改 | **PASS**（附 R1） |
| T1/T2/T3/K1 的处理记录 | **接受**。T3 按 owner 选定的估计对象（固定 524,287 target，包含由此带来的重复）记录为局限，措辞准确。 |
| 两个时间计价先导学生 `operational_pair_v1` | **PASS**（附 L1） |
| 新 token 学生的启动记录 | 输入 manifest `85efe502…` 与 v2 绑定一致；尚无结果 |

## 实际重算的内容

**token v2**
- `scripts/reproduce_token_schedules.py` 在公开 packet 上运行：8 个计划的摘要全部一致，选定的 target 为 524,287。
- 独立检查可行性（不用 Codex 的代码）：524,288 只在 depth_p4 不可行（8 次完整遍历之后余数 208，用该格的答案长度凑不出来）；524,287 在四格都可行。
- 每行曝光：breadth_p0 4.46、depth_p0 3.97、breadth_p4 20.75、depth_p4 8.00，与 disposition 中的表一致。
- `training_lengths.json` 与已审计的教师 token 数对照：1,203 行中有 8 行的学生端 `n_supervised` 比"教师文本 token + EOS"少 1。原因是解码后再用学生 tokenizer 编码，分词并不总是可逆。学生实际训练的就是重新编码后的文本，所以不是错误。

**先导学生**
- manifest 6 个文件 SHA 匹配；1,319 道 GSM8K test 题无重复。breadth 953（72.25%）、depth 969（73.46%）；只有 depth 答对 116 题，只有 breadth 答对 100 题。depth − breadth = +1.21pp，配对 bootstrap 区间 [−0.91, 3.41]（seed 20261013，10,000 次），解析标准误 1.11pp。
- 用纯 Python 独立解码保留的原始 token ID，再用不同的解析器对照 GSM8K test 金标准重新评分：2,638 条中只有 3 条判定不同（breadth 的 01181，depth 的 00013、00455）。这 3 条都在 512 token 处截断、没有 EOS；冻结规则把截断判为错，我的解析器没有这条规则。按截断规则，两边完全一致。

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| R1 | 低（可复现性） | `reproduce_token_schedules.py` 通过 `scripts.plan_real_math_scale` 间接导入了 `pyarrow`（来自 `prepare_real_math_audit.py`），实际并不需要。没有 pyarrow 的环境里无法直接运行；我用一个空模块替身才跑通。 | 把 `whole_response_schedule` 移到不依赖 pyarrow 的模块，或者改为延迟导入。 |
| L1 | 信息 | 评测上限 512 token：breadth 有 38 条（2.9%）、depth 有 33 条（2.5%）被截断。训练答案超过 512 token 的只有每格 1–5 条，所以截断主要是学生输出过长，而不是训练数据本身过长。 | 在 8 个 token 学生的结果表中逐格报告截断数，因为截断按答错计入。 |

## 未检查

8 个新学生（运行中）；两个先导的训练过程逐步核对（依赖 Codex 的本地审计）；恢复运行的代码。
