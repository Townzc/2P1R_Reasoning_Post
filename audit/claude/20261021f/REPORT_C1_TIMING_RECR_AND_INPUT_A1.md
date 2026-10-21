# P011 C1：计时修正源码复审 + 实际输入 A1（A2-lite 仍待定）

- **审计方**：Claude，2026-10-21 03:35 UTC 前后
- **共享请求**：`p011-C1-complete-path-CR-A1-A2-lite-r1`
- **target_commit**：`0c37b5a07025fbfa71b6b82532d1dc3797813b45`（请求文件更新提交为 31f0d3ff）
- 脚本 `a1_c1.py`、结果 `A1_C1_RESULT.json` 随本目录提交

本报告包含两个独立结论，第三项（数值 A2-lite）仍然缺失。

---

## 1. 源码复审（计时修正）—— **PASS**

| 字段 | 值 |
|---|---|
| scope | `p011-C1-complete-path-CR` |
| decision | `PASS` |
| target_commit | `0c37b5a07025fbfa71b6b82532d1dc3797813b45` |
| binding packet | `c1_whole_iteration_timing_preflight_v1`，MANIFEST `2e60acba30807740176a1e4f9b39e735b697acbb850615ad0a2d1433a267e6c2`；12 个源码在 target 上重算全部一致 |
| 唯一变更 | `experiments/p011/c1_execution.py` → `623f9dae3799dad60e0489e8ca5a308223ca80294b774563eb3b3c074c3d62b2`（其余 11 个与 20261021e 相同） |
| input_preparation_authorized | 不再适用：输入复制已在 817f7d67 下完成一次，**不授权再次复制** |

**逐行确认**（对应 REVIEW_REQUIREMENTS 中的 6 条结论，全部成立）
- `cycle_start` 放在循环开头，在 forecast、claim 核对、store.put 和 INTENT commit 之前；`cycle_end` 放在 CONFIRMED commit 和远端 `chunk_done` 写入之后。因此每轮计时包含 **3 次 volume commit 和远端 chunk_done** ✓
- `times` 改为完整的单轮用时，下一次 forecast 用的就是这个值 ✓
- `check_body` 只读回放时使用同一份 cycles，并逐项核对：chunk 编号、commit 次数为 3、`body_ack` 与 ack 相等、elapsed 等于 end − start、各轮不重叠、单轮用时不小于 ack 用时 ✓
- 旧的 body-only 计时仍保留，但只作为诊断字段；spec 缺少 `whole_chunk_iteration_timing=true` 时直接拒绝 ✓
- 最后的 summary/proof 写入和 commit 不在任何一轮计时内，由 `future_allowance_seconds` 覆盖，这一点已明确写出 ✓
- 失败时，`FAILED.json` 会带上已完成各轮的计时 ✓

**测试**
- 新增的 4 项测试：通过。
- 旧测试的 fixture 中没有新标志，所以约 20 项会因为 `validate_spec` 拒绝而报错。这是预期行为，并且说明新门确实生效。
- 我在本地临时给旧 fixture 补上这个标志（不提交），把 7 个文件共 51 项全部重跑：
  - 49 项通过；
  - 1 项因本机没有 torch 无法导入；
  - 1 项是我的补丁造成的假失败：它专门检查"没有标志时会被拒绝"，而补丁把标志加上了。
- **建议** Codex 以后改一下旧 fixture，让完整的模拟闭环测试能直接在最终源码上运行。

---

## 2. 实际输入 A1 —— **PASS-WITH-NOTES**

| 字段 | 值 |
|---|---|
| scope | 实际输入 A1（属于共享请求的一部分，不是数值或付费准入） |
| PUBLIC_MANIFEST | `ba38522a3656d05c1b714c4f00670cd613bbdabaa12ab55b6ce0210b1e29ea09` |
| original_inputs.tar.gz | `bf230a72ea925fbd34073c0a97ca1773260f7e8d7a3f179798a0b66bdd8ad261`，13,683,744 bytes |
| original_group_binding_sha256 | `54e73b1cb1e69d300ee40423236e2d5d2f91e96e42ad03a81f10191256546006`（包内副本与公开版本逐对象相同） |
| task inventory | `tasks_sha256` `a1e0a2ac…`；`memberships_sha256` `a2454456…`；9,594 条唯一序列；300 个 chunk；5,214,325 个输入 token；4,589,326 个监督 token；最长 1,758 |

**我独立核对的内容**（解压完整 archive，用自己的脚本重算，不调用 c1_nll）
- **原字节复用**：原 MANIFEST 的 22 个成员都与 bytes/sha 一致；18 个组文件的 sha 和 bytes 与 binding 中**原始文件**的记录逐一相同。binding 中的这些记录，我在上一份 CR 里已经追溯到 P009 S1 与 P010 student_inputs_r2 ✓
- **配置**：
  - 每组 config 的 n、seed 17、1,024 次更新、2,097,148 个 target、Qwen2.5-1.5B 基座 revision `8faed761…`、EOS `[151643]` 都一致；
  - `encoded_rows_sha256` 与 `training_rows_sha256` 都由我独立重算并匹配 ✓
- **编码结构**（共 10,800 行）：
  - prompt 部分全部为 −100，答案部分的 label 等于 ids；
  - 151643 只出现一次，并且在末尾；
  - 长度不超过 2,048；token id 都在词表范围内；
  - rows 与 encoded 的 path_id 和 problem_id 一一对应。

  结果：**0 个违规** ✓
- **嵌套与题目集合**：
  - 三位教师各自的 n400 都是 n3200 的有序前缀；
  - **三位教师用的是同一组 3,200 道题，顺序也相同**；
  - 每题的 prompt token 在 T7 和 T72 之间 3,200/3,200 相同 ✓
- **清单**：我用同样的 digest 定义重算了 tasks、memberships 和各项计数，**8 项全部与 TASK_INVENTORY 相同** ✓

**需要披露**
1. **各教师组的选择规则不同，这是 C1 结果最大的混杂因素**：

   | 组 | attempt01 | 重试 | 未验证兜底 |
   |---|---|---|---|
   | T15 | 3,200/3,200（按 S1 定义，T1.5 的 attempt01 必须答对） | 0 | 0 |
   | T7 n3200 | 2,997 | 203 | 82 |
   | T72 n3200 | 2,945 | 255 | 83 |

   T7 与 T72 的兜底题重叠 29 道。所以 T15 组只包含"T1.5 首次就答对的题"，而 T7/T72 组含有重试和未验证答案。报告中 NLL 的组间比较必须同时给出 nonfallback 子集的结果，并说明这里的题目是以 T1.5 的成功为条件选出来的。

2. **跨教师完全相同的序列有 6 条**：T15 与 T7 共 5 条，T15 与 T72 共 1 条。它们只前向一次，在各组中都按成员计数。

3. **各组监督 token 总量接近**：

   | 组 | 监督 token |
   |---|---|
   | T15 n3200 | 1,494,755 |
   | T7 n3200 | 1,566,436 |
   | T72 n3200 | 1,529,639 |

   这与之前"T72 的回答并不更长"的诊断一致。

4. **数值精度**：logits 为 BF16，转成 FP32 后计算损失，单个 token 的分辨率约为 0.01 nats，见上一份 CR 的注意第 4 条。

---

## 3. 数值 A2-lite —— **尚未给出（ABSENT）**

现在还没有实际的 SPEC 和计时依据，所以不能上传，也不能派发任务。为节省时间，下面是我**预先说明的接受条件**：代理计时满足这些条件，我就会接受。

1. **代理来源**：必须是**实测**的 P010 或 P009 学生训练记录，并且条件相同：H100、同一个 Qwen2.5-1.5B 基座、同一批长度不超过 2,048 的编码。训练包含前向、反向和优化器，所以作为纯前向的上界是保守的。需要写明所用记录文件的 sha。
2. **每个 chunk 的代理时长**取以下三项之和：
   - (i) 前向部分：按 token 缩放的训练用时上界（以 32 × 1,758 个 token 计）和 32 × 0.25 s 的调用下限，两者取较大值；
   - (ii) **3 次 commit**：如果有实测的 volume commit 用时，取其中最大值 × 3；没有实测就按 3 × 10 s 计；
   - (iii) store 读写：按 2 × 1 s 计。

   这些都必须写在 spec 的 `source_evidence_files` 和说明中。
3. **代理值不能过度悲观**：`forecast` 用的是 spec 中的时长与实测时长合并后的**最大值**，所以代理值会一直影响后面每次的预测。代理定得过大，会导致初始准入或中途预测失败。请给出单一的、有依据的保守值，不要层层叠加安全系数（forecast 本身已经乘了 1.2）。
4. **窗口与预算**：
   - 实际预期大约是：9,594 次前向，每次几十毫秒；再加上 900 次 commit。
   - `worker_seconds` 应当能容纳 1.2 × (300 × 代理时长 + 模型加载 + `future_allowance`)，同时整个结果窗口必须在 10/22 05 UTC 之前结束；
   - reserve 不超过 C 类剩余额度的 80%，并且与 C12/180/48 一致；
   - `measurement_exceptions = 0`。
5. 以上条件满足，并且 6 个 admission 标志都能如实设为 true，我就会在**同一请求**下给出 A2-lite 的最终结论。在此之前，**不得上传，也不得派发 C1**。
