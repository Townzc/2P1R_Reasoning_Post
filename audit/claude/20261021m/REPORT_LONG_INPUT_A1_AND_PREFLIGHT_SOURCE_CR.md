# 长序列实际输入 A1 + 三臂工程预检源码 CR

- **审计方**：Claude，2026-10-21 08:45 UTC（负责人夜间全权审核期间）
- **target_commit**：`63e8710fc24c7c5b206be2515976ff4dc57ecc89`
- 脚本 `a1_long.py`、结果 `A1_LONG_RESULT.json` 随本目录提交

---

## 1. 实际输入 A1 —— **PASS-WITH-NOTES**

- **scope**：`p011-long-A-D-complete-runtime-input-A1`
- **packet**：`long_numeric_gold_inputs_actual_v1`
  - PUBLIC_MANIFEST：`f4371a6afe9252a7047f0d83a21fef88718f82357510d637f6a7f11fd404c6c7`
  - ACTUAL_INPUT_BINDING：`cee34dc0…`
  - 公开 archive：`2a5dd47c…`，56 个成员
- **源码**：37 个文件，与 e6ce0467 的 binding 相同

| 独立核对 | 结果 |
|---|---|
| 公开 archive 中的成员与原构造器 MANIFEST 的 sha 一致 | 0 个不一致 ✓ |
| 10 格（A1–A8 来自 OT3 NFC，D1/D2 来自 AM）的 `plan.json` 与已接受的原 `*_PLAN.json` **逐字节相同** | 10/10 ✓ |
| `ORIGINAL_ROWS.ordered_path_ids` 等于 plan 的 `row_path_ids`；`source_encoded_sha256` 等于原 ENCODED.jsonl 的 sha；plan_file_sha 一致 | 10/10 ✓ |
| **按 plan 顺序，从我手中已 A1 的原 OT3/AM `ENCODED.jsonl` 逐条取出每一行，流式计算 digest，与 `original_row_values_sha256` 相同**；该值也等于 COMPLETED 中 30 个格 × 臂证明的 `encoded_sha256` | 10/10 ✓ |
| 每格 3 个臂的 LR 向量：我独立按 ⌈5%U⌉ 预热、余弦退火到 10% 峰值重算，与文件逐元素一致（误差 < 1e-15） | 30/30 ✓ |
| B/U/q：A 格为 41,813,212 / 654，q 依次为 16/8/4/2/1/4/1/1；D 格为 4,070,922 / 64 / 1 | ✓ |
| gold 投影：600 行 = 530 个 str + 30 个 int + 40 个 float；原值和原类型与 BENCHMARKS 一致；规范化后的 gold 为字符串原样、int 转 `str`、整数值 float 转 `str(int)`；投影行的 sha 正确 | 0 违规 ✓ |
| endpoint：共 3,300 条，id 集合正确；LOCAL 去掉 gold 再加上 `request_sha256=digest(LOCAL 行)`，恰好等于 GPU 文件，GPU 文件中没有 gold | 0 违规 ✓ |
| `required_context` = prompt 长度 + 16,384；最大 context 为 17,243；同一题在不同模式下的 prompt token 和文本 sha 一致 | ✓ |
| **prompt 文本**：我自己用默认 system 拼出 Qwen 原生模板，600 题的 `raw_prompt_text_sha256` 和 NFC 后的 sha 全部一致；没有 NFC 改动；所有 prompt 都以 `151644 8948 198` 开头 | 0 违规 ✓ |
| 10 格各自的 ENDPOINT_GPU/LOCAL 与 baseline 文件的 sha 相同，即为副本 | ✓ |
| AM 与 OT3 的 BENCHMARKS 逐字节相同；training_tokenizations 为 0 | ✓ |

**限制**
- 各格私有的 `encoded.json` 文件（以 indent 格式写出）我没有直接读取。我核对的是这些文件对应的行内容 digest：用原 ENCODED 按 plan 顺序重算 digest，结果与记录一致。
- prompt 的 **token ids** 我无法本地重新分词验证。已确认的是：文本 sha 与原生模板一致，构造器在运行时做过 decode == NFC 的往返校验，并且 worker 会在加载 vLLM 之前再做一次 decode 校验。
- 原 37318 的失败记录和 530 个未保存的临时编码，都按原样保留。

---

## 2. 三臂工程预检：源码 CR —— **PASS**

- **scope**：`p011-long-three-arm-engineering-preflight-source-CR`
- **packet**：`long_preflight_source_v1`，MANIFEST `9b1d9b45…`，SOURCE_BINDING `8a5be22b…`。33 个 source 在 HEAD 上重算全部一致；AST 闭包检查没有遗漏。

| flag | 值 |
|---|---|
| input_preparation_authorized | **true**（只允许一次生成 saved-token 子集的 CPU 运行） |
| original_completed_long_inputs_accepted | **true**（见上节） |
| engineering_subset_only | **true** |
| owner_decision_sha256 | `364aaf6c…` |

**逐行要点**
- `subset.select`：
  - 训练子集：从 A8 中按 n_processed 降序、再按 path_id 取最长的 2 行，要求每行至少 15,000 token；plan 为 2 次 update，每次都用这两行；LR 是原函数在 U=2 时的值。
  - 评测子集：每个基准取 8 个 sample-0 请求，按 prompt 长度分位均匀选取；MATH 的最后一条换成最长 prompt 题目的 greedy。共 32 条请求，cap 16,384，context 17,243 ✓
- `training.train_terminal_subset`：与正式的 `train_terminal` 逐行相同，只是校验函数换成子集版本。checkpoint 使用 `long_checkpoint.save`（mmap）；导出 BF16；`accumulate`、`load_model` 都直接复用正式模块 ✓
- `execution`：
  - 子进程 spawn，必须退出并 join 之后才启动 vLLM；
  - 使用正式的 `engine_settings` 和 `validate_engine`（max_num_seqs=256）以及正式的 `evaluate`（512 一批，这里只有 1 批 32 条）；
  - `PhaseJournal` 记录状态保存阶段和导出阶段的耗时，各阶段都计到最后一次 commit 为止；
  - 不做任何评分 ✓
- `path`：
  - 逻辑 ID 是独立的 `preflight_<arm>_s17_r1`，存储 key 为 `engineering/…`；
  - 三个 job 的限额固定：worker 900、platform 960、startup 600、closeout 7,200、window 8,760；S-F15 内存 96 GiB；
  - reserve = ⌈费率 × 1,560 / 3,600⌉，三个 job 合计 ≤ $6（按历史费率为 1.91 + 2.13 + 1.91 = 5.95）；
  - 计入 A 类，并受 80% 规则约束；protected 为 0；
  - 账本中保留 r1 失败的父尝试；并发槽上限 4 ✓
- 测试：3 个新测试文件在本地全部通过（OK）。

**注意**
1. **S-F15 可能超过 900 s**：全参的终态 state 约 18.6 GB，需要依次完成写入网络卷、mmap 回读比对、计算 sha、commit，这部分可能就要几分钟；再加上加载、训练 2 步、导出 3 GB 和 vLLM 启动，有可能撞上 900 s 的硬上限。万一超时，已经 commit 的阶段计时会保留，预检的目的（查错和计时）仍然能部分达到。负责人批准的上限是 $6，所以**不放宽**。
2. 32 条请求的评测**不能代表**正式 512 条一批的吞吐。正式 A/D 的 A2-lite 必须明确说明如何外推，`measurement_exceptions` 仍为 0。
3. 下一步：子集构造的实际 A1，以及预检的 SPEC 和 A2-lite（9 个 flag，同一请求）。
