# G0 范围修订（G0-1 采纳方案 a）@ `610fde47`：**PASS**

- 复核范围：只看 `phase0_runtime.gpu_probe` 的两个超时分支、`scripts/audit_p008_phase0.py` 中的并发分类、`tests/test_p008_concurrency.py` 和协议里那一句话。原 G0（`f996621d`，`722735e2`）的其余结论不变。
- reviewed_commit：`610fde47e0b0d14b1de459e7a627ea7c89072843`。

## 核验结果

- `phase0_barrier_v2/SOURCE_BUNDLE.json` 与 G0 版本相比，**只有** `experiments/sft_allocation_p008/phase0_runtime.py` 变了（新 SHA `3f76fad5…1674`），其余 18 个源码文件的哈希不变；19 个文件的哈希都与工作区一致。`modal_phase0.py`、`contract.py` 和 `PHASE0_ADMISSION.json` 没有改动，调用量、计时器和预算也都没变。
- 超时分支：等待就绪超时，或等待 ack 超时，都写入 `status=concurrency_not_achieved` 和原因，然后返回，原有的教师 / smoke 调用继续执行，不会新增调用。payload 损坏、身份重复、UUID 少于 4 个，仍然直接失败。
- 审计脚本：只有当 4 个角色全部为 `four_gpu_verified`、有 4 个不同的 UUID、并且重叠时间 > 0 时，才判定 `four_gpu_verified=True`；输出中带有 `main_dispatch_requires_four_gpu_verified=True`。三种状态各自的字段一致性都有断言。
- 本地测试：`tests.test_p008_concurrency` 加上 `tests.test_p008_contract`，14/14 通过。
- 边界情况（检查过，没有问题）：如果某个角色晚到，它会看到其余三个都已就绪，于是去校验 payload 并写 ack，但其他角色已经超时离开，它最终以 `ack_timeout` 结束，最多多等 180 秒，仍在自身计时器之内。

## 关于 G0-2 的措辞

接受 Codex 收窄后的说法：精确子集和与长度有关，不是均匀抽样。所以报告写成"给定库存和曝光的条件联合效应"，不写成"多样性的因果效应"。

**结论：** 修订后的 Phase 0 可以上传并派发。主运行时代码（`e2e9a294`、`fb92bef7`）和 v2 解析器仍是单独的待审项，本 PASS 不覆盖它们。
