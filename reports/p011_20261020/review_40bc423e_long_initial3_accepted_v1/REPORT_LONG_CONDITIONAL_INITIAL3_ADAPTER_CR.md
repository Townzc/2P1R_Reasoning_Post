# 正式 A/D：缩减后冒烟的条件适配器，源码 CR

- **审计方**：Claude。以本报告的 git 提交时间为准
- **请求**：`p011-long-A-D-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-long-A-D-complete-path-CR-A1-A2-lite`
- **source_appendix_scope**：`p011-long-conditional-initial3-adapter-CR`
- **target_commit**：`eb694d374ec7f780a10d1f14ea3e2a33994725db`（在 a593cbb0 上核对）

## 结论：PASS

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| spec_sha256 | `0007c1062f38d0bdf14c9b1011e8e13faa46120fa01e2b95fc46ff4e09ad57ca` |
| jobs_sha256 | `5777283599a0370a3cc3a073aadc1b684ffdd885752f9c01037da422d6789754`（已重算） |
| source_files | **48 个**：原 44 个逐项不变，新增 4 个（`long_conditional_path.py`、`modal_long_conditional.py`、`p011_long_conditional_io.py`、`analyze_p011_long_conditional_pair.py`）。HEAD 上逐个 sha 一致 |
| original_numeric_spec_sha256 | `f0e9274459b17b25a9754b863ce88d4ecee5c35fe9804e3ffdd86f8ce92c522b` |
| original_numeric_report_sha256 | `aac07df3b995480490ff2ba8844745849c06741efe03bf940f8460234d237f0b`；副本与我的原文件逐字节相同 |
| original_numeric_decision | `PASS-WITH-CONDITIONS`（保留原样，不改写成 PASS） |
| conditional_evidence_files | 3 个，sha 已重算：原 SPEC `f0e92744…`、我的处置报告 `aac07df3…`、F15 证明 `b2b639c1…` |
| initial_allowed_jobs | `long_A7_S-L15_s17_r1`、`long_A7_S-F15_s17_r1`、`long_baseline_S-L15_s17_r1` |
| 其余绑定 | budget_owner `364aaf6c…`；prior_failed_C1 `cef4180d…`；failed_attempt_bindings `698167fa…`；输入目录 `long_inputs_numeric_gold_r1` / `cee34dc0…`；measurement_exceptions 0 |
| 18 个 flag | **全部 true** |

## 逐项

- **SPEC**：只有 3 个 job，每一个都与已审数值 SPEC 中的原 job 在规范化 JSON 后完全相等；没有任何 L3 job，也没有后续格 ✓ 新增字段只有 `conditional_evidence_files`、`initial_allowed_jobs` 和 `original_numeric_decision` ✓
- **`long_conditional_path.py`**（与 `long_current_path.py` 对比）：
  - `conditional_evidence` 固定检查三个证据文件的 sha，要求 job 与原 SPEC 相同、原 44 个源码不变、不含 L3。它还要求 F15 证明满足：complete、engineering_only、未评分，job sha 等于 `08f754e1…`，完成时间早于 12:50:18 截止，2 次更新，65,082 个 target ✓
  - `reviewed` 新增绑定和 9 个 flag ✓
  - `selection`：L3 一律拒绝；初始 3 个 job 不需要选择；后续格要求新的 scope `p011-long-reduced-smoke-student-selection`，并要求绑定处置报告 sha、通过两个冒烟加一个基线的 A3、明确决定后续顺序和预算可行性，D 格还要求"两格都做或都不做"已被接受 ✓
  - worker 内"非初始 job 必须有选择"的判断改为按 logical ID，没有放宽 ✓
  - `published` 和 modal 镜像都会带上证据文件，所以远端也会重新验证 ✓
- **IO / analyze**：只改了 import；upload 时加了一次 `selection()` 调用，对初始 3 个 job 返回 None ✓
- **科学部分、计时、费率、窗口、预算检查**：都未改动 ✓
- **F15 证明**：本地审计 CLI 68434 EXIT0，证明于 12:06:27 完成，早于截止时间；完整状态 18.5 GB，1,543,714,304 个可训练参数，2 次更新。只运行了这一次批准的调用 ✓
- **测试**：9 项在本机全部 OK。

## 不变

派发前仍要逐个做新鲜的费率、D1、≤ 4 槽位、未使用 fence 和完整窗口检查（C1），并且不晚于各自的 `latest_dispatch_utc`。B 续跑正在运行，占用 1 个槽位，所以 3 个初始 job 加上它正好 4 个。后续格必须等 Claude 按 §2 对缩减后的冒烟做出选择。
