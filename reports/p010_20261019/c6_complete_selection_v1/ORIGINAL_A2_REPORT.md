# P010 审计 20261020k：C6 infinity 局部补完 A2，以及 E9 输入 A1

- **审计方**：Claude
- **时间**：2026-10-20 08:31 UTC
- **审计对象**：`a172e10c`

## 1. C6 局部补完 A2（`p010-C6-nonfinite-local-selection-resume-A2`）：PASS

**绑定的文件**
- SPEC：`ed894c556dc367fd…`
- `ORIGINAL_FAILURE_FILES.json`：`da655e30b17c1c1b…`
- 委托决定：`20261020i/OWNER_DELEGATION_AND_DECISIONS.md` 中的 D3

**代码审查**
- `cue_answer_key_nonfinite.answer_key` 和原来的 `cue_answer_key.answer_key` 逐行比较：只多了一个分支，把 ±inf 映射成两个带正负号的符号键；NaN 仍然报错。抽取逻辑（`extracted_tail`，直接 import 原函数）、文本键、缺失判定、保留 6 位小数、0 和 -0 合并为同一个键，这些都没有变。
- `cue_key_resume.confirmed_prior` 要求先满足以下条件才继续，任何一条不满足就停止：
  - 恰好有 731 个已确认的键；
  - 恰好有 1 个失败键，并且它的哈希、`extracted_answer == '\\infty'`、错误文本都与原失败记录一致；
  - `automatic_retry` 为 false。

**验收字段**

| 字段 | 值 |
|---|---|
| signed_infinity_symbolic_keys_accepted | true |
| confirmed_keys_reused_without_reparse | true |
| failed_key_single_new_attempt_accepted | true |
| no_new_model_outputs | true |

## 2. E9 输入 A1（`p010-E9-exact-input-and-plan-A1`）：PASS

**绑定的文件**
- BASIS：`7c919d0f93cf65f3…`
- `actual_inputs.tar.gz`：`e356c1e704ee26e8…`
- 原 T72 的 A1：`20261020f`
- D2：`20261020i`，负责人已于 00:10 直接批准

**检查结果**

| 检查项 | n400 | n3200 |
|---|---|---|
| 与 T72 已审 K1 `rows.json` 的 `path_id` 顺序是否一致 | 一致 | 一致 |
| prompt 与 response 文本是否逐字一致 | 一致 | 一致 |
| 是否新选了数据 | 否 | 否 |
| OLMo 编码：最后一个监督 token 为 EOS 100257、标签计数一致 | 是 | 是 |
| 最大长度（token） | 1,429 | 1,675 |
| 截断或删除的条目 | 无 | 无 |
| 计划：Σ = 2,097,148 / 1024 次更新 / 每条更新次数 = 暴露次数 | 满足 | 满足 |
| 暴露次数 | 11–12 | 1–2 |
| seed / LR | 17 / `14ac59d2` | 17 / `14ac59d2` |

**MATH 端点**
- 共 500 题，题目和顺序与 Qwen 端点一致。
- 提示文本由同一个 `src.sft_data` 模板生成（`Problem: …\nSolution:\n`），再用 OLMo 分词。
- 最长的提示是 760 token，加上 1024 不超过 2048，所以没有不支持的题。

**局限**
- 本地没有 OLMo 分词器，无法独立重新分词，也就无法逐题核对提示文本解码后是否一致。
- 训练端在模型侧会做重新分词校验，但评测端没有对应的校验。
- 两个端点的 `source_row_sha256` 因为字段定义不同，不能直接比较。

**说明**：E9 现在可以进入 A2（运行时审计）。v3 要求的 A4 报告已在 `20261020j` 发出，Tier 3 可以按授权继续。
