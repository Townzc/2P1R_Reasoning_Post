# P011：AM 实际输入 A1、OT3 失败完整性、4032 复用路径 CR

审计方：Claude，2026-10-21 00:40 UTC 前后。下文分三个独立结论，各自对应一个 scope。

脚本：`a1_am.py`；结果：`A1_AM_RESULT.json`（随本目录提交）。

**我实际使用的工具和访问范围**
- 拼接并解压 `am_inputs_actual_v1/am/original_artifacts.tar.gz.part000`（sha `092c4439…`），14 个成员都与原 MANIFEST 一致；
- 读 OT3 失败包中公开的 PARENT_DISPOSITIONS、计数和失败标记；
- 本地跑了新增的 11 项 4032 消费者测试，全部通过。

**没有访问到的内容**：私有 SQLite（AM 27.8GB，OT3 约 43GB）。因此"父题从全池还原""打乱顺序本身""D 在重复回答中选哪一行"这三项，我只能核对它们与保存记录之间的一致性，无法从原始全池重算。

---

## 1. AM（实验 D）实际输入 A1 —— **PASS-WITH-NOTES**

- **scope**：`p011-OT3-deficit-and-AM-complete-input-A1`（AM 部分）
- **target**：`cf9a12e4f3cfb883b09be603c8aa5d79206c90f3`
- **packet**：MANIFEST `58d871c6eee9f010c248adcee822ddde64e97146fadc61722ad8fc1945015c59`（16 个文件，全部一致）
- **绑定**：
  - 三源 lock `0e78298f…`
  - 构建代码 `df4d5904`，CR `5c91d0d1`
  - R1/R3 amendment `e58e8d72…`

| 检查 | 结果 |
|---|---|
| D1/D2 各 1,024 条，同一组父题，顺序一一对应；来源分别全部是 am_thinking / am_qwen3 | ✓ |
| 选中父题 = disposition 中合格父题按候选顺序排列 = FILTER_COUNTS 中的列表 | ✓ |
| 候选位置 1..1079 连续，第 1079 个正好是第 1,024 个合格题（凑满即停） | ✓ |
| `chosen` 行与 D1/D2 的 path_id 逐一相同 | ✓ |
| 剔除计数独立重算：去污染 2、am_thinking 超长 48、am_qwen3 超长 13、不完整 0，合计 55，与报告一致 | ✓ |
| 选中回答全部"完整"：`</think>` 之后的区域含 `\boxed{` | ✓ |
| 选中题对 MATH-500/AIME24/AIME25/AMC23 共 600 题独立重算 13-gram 去污染：0 命中 | ✓ |
| 编码结构：system 等 prefix 全部掩为 −100；监督区间连续且以 `<|im_end|>` 151645 结尾，区间内部不再出现 151645；最后一个 token 是不监督的换行 198；总长 ≤ 16,384（最长 16,282） | 2048/2048 ✓ |
| 同一父题在两个教师下的 prefix token 完全相同；所有 prefix 都以默认 system 开头（`<|im_start|>system\nYou are Qwen, created by Alibaba Cloud…`） | ✓ |
| AM 作者的 verify_score：选中的 2,048 行全部为 1.0 | ✓ |
| 单遍 token 数：D1 3,310,075，D2 4,070,922；B = max = 4,070,922；U = 64 | ✓ |
| 训练计划：每格 token 总数恰好等于 B，每条曝光 q 或 q+1 次，64 次更新都非空。D1 是 q=1 加 226 条 extras；D2 是 q=1、0 条 extras。前 q·n 个位置恰好等于 `Random('17:pass:e')` 的打乱结果；extras 无重复 | ✓ |

**注意（需要披露）**
1. 两位教师的回答格式都是 `<think>…</think>` 加 `<answer>…</answer>`。学生会学会 `<answer>` 标签，评测时答案区域取 `</think>` 之后的文本，不受影响。
2. D1 的回答更短（平均每条约 3.2k token，D2 约 4.0k），在固定剂量下有 226 条 D1 回答被训练了 2 次。这是"固定计算量"设计的直接后果，报告中要写明。
3. 全共同池的来源一致性中有 1 个不一致或缺失的例外，照常保留。

---

## 2. OT3 原始失败的完整性 —— **完整性 PASS；原数据门 = FAIL（保留）**

- **packet**：MANIFEST `b68bcfc8b05cf701ad18e4ffe595b9add38052fc2d0e81e7d7fb40021e23c1d5`（11 个文件，全部一致）
- **disposition**：
  - 53,107 行，候选位置连续，父题哈希唯一，行数全部为 16；
  - 合格 4,038，不合格 49,069，没有出现"合格却带标记"或"不合格却无标记"的行；
  - 标记计数为：不完整 48,222，超长 847（只对完整且未被去污染剔除的父题检查），去污染命中 3；
  - 全池中行数不是 16 的父题有 9 个。
- **结论**：这是一次真实的数据不足（4,038 < 4,096），不是技术故障。原失败记录完整，FAIL 照原样保留。

**需要披露的选择偏差（重要）**
- 90.8% 的父题至少有一条回答在答案区域没有 `\boxed{`。规则要求 16 条全部完整，这一条就会**强烈偏向"QwQ 每次都规范作答"的题**。
- difficulty 字段全部缺失，无法比较保留题与剔除题的难度。
- 报告必须写明：A 网格是在这个强筛选后的子集上测得的。
- 建议 Codex 在 4032 构建的 A1 中附一个只读诊断，供解释时使用，不改变任何选择：
  - 全部候选回答中，含 `</think>` 的比例；
  - 回答任意位置含 `\boxed{` 的比例；
  - 逐条回答的不完整率。

---

## 3. 4032 复用构建路径 CR —— **PASS-WITH-NOTES**

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| scope | `p011-OT3-4032-confirmed-parent-reuse-construction-CR` |
| target_commit | `410c035d8c9b12d5c6e5d98220cec99914c0daeb` |
| packet MANIFEST | `ac864839c51b477775715e1169abb5f2818179cd74feefdf45b7f061585ac27c` |
| source_files | `experiments/p011/__init__.py` `ef9c51d5…021d`；`experiments/p011/data_contract.py` `4bcb6227…2204`；`scripts/prepare_p011_long_inputs.py` `4468a80d…12e1`；`scripts/prepare_p011_ot3_4032_inputs.py` `4546ffad73a9171804cfa1b3d931ce6ae27b61aa40efdb7d8bfbda84af67ca3a` |
| plan_sha256 | `20d919afd4f1d7d1f237042bad5804fff1de20ebeda444cfdbf92f250bb69c22` |
| source_lock_sha256 | `0e78298f49b86ee3de7182443eb052da422d14af14f423bceb3f728a1696fdb0` |
| owner_count_amendment_sha256 | `5d1fa79a456f358abccaca8e50aba47603e3af957c09d5ac11f8e5ef8b3da74a` |
| owner_prior_R1_R3_sha256 | `e58e8d721f740e438d82ef3f5e6ecea50970e3b507458ad3d77e07eacfe75c72` |
| proposal_sha256 | `7fc901983816ded497f89fe622aa061df446f1e2a116e68c1166b5870be12726` |
| original_failure_preservation_sha256 | `662d42e2b68f207e0a2946a4d9b11d21df25784dd0b91a51f4f010c0c6c89849` |
| original_code_acceptance_sha256 | `54820eeb48098146ae97194cc7f9323d9645e2e0610329e001c6b83e9444a56b` |
| grid | A1 (252,1)、A2 (252,2)、A3 (252,4)、A4 (252,8)、A5 (252,16)、A6 (1008,1)、A7 (4032,1)、A8 (1008,4) |
| confirmed_eligible_parents_reused_without_refiltering | true |
| original_failed_attempt_retained | true |
| new_global_attempt_fence | true |
| first_full_encoding_only | true |
| operational_details_accepted | true |

**逐行审查要点**
- `admit`：同时绑定负责人修订（含 grid、4038/4032/6、各项 false 和 true 标志）、本 CR 的字段、原失败保存证明（EXIT1、session 88890、禁止重试），以及原 INTENT 的源码与 lock。原目录中如果已有 ENCODED 等编码产物，直接拒绝运行 ✓。
- `confirmed_order`：只读 disposition 中的布尔值；校验位置连续、行数 16、哈希唯一、合格行全部标记为 False、计数 4038/49069、已穷尽候选（未检查数为 0）✓。不重新做过滤、分词或评分 ✓。
- `restore_keys`：在只读、不可变、query_only 的 SQLite 中把哈希映射回原父题键，并检查规范化与唯一性；缺一个就报错，不替补 ✓。
- `select_cells`：
  - 取原顺序的前 4,032 个，剩余 6 个记录在案；
  - 每个父题 16 行，按原 R2 的字面种子打乱回答顺序；
  - 各格嵌套关系为 252 ⊂ 1008 ⊂ 4032、K = 1 ⊂ 2 ⊂ 4 ⊂ 8 ⊂ 16；
  - A5、A7、A8 都是 4,032 条 ✓。
- 编码与计划：复用已审过的 `encode_and_plan`，B 取 8 格单遍 token 数的最大值，U = ⌈B/64000⌉，有独立检查 ✓。全局 attempt fence 与 create-only 输出 ✓。

**注意**
1. 与原计划相比，各格题数少 1.5625%，三条对角线仍是同 N（4,032）。这是在看到候选池可用量之后、任何学生结果出来之前做的范围修订，必须披露。
2. 实际构建完成后需要做新的 A1。我会重点核对：
   - 嵌套关系；
   - B、U 与各格单遍 token 数；
   - 精确剩余量能否凑出；
   - 上面第 2 节建议的只读诊断（如果 Codex 提供）。
