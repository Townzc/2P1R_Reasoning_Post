# B 学生输入驱动（92 个源码）与学生路径（96 个源码）：源码 CR

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-B-remaining-generation-selection-complete-path-CR`（输入驱动，target `e556c4c9`）；`p011-B-retained-students-complete-path-CR`（学生路径，target `bf708e6a`）

## 结论：FIX-REQUIRED（不授权输入准备）

### 阻断问题：gold 文件路径错误，驱动必然失败

- `scripts/prepare_p011_b_remaining_student_inputs.py` 中 `GOLD='.local/p009_20261014/r1/source_assets_r1/math500/test.jsonl'` 指向的是 **HF 原始下载**。按 p009 `PUBLIC_SOURCE_DOWNLOADS.json` 的记录，它的 sha 是 `35dc4108…`（446,564 字节）；SOURCE_BINDING 的 `student_endpoint_files` 也记为这个值。
- 但 `prepare_student` 第一步就要求 `sha(GOLD) == b_student_evidence.GOLD_SHA256 = 132582ca…`。这是 P1 处理后的 `math500.jsonl`（504,454 字节，见 p009 `INPUT_MANIFEST.json`），P010 学生和 E9 都用的是它。学生 IO 的 audit 同样要求 `GOLD.jsonl` 的 sha 等于 `132582ca…`。
- 两个 sha 不可能同时满足，所以驱动会在写入 fence **之前**就 raise。这不会造成损害，但驱动没法用。
- 原 `prepare_p011_b_runtime_inputs.py` 和 `prepare_p011_c2_students.py` 里也有同样的常量，我之前没有发现，这是我的疏漏。C2 已经关闭；原 B 驱动从未运行。
- **修复**：把 `GOLD` 改为 sha 为 `132582ca…` 的冻结 `math500.jsonl` 在本地的实际路径，并同步更新 SOURCE_BINDING 的 `student_endpoint_files`。不改其他任何东西。修复后重新提交，我会尽快复审。

### 其余部分已逐行看过，没有发现别的问题

- **输入驱动**：
  - `actual_generation_A3` 绑定 4 个完整结果文件、生成报告 `0c1a9a1f`，以及我在 A3 中给出的 3 个 flag（见我的 A3 报告中的"绑定"一节），并要求 oracle passed、technical_unknown = 0、6,400 条输出，records 和 selection 的 digest 都要一致 ✓
  - 先写 fence 再动手；分词器用 C1 模型资产绑定的 sha 核对（base，EOS 151643）；`student_inputs` 原样复用已审代码（训练里出现未映射行就 raise，K1 期望集合 = 400 − 全未映射题）；B1/B2/B3 都会编码（B2 编码不花钱，也不会被派发）✓
- **学生路径**（与 `b_current_path` 对比）：
  - 只允许 B1 和 B3；必须绑定生成 A3、输入 CR 报告、输入 manifest，以及 5 个新 flag。
  - `remaining_student_budget` 在每次派发前，对**尚未尝试**的学生按顺序检查 80% 规则，所以 B1 派发时也会确认 B3 仍然放得下 ✓
  - 账本接上了失败的 B 和 C1；资产收据 `0a6c9e26…`；protected 0 ✓

## 仍需

修复并复审 → 构建输入 → 输入 A1 → 具体 SPEC 与数值 A2-lite（B3 的余量只有 $0.06）。B1/B3 的完整窗口各 37,465 s，按目前的时间在 10/22 05:00 UTC 截止前仍然放得下，但每过一小时余量就少一小时。
