# Claude 审计：固定 token 计价新方案 @ `6c127d66`（第三轮）

- 范围：`docs/experiments/P007B_token_tariff_revision.md`、`reports/p007_audit/token_tariff_v1/`、`P007B_TOKEN_RETIREMENT.json`、`P007B_TOKEN_STUDENT_ADMISSION.json`、`experiments/sft_allocation_acquisition/{token_contract,token_student_runtime}.py`、`scripts/{audit_token_prefix_packet,audit_token_student,summarize_token_students}.py`、`tests/test_token_tariff.py`。
- 复现：检出 `6c127d66` 后，在仓库根目录运行 `python3 <本分支>/audit/claude/20261012c/token_audit.py reports/p007_audit/token_tariff_v1`。该脚本不调用 `token_contract`，独立重放。

## 结论

| 对象 | 结论 |
| --- | --- |
| 计价前缀与选中的数据 | **PASS** |
| 学生端代码与汇总代码 | **PASS-WITH-NOTES**（K1） |
| 用于回答"题价是否改变 breadth/depth 排序"的科学设计 | **未解决：T3（高），启动前需要 owner 决定** |

## 实际重算的内容

- manifest 中 7 个文件的 SHA-256 全部匹配；`audit_token_prefix_packet.py` 可以运行；`tests.test_token_tariff` 5/5 通过。
- 独立重放四格：批次数、尝试数、可用答案数、覆盖题数、花费与 `prefix_simulation.json` 完全一致（32/512/408、33/528/474、7/112/91、16/256/230；剩余 6.14%、6.88%、12.26%、10.90%）。选中的候选 ID 序列逐条一致。
- 轨迹行与此前已审计的 `policy_all_v1/attempts.jsonl` 对照：usable、批次号、token 数（文本 token + EOS）0 处不一致。
- prompt 长度与运行时写下的 `prompt_manifest.json`（本地保留的 4 个导出）对照：4,096 条 0 处不一致。
- 训练计划：8 个计划都是 524,287 个 target、256 步；每行曝光次数 breadth_p0 4–5、depth_p0 3–4、depth_p4 8–9、**breadth_p4 20–21**。

## 发现

| ID | 严重度 | 事实 | 建议 |
| --- | --- | --- | --- |
| T3 | **高（未解决）** | 新方案的 limitations 和设计文档都没有提到重复剂量问题。breadth_p4 只有 91 条答案，每条训练约 20.75 次；depth_p4 约 8 次；p0 两格约 4 次。P007 主实验中，13.6 次曝光就带来约 10.8pp 的损失。 | 价格交互项会混入强烈的重复效应。owner 的选择在 T3 发出之前就已作出，所以请重新确认。最低限度：把每行曝光次数写进 limitations 和结果表，结论限定为"固定训练算力（524,287 target）下"。更好的做法：给 p4 两格加一组按固定曝光训练的学生（例如每行约 4 次曝光，target 数按语料大小缩小，评测相同），这样可以把"数据多少"和"重复多少"分开。这只是改变剂量，不需要新的教师生成。 |
| T2 | 中（部分处理） | 结果汇总写了"common budget cap, not exactly equal realized spending"。 | 请把具体数字（剩余 6.1%–12.3%）写出来，并说明超过了原设计 5% 的阈值。 |
| K1 | 低 | `token_contract.TARGETS` 已经是一个常量，但 `token_student_runtime.py`（预检与运行检查）和 `audit_token_student.py` 中仍然直接写着 524287。 | 改为引用常量；目前取值一致，不影响本次运行。 |

## 未检查

新学生尚未运行；`modal_token_student_runner.py` 的调度逻辑只粗读了一遍；保留的两个原始学生的结果不在本轮范围内。
