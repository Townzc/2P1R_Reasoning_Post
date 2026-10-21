# B 完整 6,400 条生成与选择：A3（实际结果）

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求 / scope**：`p011-B-complete6400-generation-and-selection-actual-A3-r1` / `p011-B-complete6400-generation-and-selection-actual-A3`
- **target_commit**：`19686a28d09cff472027e4a61ba40594c512c7f6`（在 b562e7dc 上核对）
- **证据**：ACTUAL_RESULT_BINDING `55973e11…`；SELECTION `30fe8003…`；归档 part000 `584b9c09…`，我自己解开并读取

## 结论：PASS-WITH-NOTES

| flag | 值 |
|---|---|
| independent_original_token_decode_and_correctness_checks_accepted | **true**（范围见下文和注意 1） |
| all6400_outputs_and_unmapped_exclusions_accepted | **true** |
| actual_selection_and_Pcov_accepted | **true** |

## 独立检查（脚本和输出见 `b_a3_scripts/`）

1. **解码（6,400 条全量，独立实现）**：
   - 我没有使用仓库里的 transport 或 `first_stop`，而是自己写了 byte-level BPE 解码器，直接读取 `tokenizer.json`。这个文件的 sha `c0382117…` 等于教师 Qwen2.5-Math-1.5B-Instruct 固定的 tokenizer.json。
   - 按停止原因重新算出答案片段：native_eos 取第一个 EOS 之前；length_cap 取全部 token；invalid_special_token 取第一个未映射 ID 之前。与保存的 `answer_segment` 比对，**6,400 / 6,400 逐字相同，0 处不符**。
   - 停止原因分布：native_eos 6,241，length_cap 158，invalid_special_token 1；没有 new_problem_boundary。
   - 含未映射 ID 的行**只有 1 条**，即原前缀中的 `…482::attempt09`；新生成的 5,120 条里一条都没有。
2. **采样参数**：6,400 条全部是 T = 1.0、top-p 0.95、上限 1024、n = 1；seed 都等于 P010 的 `seed_for(candidate_id)`；400 题 × 16 次，没有重复。
3. **评分一致性（6,400 条全量；没有重跑 math-verify，见注意 1）**：
   - 我用自己写的花括号配对提取最后一个 `\boxed{}`：与保存的 `extracted_answer` **0 处不同**。
   - 规范化字符串等于 gold 的 5,494 条**全部判对**；字符串相等却判错的有 **0** 条。
   - 非 native 停止的 159 条全部判错，也都不可用于教师标签 ✓
   - 只靠符号比较判对的 435 条只涉及 **40 个不同的（答案, gold）对**。我**逐一人工看过这 40 对**，都是合理的等价，例如 `45.5`↔`\frac{91}{2}`、`0.52`↔`\frac{13}{25}`、`12\sqrt{3}+12`↔`AB=12+12\sqrt{3}`、`(x+2)(x+1)`↔`(x+1)(x+2)`、`4320`↔`4,\!320`、`28`↔`28_9`。反例也核对过：`12\sqrt{3}` 对 `AB=12+12\sqrt{3}` 判错，正确。
   - 合计判对 5,929 / 6,400（92.6%）；剔除未映射行的敏感性口径为 5,929 / 6,399。
4. **选择（独立重算）**：
   - 我按"可用 = native_eos、box 已提取、已解析、判对"和"只在映射行中取"重算。
   - K1：第一条可用解，没有就退回第一条映射行。K4/K8：按尝试顺序取空白规范化后不重复的可用解。
   - 结果与保存的 SELECTION **完全相同**：K1/K4/K8 分别为 400 / 1,583 / 3,125 条，回退 1 题，K4 欠满 7 题、K8 欠满 17 题。都没有触发 10% 的报告条件 ✓

## 注意

1. **符号等价没有独立重跑**：本环境无法访问 PyPI，装不了 math-verify 和 sympy。评分部分的独立性范围是：提取全量独立核对，字符串相等全量核对，40 个只靠符号比较的对全部人工核对。我没有重新执行 math-verify。对 B 的用途（选择训练答案）来说，判对的方向已经全部核对，可能遗漏的只是被误判为错的行，这只会让可用解变少。因此我接受。
2. 这些是生成阶段的描述性数字，不是 B 的科学终点。B1/B3 学生还需要输入 A1 和数值 A2-lite，B3 的余量很窄。
