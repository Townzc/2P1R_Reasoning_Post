# 正式 A/D：数值 A2-lite + §7.4 委托处置

- **审计方 / 决定方**：Claude，委托授权（负责人在对话中授权今晚的 P011 审批）。负责人已在 11:40 UTC 前后收到 §7.4 通知，目前尚未答复；以本报告的 git 提交时间为准
- **请求**：`p011-long-A-D-complete-path-CR-A1-A2-lite-r1`
- **scope**：`p011-long-A-D-complete-path-CR-A1-A2-lite`
- **target_commit**：`99508f316768237185479fbfa660850ea4ed5c0f`（在 ccb5dfc8 上核对）

## 结论：PASS-WITH-CONDITIONS（只批准缩减后的冒烟，见第二节）

| 字段 | 值 |
|---|---|
| decision | `PASS-WITH-CONDITIONS` |
| spec_sha256 | `f0e9274459b17b25a9754b863ce88d4ecee5c35fe9804e3ffdd86f8ce92c522b` |
| jobs_sha256 | `5fb72cdbfe1705877dfefcd72932e412eec9d6ee823d58f67350d46d9cfafba6`（32 个配置；已重算） |
| source_files | 44 个，与已接受的 83d5d8c9 相同 |
| budget_owner_decision_sha256 | `364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f` |
| prior_failed_C1_sha256 | `cef4180dfae70eb1a8713bc29e3e8b90a4d30f866e1b08ee65b1ec555b8d705f` |
| failed_attempt_bindings_sha256 | `698167fa6dddf11d64c6c1e7dafb1761c97c08a418e74cdafbfb87450b36b06f` |
| actual_input_directory / binding | `long_inputs_numeric_gold_r1` / `cee34dc05189b785fe92e4c6384f8afb28a6ec26d1e60871d8fdbba3ea70deb3` |
| measurement_exceptions | 0 |
| 代码检查的 9 个 flag | 全部 **true** |
| 另外 4 个 flag | `original32_to_formal512_and_processed_token_scaling_scope_accepted` **true**；`new_A_D7200_scoring_cap_with_frozen_per_row_rules_and_full_window_accepted` **true**；`plan7_4_mandatory_remaining_budget_disposition_explicitly_accepted` **true**（处置见第二节）；`fullparameter_actual_local_oracle_accepted_after_preentry_disposition` **true，但带条件 C2**（见第三节） |

## 一、数值核对

- **训练**：
  - B = 41,813,212，U = 654，seed 17，与冻结的 A7 输入一致。
  - 每次更新的计时按实测完整周期 × (正式更新的最大 processed token / 32,673) 外推。各格最大 processed token 在 76,032–77,961 之间，比例约 2.38。
  - 预检挑的是两条最长（≥ 15k token）的序列，所以每条序列的显存峰值已经被预检覆盖，这一点我接受。显存峰值的字节数没有记录，必须披露。
- **评测**：3,300 条，按 512 条一批共 7 批，每批计时取 32 条实测 × 16。
  - 这个线性外推没有校准：512 条并发能提高吞吐，但正式模型输出更长，两个方向的误差相反。
  - 我按 KV cache 粗算：1.5B 每 token 约 28.7 KB，3B 约 36.9 KB，H100 能容纳约 2M token；即使大量回答跑满 16k，也是抢占而不是 OOM。
  - 外推依据可以接受，**但不是上界**：超时就按硬计时失败，不重试。
- **评分上限 7,200 s**：E3 的 W = 107.35 s，按 10 倍、按规模、再乘 1.2 的情景估计为 1,328 s，远低于 7,200。评分只取 `</think>` 之后最后一个 `\boxed{}`，单对 8 s 超时和 worker 规则不变；部分失败照实记录，不补零。接受。
- **完整窗口**（collect 3,600 + oracle 3,600 + 评分 7,200 + 清理 5，加 worker）：已核对 `latest_dispatch` 的计算。截止时间为 10/22 05:00 UTC。
- **费率**：H100 3.95 + 4 × 0.0473 + 32 × 0.008 = 4.3952；96 GiB 时为 4.9072 ✓ reserve = 费率 × (startup + platform) / 3600 ✓

## 二、§7.4 委托处置

**事实**（Codex 的数字我已复核）：
- 按原设计，冒烟 3 臂 + 2 个基线，A 类预留 110.53 / 115。不可砍的 A1/A5/A6 无论选哪一臂都放不下。
- **时间**：L3 冒烟的 worker 约 27,064 s，现在派发也要到 19:30 UTC 之后才结束，而 L3 后续格最晚派发时间是 17:13–17:18 UTC，**选中 L3 已不可能**。只要等 L3 冒烟跑完再做选择，L15 后续格的派发截止（19:03 UTC）也会错过。
- 5 个冒烟 job 加上 B 续跑共 6 个，超过共享上限 4 个槽位。
- **D**：如果选中 L15，D1 + D2 = 26.52 > D 上限 25，D 按"两格都做或都不做"整体放不下；如果选中 F15，D = 11.21，放得下。

**处置**（不加上限、不跨类别、不释放预留、不改科学规则）：
1. **冒烟缩减为 S-L15、S-F15 和 1.5B 基线**，即 `long_A7_S-L15_s17_r1`、`long_A7_S-F15_s17_r1`、`long_baseline_S-L15_s17_r1`。**所有 S-L3 job 和 3B 基线都不派发**，理由是时间上不可行。报告中披露为偏离 §2"三臂冒烟"。§2 的门槛（EOS ≥ 70%、比基线低不超过 10pp、无技术失败）和选择规则（最高者；更便宜的臂相差 ≤ 3pp 时改选它）在两臂上原样执行。
2. 预留：26.08 + 15.63 + 12.17 = 53.88；加上工程预留 5.95，A 共 59.83 / 115。每次派发各自按 80% 规则检查，按上面的顺序都能通过。
3. **冒烟后**（按 §7.1 要求用实测费用重新预测）：
   - 后续格按 A1 → A5 → A6 → A4 → A3 → A2/A8 的顺序逐个按 80% 规则派发，放不下的就停。
   - 如果选中 L15，按悲观外推 A5 已经放不下。那时用实测费用重算，仍然放不下就如实报告"不可砍格因预算未完成"，并再次按 §7.4 通知负责人。
   - D 按选中臂的实测费用判断，两格都放得下才做。
4. 负责人如果决定加预算或允许挪用，以负责人的决定为准。本处置只是在现有上限之内能做的最好安排。

## 三、条件

- **C1**：每个 job 派发前都要做新鲜的费率、D1、共享 ≤ 4 槽位、未使用 fence 和完整窗口检查；派发时间不得晚于各自的 `latest_dispatch_utc`。
- **C2**：`long_A7_S-F15_s17_r1` **只有在** F15 预检本地 oracle 按 76093675 的批准完成并 **PASS**，且 Codex 公开其证明之后才能派发。如果失败或超时，F15 不进入正式阶段，冒烟只剩 L15。L15 和基线不受这一条影响。
- **C3**：学生选择由 Claude 按 §2 执行；在此之前，除上面 3 个 job 外，不派发任何后续格。
