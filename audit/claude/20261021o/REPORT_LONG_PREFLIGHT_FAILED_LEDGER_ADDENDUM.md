# 长序列三臂工程预检：失败账本窄补充 CR

- **审计方**：Claude，2026-10-21 10:15 UTC 前后（负责人夜间全权审核期间）
- **请求**：`p011-long-three-arm-engineering-preflight-CR-A1-A2-lite-r1`
- **final scope**：`p011-long-three-arm-engineering-preflight-CR-A1-A2-lite`
- **target_commit**：`38942d3a9380030d3ad885dfe46b6cfb377aad00`（在 HEAD `e9a9250b` 上核对；勘误 `LONG_PREFLIGHT_LEDGER_BINDING_ERRATUM.md` 已读）

## 结论：PASS（仍只授权这 3 个工程调用，各一次）

| 字段 | 值 |
|---|---|
| decision | `PASS` |
| original_plan_commit | `e0dee182972f9910b707fac68800dcb5a3aff2d3` |
| spec_sha256 | `eb88670f66ca6ebdfa080d9e5b39dc9654e00604be2cf398df31cb4f7d21d7a6`（文件 sha 已重算） |
| source_files | **37 个**：SOURCE_BINDING、SPEC、REVIEW_REQUIREMENTS.binding 三处完全一致，HEAD 上逐个 sha 一致。原 33 个未变；新增 4 个：`experiments/p011/failed_attempt_ledger.py`、`experiments/p011/long_preflight/failed_ledger_path.py`、`experiments/p011/long_preflight/modal_failed_ledger_entry.py`、`scripts/p011_long_preflight_failed_ledger_io.py`。REVIEW_REQUIREMENTS 顶层继承的 33 项映射只是历史字段，不作为本次绑定 |
| jobs_sha256 | `d87c67f03a65f7d0d76f6b90bf970414b9ac69a205bce57a824bb3fad9539a29`（与原 SPEC 的 jobs 逐对象相同） |
| owner_decision_sha256 | `364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f` |
| measurement_exceptions | 3 |
| formal_repair_review_sha256 | `7c67c4d4c5afd2a874f1bd3dfc3e6654f369decca35ccede67d53da65bf3ff40` |
| failed_attempt_bindings_sha256 | `698167fa6dddf11d64c6c1e7dafb1761c97c08a418e74cdafbfb87450b36b06f`（digest 已重算） |
| original_preflight_A1_A2_report_sha256 | `2dd1dc459fb00a0a52190b489de7b2d6db37e092130ba85cfb3a608ee60735c1`（即我在 20261021n 的报告） |
| complete_source_closure_accepted | **true** |
| actual_input_A1_accepted | **true** |
| formal_R1_R3_source_CR_accepted | **true** |
| engineering_subset_of_formal_path_accepted | **true** |
| all_three_reserves_at_most6_accepted | **true** |
| full_state_export_join_and_original_engine_accepted | **true** |
| original_failed_parent_retained | **true** |
| current_owner_budget_scope_and_full_window_accepted | **true** |
| no_scientific_result_or_A3_A5_claim | **true** |
| failed_terminal_ledger_and_original_reservations_accepted | **true** |
| original_three_preflight_jobs_unchanged | **true** |

## 核对

- **问题本身**：原共享账本 `c1_outer.ledger` 对任何有 PROVIDER_STOPPED0 的目录都要读 RESULT.json；B 生成失败后正确地没有 RESULT，所以会让预检派发卡住。这是派发前发现的本地不兼容，没有付费调用受影响 ✓
- **`failed_attempt_ledger.ledger`**（逐行审阅）：
  - 只有 SPEC 中明确绑定的失败尝试才能走"失败终态"分支；该分支要求**没有** RESULT，8 个文件（intent / submitted / failure / provider / 3 个 named fence / preservation）逐个 sha 一致、不是绝对路径、没有 `..`、不是 symlink；
  - 并且要求 terminal 的 status = failed、logical_id 和 app_id 一致、`automatic_retry_allowed is False`、provider 观测时间晚于失败时间、intent 中的类别和 reserve（B, 3.01）与绑定一致、preservation 是 stable 且不是 scientific completion，3 个 named fence 的 key 和 value 与 intent / terminal / claim 交叉一致；
  - 未绑定且有 STOPPED0 的目录仍然必须有 status = completed 的 RESULT，并且 app_id 和时间一致，比原来更严 ✓
  - 没有 SUBMITTED 的目录仍按"待定"占槽；绑定了却找不到的失败尝试会报错 ✓
  - 失败尝试的 reserve 继续计入类别合计（B 3.01）。`shared.accounting` 对有 saved_provider 的记录按 stopped 处理，不额外占槽；这与原来对已完成调用的处理相同 ✓ C1 r1 仍由 `parent.records_with_failed_parent` 原逻辑处理，C1 两次的 6.38 保留 ✓
  - 我还核对了 C1 r2 公开的 ORIGINAL_RESULT：有 `status: completed`、app_id 和 finished_epoch，所以新的更严检查不会误挡它 ✓
- **`remote_fences`**：只读 B 失败父尝试的 3 个已保存 key，并与保存的 value 比对；不重新轮询已关闭的 app，也不枚举整个账本 ✓
- **交叉核对**：B 公开保存包中私有 ADMISSION 的原始 sha `4cd5aece…` 等于绑定中 intent 的 sha；FAILURE.json 的 sha `54e1b112…` 等于绑定中 failure 的 sha ✓
- **三个包装文件**：我自己做了 diff。`failed_ledger_path` 与已审的 `path` 相比只有 20 行改动（SPEC 路径、两项新绑定、两个新 flag、换用新账本并加读失败 fence）；modal entry 和 IO 脚本都只改了 import ✓ 预算、窗口、reserve 公式、worker 主体都没有改。
- **测试**：`tests/test_p011_failed_attempt_ledger.py` 9 项在本机全部 OK。
- **时间**：最晚派发时间仍是 10/22 02:34 UTC ✓

## 注意

1. 派发入口仍要求：新鲜的费率和 D1（1 小时内）、4 槽检查、三个工程预检累计 reserve ≤ 6、各自窗口放得进截止时间。
2. 本 PASS 不涉及 B 的处置。B 的处置见同目录 `DECISION_B_FAILURE_NATIVE_EOS_UNMAPPED.md`。
