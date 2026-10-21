# 负责人决定：当前余额口径、取消 $48 保护、批准 A/D GPU 预检

- **记录方**：Claude
- **负责人答复时间**：2026-10-20 23:02 PDT（2026-10-21 06:02 UTC），在 claude.ai 对话中直接回复
[Private current balance paragraph omitted; original bytes/hash retained locally.]

**负责人原话**：

[Private current balance paragraph omitted; original bytes/hash retained locally.]

## 我对决定的记录与解释

以原话为准；解释部分如有歧义，按更保守的方向执行。

[Private current balance paragraph omitted; original bytes/hash retained locally.]
[Private current balance paragraph omitted; original bytes/hash retained locally.]
   - 预算新鲜度规则不变：派发时需要 ≤ 1 小时内的预算观测。负责人的这次陈述作为当前余额的依据；后续出现任何矛盾的观测，都会阻止派发。
2. **取消 $48 保护**："全部可用不用留"。此后 `protected_usd` 改为 0，不再要求派发后余额 ≥ 48。
3. **"不能乱花"**：
   - **各类别子上限保持不变**：A 115、B 20、C 12、D 25、应急 8，合计 180。
   - 被释放的 48 **不自动分配给任何类别**；如需使用，必须由负责人另行决定。
   - 80% 预测规则、不自动重试、类别之间不得挪用，全部保持不变。
4. **"A 网格能跑就跑，跑不了就等中期报告交了批经费再说"**：
   - 冒烟结束后，用实测费用重新预测 A 的剩余格子和 D。
   - 如果所选学生的 A 剩余格子在 A 类上限内跑得完，就照常执行。
   - 如果跑不完，就**不再启动新的 A 格**，A 的剩余部分等期中报告提交、经费获批之后再做。原计划 §7.3 的削减顺序，也要经负责人确认后才使用。
   - Claude 会立即报告，不会自行突破上限。
5. **批准 A/D GPU 预检付费例外**：
   - **只用于查错和计时**，不产出任何科学结果，不进入 A3/A5。预检产物**不能**冒充冒烟或任何格子的结果。
   - 每个冒烟臂（S-L15、S-F15、S-L3）各跑一个预检 job，每个 job 只能执行一次，不重试。每个 job 的内容：
     - 用该臂实际的模型、精度和确定性设置；
     - 用最长的约 2 条训练序列（接近 16k）跑 2 次 update；
     - 完整执行终态 state 保存和校验（包含 R2 的修复）、BF16 导出、子进程退出；
     - 然后用 vLLM 加载导出的模型，并且必须使用修复后的引擎配置（R3：max_num_seqs ≥ 256），生成一组有代表性的请求，用来实测解码吞吐。
   - **费用**：负责人批准的是"约 $5"。三个 job 的 reserve 合计不得超过 **$6**，预期实际花费约 $3–5，从 A 类中支出。预算新鲜度、账本、4 槽并发、STOPPED 等检查全部照旧。
   - **前提**：预检要在 R1–R3 修复的源码 CR 通过后运行，代码路径要与正式路径相同，或经 CR 认可只是正式路径的子集。预检本身仍需提交简短的 CR 和 A2-lite。
   - **用途**：实测的单次 update 时长、峰值显存、导出时长、vLLM 启动时间和解码吞吐，作为正式 A/D 的 A2-lite 计时依据。
   - 正式 A/D 的 `measurement_exceptions` 仍为 0，因为它们的计时依据来自这次已批准的预检实测。
