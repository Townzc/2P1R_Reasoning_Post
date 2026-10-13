# 学生入口 + 最终 CPU 审计代码预审 @ `f944723e` / `33f964bb`：均为 **PASS-WITH-NOTES**

- 请求：`p008-student-runtime-preflight-r1`（target `f944723ee58e99483a5c5c4e7f41485a2d9fde9f`）和 `p008-final-cpu-code-preflight-r1`（target `33f964bbeda4d67de8caac72691a8dd7f01ff4f0`）。我读的是 `e3d9b196`，包含这两个 target。
- 范围只是代码。学生派发仍需要：两个 pool 的真实 terminal、我的 G1-D1 / G1-D2、联合计划门，以及数值规格。两个 pool 正在运行，本审查不影响它们。

## 学生入口（`modal_students.py`、`student_binding.py`）

- **原 pool 运行时和准入文件没有改动**：新入口单独成文件，去掉了教师分支，只接受 main、bridge、base 三种角色。HF 训练、评测、停止、评分这些原语，仍然调用原来的 `student_runtime`（含 1024 步的取证 checkpoint）。
- `validate_student_binding` 在 `validate_binding` 之外还要求：联合计划门的 SHA 与 spec 一致；两个 pool 的 terminal 都为 completed，并在 worker 内与 claims 逐一核对；G1 绑定固定的报告 SHA 和 target commit、本格的 `input_sha256`，以及联合计划门的 SHA；pool 准入的来源 SHA 一致。
- 本地派发前会检查：当前时间 + max_seconds + 700 秒不晚于全局截止时间，否则不派发（标 pending，不缩减剂量）。其余保护与之前相同：源码必须已发布，已有 claim 不派发，未完成的调用也算占用一个槽，最多 4 卡，pool 未结束不派发学生。
- **S1（信息，排程）：** 2048 步的学生，max_seconds 是 9,560 秒，加 700 秒，所以**最晚必须在约 16:09 PDT 启动**；1× 学生 6,001 秒，最晚约 17:08 PDT 启动。请把这两个时间点写进排程表。如果 D2 的 8× 主格排不进去，按协议标 pending。

## 最终 CPU 审计（`audit_binding.py`、`audit_bundle.py`、`modal_audit.py`）

- 覆盖的名单：21 个标签（2 个 pool + 18 个学生 + base），要求每个都是 completed、资源已释放，并且本地 oracle 绑定到原始 artifact 的 digest。
- `verify_packed_run`：逐个文件哈希比对压缩包的 manifest 和原始 envelope；单独复制并加载 state（256 步的学生读 1 个，2048 步的学生读 1024 和 2048 两个），检查 step、cursor、schedule、`lrs(U)`、阶段性剂量、adapter 和 optimizer 是否完整且数值有限、RNG 的四个分量；state 的 SHA 必须等于独立 oracle 中记录的值；每个学生 1,319 道题的布尔值之和必须等于正确数。
- 范围表述准确："绑定先前的独立 raw/dose oracle，不重新评分，也不逐个重读原始文件"（与 C14-1 一致）。
- 单次运行、不重放：每个标签的 unit 和 done 都写入不可覆盖的 claim；超时会写 `failure.json`，并保留已完成的部分证明，这正是 C14-2 建议的软截止。
- **S2（低）：** 软截止只比硬退出早 30 秒，而 `check()` 只在 8MB 块之间和每个 state 加载前后被调用。加载一个 222MB 的 state 并做有限性检查，可能超过 30 秒，从而被硬退出打断，这次的失败就不会写入记录。建议把余量放宽到约 120 秒（只是一个常数的改动）。
- **S3（信息）：** 上次 P007B 的 CPU 审计在 3,300 秒内只完成了 10/14。这次需要读取约 26 个 state，约 5.8GB，用 2 个读取线程。请在准入前用 Phase 0 的 I/O 测量（以及 P007B 的实际耗时）估计一下时间。如果不够，提前写好"超时后只续核剩余标签"的路径（P007B 时已经有过先例）。

## 测试

在我的环境里，`test_p008_student_binding`、`test_p008_audit_binding` 和 `test_p008_audit_bundle` 中有 7 项因为缺少 torch 而报 `ModuleNotFoundError`，属于环境问题；其余全部通过。Codex 报告在完整环境中 21 + 25 项通过。

**下一步：** 两个 pool 完成后进行 G1。我会在用户电脑上从原始 token 独立重新评分所有教师输出，并自己写一份重放程序，核对 8 个钱包的计费。
