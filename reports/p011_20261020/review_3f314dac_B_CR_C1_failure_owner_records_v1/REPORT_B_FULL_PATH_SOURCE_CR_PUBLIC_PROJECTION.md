# P011 B 完整路径：源码 CR

- **审计方**：Claude，2026-10-21 06:55 UTC 前后
- **请求**：`p011-B-generation-student-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-B-generation-student-complete-path-CR`

## 结论：PASS-WITH-NOTES

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-NOTES` |
| target_commit | `bca90236c7be2c2b37f3a207eb23d1f518027290` |
| packet MANIFEST | `53ebcdf81010ce98936fa247797fd6f0c00d4e26e5755d3cd5f18353fd734489` |
| SOURCE_BINDING | `2340041a…`。71 个 source 文件在 HEAD `bd5466e1` 上逐个重算，全部一致 |
| owner_B16_sha256 | `2e0c8af11de76ac34368f9188d3731b2ac89d0e47e5870e8684e3d55c4953f60`，即我在 d3f66ec3 记录的负责人选项 (b) |
| original_input_files | 3 个 P010 输入：MATH_ROSTERS `2cd19c3f…`、MATH_SOURCE `fe02f5a3…`、t15_fixed_requests `96b0aa9b…` |
| student_endpoint_files | MATH_ENDPOINT `8f9a0500…`、math500 gold `35dc4108…` |
| input_preparation_authorized | **true**。覆盖两项：生成输入的投影；以及在新的 6400 条全部完成评分之后，学生输入的一次性构建 |
| 不授权 | 上传、生成、训练、任何付费调用。这些都必须等实际输入 A1 和 A2-lite 通过后才能进行 |

## 逐项要点

- **源码闭包**：我对 71 个文件做了 AST 扫描，本仓库内的 import 没有遗漏。评分子进程以 `-m MODULE` 方式启动，所需模块已列在闭包中。（长路径 R1 那类问题，B 没有。）
- **生成**：
  - `short_generation.b_requests` 复用 P010 的 `canonical_request(pid, attempt, 't15', prompt)` 和 `sampling`，只把温度改为 1.0；
  - attempt 1–16 的 seed 函数与 P010 T0.8 相同，attempt 1–4 是共同随机数 ✓
  - `validate_queue` 要求请求逐对象等于 400 × 16 的冻结列表，prompt 长度 + 1024 ≤ 2048 ✓
  - 生成按 256 条一批，共 25 批；每批 3 次 commit 并写远端 ack；完整轮次计时覆盖这些开销 ✓
- **选择规则**：`b_selection` 严格实现负责人选项 (b)：
  - K1 取 16 次尝试中第一个可用的，16 次都不可用时取 attempt01，并标记为未验证兜底；
  - K4/K8 取前 k 个不重复的可用答案，16 次都不可用的父题不进入 K4/K8；
  - 冲突列表必须正好等于兜底列表；兜底超过 10% 时，学生准备被阻止，交由负责人处置 ✓
- **学生**：`b_student_training` 校验配置后，调用**未改动的 P010 训练路径**（`rt.new_model / rt.train`，block journal 64 × 16），参数与原来相同：1024 次更新、2,097,148 个 target、seed 17、相同 LR 向量。在 FP32 下合并、以 BF16 保存。训练子进程退出并 join 之后才加载 vLLM ✓
  - 学生输入只对新选中的答案编码一次：`encode_row(..., 2048)`，原 P010 数据不重新编码 ✓
- **评测**：沿用 P010 端点，500 道题 × (greedy + 4 次采样)，每批 256 条，共 10 批，每批 3 次 commit 并写 ack ✓
- **remote_path**：
  - 输入：`b_inputs_r1/<run_id>`，upload 与 worker 一致；
  - 输出：`b_runs_r1/<logical>/evidence.tar`，pack 与 collect 一致；
  - T1.5 资产：`mp-teacher-cost-20261012-r1/assets/model`；基座：`mp-engineering-20261012-r1/assets/model`。这两处都是 P010 用过的原始 writer 路径 ✓
  - GOLD 只保留在本地，不在 input_files 里，不会上传 ✓
- **生命周期**：账本、并发槽、dispatch/claim/terminal fence、失败保全，与 C1/long 路径共用同一套实现 ✓

## 注意

1. **时间窗是 B 的最大风险**：
   - 生成的评分上限是 62,000 s（约 17 小时），学生评分上限是 25,200 s；
   - `full_result_window` 的检查用的是**上限值**，不是实际耗时；
   - 按现在的上限，生成 job 必须在约 2026-10-21 10:40 UTC（03:40 PDT）之前派发，否则窗口检查不通过。之后的学生 job 也要各自放进 05 UTC 之前；
   - **请在 A2-lite 中按 P010 实际的评分耗时设定较小、但有依据的 score_seconds**，不要直接用最大值。
[Private current balance paragraph omitted; original bytes/hash retained locally.]
3. **复用部分没有重读**：P009/P010 中未改动的文件，这次只核对了 sha 与原来一致、确认已在生产中使用过，没有逐行重读。新文件我是逐行审阅的，重点看了数据流、remote 路径和循环边界。
4. **测试情况**：本地没有 GPU 和 vLLM，以上结论都来自代码阅读和 mock 测试；Codex 报告的 20 项新检查都已通过。
