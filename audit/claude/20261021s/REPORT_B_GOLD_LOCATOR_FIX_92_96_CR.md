# B 学生输入驱动 gold 路径修正：92 / 96 源码 CR

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`

## 1. 输入驱动（92 个源码）：PASS

- scope `p011-B-remaining-generation-selection-complete-path-CR`；target `11a18aaa279a2c6a1fd3974fd86c004651238f79`
- SOURCE_BINDING `9371c51a735b88b58e7634f407bb3549c7495a4f8eedbc79c22b313a260dd5c4`，92 个文件 sha 全部一致
- 与 FIX-REQUIRED（3f076ba7）时相比，只改了 `scripts/prepare_p011_b_remaining_student_inputs.py` 的两个常量：
  - `GOLD` 改为 `.local/p009_20261014/r1/stage0_inputs_r1/math500.jsonl`，sha `132582ca…`，等于 `b_student_evidence.GOLD_SHA256`，也等于 p009 INPUT_MANIFEST 中的值
  - `PACKET` 改为新的绑定目录
  - 其余 91 个文件不变
- `student_endpoint_files` 已同步修正
- owner_B16 `2e0c8af1…`；delegated_failure_decision `8ca01d6f…`；actual_generation_A3_report `885fce37…`
- **input_preparation_authorized: true**：授权在 CPU 上本地构建一次学生输入，然后接受输入 A1。不授权学生模型调用。

## 2. 学生路径（96 个源码）：PASS

- scope `p011-B-retained-students-complete-path-CR`；target `1bf3de6d8c6187994faf12ffd401a8ce992d562c`
- SOURCE_BINDING `e723639f71b6d8a563dd11a993988ddc35df11a4f720d2479d73984aea2f721d`，96 个文件；与 47b442ab 时相比只有同一个驱动文件不同
- 5 个 flag 全部 **true**：all96_sources_and_new4_adapters_accepted、actual_generation_A3_and_student_input_A1_required_before_paid_entry、B1_B3_only_B2_first_cut_and_failed_reserves_retained、original_base_receipt_reused_without_old_weight_transfer、original_science_scoring_and_absolute_windows_unchanged
- 4 个适配器已在 3f076ba7 中逐行看过，这次没有改动。
- 不授权付费调用；之后还需要输入 A1 和具体 SPEC 的数值 A2-lite，账本要包含两个新的长序列失败父任务。
