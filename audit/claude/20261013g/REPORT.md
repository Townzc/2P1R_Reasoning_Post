# Claude 审计第十四轮：CPU 审计超时与续跑代码 @ `4c44d8cc`

- 范围：`bce2daca..4c44d8cc`（`d7ae7ade`、`143e47f8`、`9acb1137`、`4c44d8cc`），包括 `experiments/sft_allocation_acquisition/{audit_continuation,modal_audit_continuation}.py`、`tests/test_audit_continuation.py`、`P007B_FINAL_CPU_AUDIT_{INTERRUPTED,CONTINUATION_ADMISSION,CONTINUATION_STARTED}.json`。
- 事实：原 CPU 审计在 3,300 秒时被计时器终止（exit 124），14 个标签中完成了 10 个。续跑只对剩下的 4 个（depth_p4_s17、depth_p4_s23 和两个旧先导）做完整核验，另外新增预留 $3（合计 $369.50）。截至此 commit，续跑仍在进行，没有结果。

## 结论

| 对象 | 结论 |
| --- | --- |
| 续跑代码 | **PASS-WITH-NOTES**（C14-1、C14-2）。8 个测试通过。 |
| 处理流程 | **接受**。先完整对账原审计的 ledger 和部分证据，再发布准入文件；原 claim 不重置，失败记录保留；本地对账第一次因为 4MB 上限误拒合法文件，第二次在 12MB 上限下完成，两次记录都保留。 |

## 代码审查

- `validate_partition`：14 个标签的名单必须与 admission 推导出来的完全一致；已完成和剩余的标签必须互不相交，且合起来覆盖全部；只允许父任务已经停止且未完成的情况；不得延长绝对截止时间；只能有一个 $3 的槽位。都正确。
- `verify_carried`：沿用的 10 个结果，以父任务中证明文件的 SHA 和字节数为准（钉在 binding 里），并逐一核对 terminal、manifest digest、`result.json`，以及每个 checkpoint 的 manifest 与 `state.pt` 的 SHA 和字节数。**不重新读取 state.pt 的全部字节**（见 C14-1）。
- `verify_remaining`：保留原审计的语义：`verify()` 对 manifest 中每个文件做大小和 SHA 校验，并加载每个 checkpoint。
- `main`：发布前检查本地 HEAD 是否等于远端分支、源码字节是否与 HEAD 一致、父任务是否已停止且没有容器、新 campaign 是否还没有记录、证据目录是否为空，所以不会重复派发。都正确。

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| C14-1 | 低（表述） | 沿用的 10 个标签不会重新读取 state.pt 的全部字节，依靠的是父任务当时的完整检查，加上证明文件 SHA 的绑定。 | 合并后的审计结论应写成"10 个由原审计完整核验、4 个由续跑完整核验"，不要写成"14 个在同一次运行中核验"。另外，8 个学生终点 state.pt 的 SHA 我已经在用户电脑上独立核对过（第九、十一、十二轮），可以作为旁证。 |
| C14-2 | 低（运维） | 超时是由 `threading.Timer` 触发 `os._exit(124)` 实现的，会绕过 `except` 分支，因此不会写入 `failure.json`，也不会执行 `guard.finish`。原审计就是这样结束的，所以 claim 留在未完成状态，需要人工对账。 | 当前运行不要修改。以后可以在硬退出之前留出 60–120 秒的"软截止"：先写失败记录，再退出。 |
| C14-3 | 中（日程） | 原审计 3,300 秒只完成了 10/14。剩下 4 个里有两个完整的学生（各 9 个 checkpoint，每个约 222MB），续跑同样只有 3,300 秒、2 个读取线程。时间应该够，但不确定。按照现在的门控，图和事实页要等 14 个标签全部完成才会生成，而中期材料的截止是 21:00 PDT。 | 这是 owner 的决定：建议事先写好"如果续跑也超时"的方案，例如图和事实页照常生成，但注明 CPU 审计 X/14 完成，其余由独立的本地核验覆盖。不要临近截止时再临时放宽门控。 |

等待：续跑结果、最终 summary、图和事实页。
