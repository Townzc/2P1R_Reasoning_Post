# 主运行时代码预审（请求 `p008-main-runtime-preflight-r1`）@ `c9f80579`：**PASS-WITH-NOTES**

- reviewed_commit：`c9f805796df99f24a3f07840d0eb107157302579`。范围只是代码：`procurement.py`、`pool_runtime.py`、`student_plans.py`、`schedule.py`、`student_runtime.py`、`sensitivity.py`、`main_binding.py`、`modal_main.py`。数值准入（ADMISSION、分支、计时器、输入）需要在 Phase 0 之后另行过门，本 PASS 不能单独准入任何模型调用。
- 本地测试：procurement、plans、student_runtime、sensitivity、bundle、main_binding 共 35/35 通过。

## 已确认正确的部分

1. **不预知未来（no lookahead）。** `Wallet.propose` 只调用 `Policy.propose`（只依赖合法历史）和已知 prompt 长度，不接触缓存。`pending_union` 只收集已提交（begin）的动作。`settle` 在提交之后才读取缓存，并检查行的顺序和身份（`d{draw}::pid::attempt`）、prompt 长度、0 < completion ≤ 1024。
2. **每个虚拟策略自己付费。** charge = 题价 × 新题数 + Σ(prompt + completion)，与缓存是谁生成的无关；charge 不超过预留（16 × 1024 最坏情况加上 prompt 和题价），也不超过上限。`replay` 逐事件比对 intent 和 done，最后还要求合法停止（`propose() is None`）。
3. **去重语境与策略无关。** `Policy.propose` 每个动作中每题只有一次尝试；`pending_union` 要求第 k−1 次尝试已在缓存中才能生成第 k 次。任何消费第 k 次尝试的策略都已经消费过第 1 到 k−1 次，所以同一题的"已接受集合"对所有策略都相同，usable 判定与策略无关。我检查了这一点，没有问题。
4. **训练计划。** 每个 T 档在两个 draw 的所有格上联合向下搜索，最多下调 0.1%，失败就整体停下，不会对单格做修补。`validate_plan` 检查 LR = `lrs(U)`、seed 17、曝光极差 ≤ 1（允许 0）、整答案剂量精确、无 padding，并且计划哈希必须与 COMMON_PLAN_GATE 一致。`rt.train` 是通用实现，不含写死的 256；写死 256 的 `frozen_main_lrs` 不会被 P008 调用。
5. **次要解析器 v2。** 只修复 E1（百分号）和 E2（空陈述 + 显式框内答案），不接触金标准，标记为 `secondary_only`，不进入采购、训练或主终点。
6. **派发保护。** 本地 HEAD 必须等于远端分支，源码字节必须一致；已有 claim、intent 或 terminal 时不派发；已提交但还没有 terminal 的调用也算占用一个槽；最多 4 个；pool 未结束前不派发学生。每个学生都要求：两个 pool 的 terminal 都已完成、通过联合计划门，并且本 draw 的 G1 结论绑定到同一个本地 oracle 的哈希。

## 发现

| ID | 严重度 | 内容 | 建议 |
| --- | --- | --- | --- |
| M1 | **中高（进度）** | `validate_binding` 要求 `phase0.four_gpu_verified is True`，否则**任何**主运行都不能派发，包括 pool。如果 Phase 0 只是没凑齐 4 卡（这正是 G0-1 修订允许出现的情况），整个 P008 就会停住，而协议里没有写降级路径。 | 在任何主结果出来之前，预先写好一条降级规则：如果 4 卡未验证，就按 P007B 已验证过的 **2 卡并发**派发，并用 2 卡的时间预测重新执行 `select_branch`（这样可能自动落到更小的分支）。规则只由工程证据触发。 |
| M2 | 中（预测） | pool 是按"轮"推进的：每一轮，8 个钱包各提交一个 16 槽动作，取缺失项的并集生成，单轮耗时由最长的那条（最多 1024 token）决定。后期往往只剩 breadth p0 8× 一个钱包还在活动，每轮只有十几条。我的粗估是：8× 下每个 draw 约 260 轮，乘以每轮最长生成时间（eager 模式下约 15 秒）≈ 1 小时以上。Phase 0 测的是满 32 条的批次，直接外推会低估时间。 | 时间预测用"轮数 × 每轮最长长度的 p95 延迟"，不用"条数 ÷ 吞吐"。可选的优化是去掉 `enforce_eager`（启用 CUDA graph）并放大 `max_num_seqs`；因为种子是逐请求的，不影响采样分布。但这会改动 pool 源码，需要我复核 diff。 |
| M3 | 低 | 2048 更新的学生只在最后一步保存 checkpoint（约 1 小时训练 + 1 小时评测，3 小时计时器）。中途失败的话，没有可供取证的状态。 | 可以加一个 1024 步的 checkpoint（只用于取证，不做续跑）。不改也可以接受。 |
| M4 | 低 | 物理尝试数到达 16,384 的上限时会抛出 RuntimeError，该 draw 作废。按 P007B 的消耗率，我估计 8× 下每个 draw 约 7–8k 次，余量足够。 | 不改。在 G1 中报告实际次数。 |

**下一步：** Phase 0 收尾和分支冻结；G1-D1。届时我会从导出到用户电脑的原始 token 独立重新评分，并独立重放 8 个钱包的计费。
