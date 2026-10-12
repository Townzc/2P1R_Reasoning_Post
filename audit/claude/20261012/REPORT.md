# Claude 审计：P007 三个 packet（2026-10-12）

- 仓库 / 分支 / 审计的 commit：`Townzc/2P1R_Reasoning_Post` / `codex/icml-acl-2027` / `044fb6d45182fc37ab442d330ed18f3c4c07b5c9`
- 审计方式：只读。所有数字由下列独立脚本重算，没有调用 Codex 的 verify 脚本得出结论（只额外跑了一次作对照）。没有启动计算，没有改代码。
- 复现：在仓库根目录 `python3 audit/claude/20261012/main_audit.py reports/p007_audit/main_v1`，`pilot_audit.py reports/p007_audit/pilot_v1`，`p0_audit.py reports/p007_audit/policy_p0_v1`。`rescore_raw_device.py` 需要本地保留的 `.local` 原始 token 文件（owner 电脑上运行）。

| Packet | Snapshot / manifest | 结论 | 范围 |
| --- | --- | --- | --- |
| P007 main | `p007-main-20261012-v1` / `ca17892c…` | **PASS-WITH-NOTES** | 9 个准确率、2 个主要对比及区间、剂量与曝光；8 个训练 run 的逐题评分（独立解码 + 独立解析器） |
| P007A teacher pilot | `pilot_v1` | **PASS** | 紧凑 supply/cost 表的计数、删失与前缀成本一致性 |
| P007B zero-price | `policy_p0_v1` | 记账机制 **PASS**；"相同上限 = 相同获取成本"**FAIL** | 计数、退役规则、钱包链条与上限；成本度量的有效性 |

## P007 main — PASS-WITH-NOTES

**重算结果（全部一致）：** manifest 3 个文件 SHA-256 匹配；3,879 行 = 9 × 431，无重复，题目集合一致；9 个准确率完全一致；独立实现的配对 bootstrap（10,000 次，seed 20261013，两个 seed 共用同一抽样）给出 Solutions − Repeat = +10.789pp [7.19, 14.39]，Breadth − Solutions = −0.812pp [−3.71, 2.20]，与 packet 一致；每个 run 均为 256 次更新、524,288 个监督 target，Repeat 每对平均曝光 13.58 次，其他三臂 3.37–3.44 次。

**独立评分：** 用纯 Python 的 byte-level BPE 解码保留的原始 token ID，再用一个与 `marked_answer_v1` 不同的解析器（最后一个 `\boxed{}` → `####` → 行内任意位置的 "answer is"，在 `\nProblem:` 处截断）对照 GSM8K train 金标准。8 个训练 run 共 3,448 道题，逐题判定 **3,448/3,448 一致**。

| ID | 严重度 | 影响的结论 | 观察到的事实 | 建议 |
| --- | --- | --- | --- | --- |
| C-M1 | 中 | 任何"相对 base 提升"的说法 | base 在 `marked_answer_v1` 下有 93/431 题未解析，109 题停在新问题边界；部分输出续写出聊天模板式的系统提示（如 `gsm8k/train/00105`）。`ANSWER` 正则要求行首，行中的 "The answer is N." 被判为缺少答案：6 道 base 题金标准正确却记为错（00569、00921、03647、04022、04297、05339）。base 得分：冻结规则 256（59.4%）；接受行中 "the answer is" 为 262（60.8%）；段内最后一个数字（宽松上界，可能误收）为 301（69.8%）。训练臂几乎全部使用 `\boxed{}`，不受影响。 | 主要对比不受影响。base 数字要带协议说明和敏感度区间（59.4%–69.8%）；"训练后比 base 高 12–23pp"应表述为"在冻结的 marked-answer 协议下"，其中很大一部分是格式和终止行为的学习，不能当作推理能力提升。 |
| C-M2 | 信息 | Repeat 的解读 | 两个 seed 在逐题对错上的不一致数：Repeat 106/431，Solutions 61，Mixed 55，Breadth 64。 | 描述性证据，与 Repeat 在 13.6 次曝光下方差更大相符；不能作为因果解释。 |
| C-M3 | 更正 | 此前 Claude 的措辞 | 我此前写的"seed 差最多 2 题"不对（Mixed 差 3 题），"只能排除 3pp 以上的差别"也不对（下界是 −3.71）。 | 接受 Codex 在 `docs/audit/P007_REVIEW_DISPOSITION_20261012.md` 中的更正。 |
| C-M4 | 信息 | few-shot 参照 | 我此前引用的 68.5%（4-shot）来自记忆，尚未核实。 | 核实前不要使用。 |

**未检查：** 生成过程本身的可复现性（没有重新生成）；8 个被中断的中间诊断；按 run 归属的成本。

## P007A teacher pilot — PASS

**重算结果（全部一致）：** manifest SHA 匹配；128 个 parent 互不重复；1,024 次尝试、959 个可用答案；k = 1/2/4 达到/删失为 125/3、123/5、122/6，与 `results.json` 一致；`prefix_costs.json` 与 `parent_supply.json` 逐项 0 处不一致；达到 k 的 parent 平均尝试数 1.072 / 2.065 / 4.107。

| ID | 严重度 | 影响的结论 | 观察到的事实 | 建议 |
| --- | --- | --- | --- | --- |
| C-P1 | 中（设计） | 成本分配研究能否区分 | 供给几乎饱和：107/128 个 parent 8 次全部可用，只有 6 个 parent 删失。每多一个可用答案，大约多花 1.03 次尝试，边际成本几乎是常数。 | 在 GSM8K + 这个 teacher 上，breadth/depth 的成本差几乎完全由题目价格情景和实现开销决定，与难度相关的供给关系不大；按难度分层的方差也很小（且分层是内生的，Codex 已指出）。中期后建议换更难的题池（例如 MATH Level 3–5），让供给曲线真正有变化。 |

**未检查：** 原始 teacher 输出和检查器的逐条判定（packet 中没有）。

## P007B zero-price — 记账机制 PASS；成本度量 FAIL

**重算结果（一致）：** manifest SHA 匹配。breadth：544 次尝试、437 个可用、450 个 parent；depth：736 次、650 个可用、179 个 parent（171 个有可用答案）。退役规则 0 处违反；每个 parent 最多 8 次尝试；钱包单调；两格花费均不超过上限，剩余比例 2.4% 与 2.5%。

| ID | 严重度 | 影响的结论 | 观察到的事实 | 建议 |
| --- | --- | --- | --- | --- |
| C-B1 | **高（建议在 student 训练前处理）** | "两种策略在同一获取上限下比较" | 按实测时间计费时，breadth 每个输出 token 的生成时间多约 31%：2.715 vs 2.072 ms/token（439.9 s 生成 162,049 token，对比 437.0 s 生成 210,945 token）。每批平均 22.1 s vs 16.2 s，两边都是 16 个槽位，最长输出相近（481 vs 445 token）。两格的实际计费里约一半是非生成时间（active 约 872 s，生成约 440 s）。两格在不同容器上并发运行（app 创建于 12:38:04 和 12:38:49）。 | 目前的策略对比里混进了基础设施速度差异，而不只是获取策略本身。**不需要新算力的检查：** 把 depth 的记录截到 breadth 的 162,049 个输出 token，得到 560 次尝试、499 个可用、130 个 parent。可用答案的差距从 650 vs 437（1.49 倍）缩到 499 vs 437（1.14 倍）。建议（需要 owner 决定）：(a) 主成本改用确定性的 token 计价（prompt + 输出 token × P007A 标定的单价），实测时间作为敏感度分析；(b) 现有记录按等 token 截断，不重新生成，正价格格也按同样方式处理；(c) 用保留的 GPU 采样诊断速度差（SM 时钟、每步时间），查清之前不要归因；(d) 如果仍以实测时间为主成本，两种策略应在同一容器上交替运行。 |
| C-B2 | 中 | 正价格格 | breadth 在 192 个已知输出后中断，恢复过程会重建成本（没有 packet，未审计）。 | 重建的部分要单独标注；它也受 C-B1 影响（恢复时用的容器速度）。 |

**未检查：** 原始 token 重新评分；正价格的两格；student 阶段。
