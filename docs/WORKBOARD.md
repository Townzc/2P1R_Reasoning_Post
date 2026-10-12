# P007 工作总表

所有时间使用 **America/Los_Angeles（PDT，UTC−7）**。这是团队进度与决策入口；实验原始证据仍在结果文件、RUN_LOG 和审计包中。时间来自提交、回执或 GitHub 事件；仅知道读取时间时写“收录”，不假定那是实际发生时间。

## 当前状态

| 工作 | 负责人 | 状态 | 下一步 |
|---|---|---|---|
| 原 P007 四组实验 | Codex；Claude 审计 | 已完成；Claude **PASS-WITH-NOTES**，仅限报告列明范围 | 保留 base 解析敏感性、曝光及评测污染限定 |
| P007A 教师供给先导 | Codex；Claude 审计 | 已完成；紧凑计数/成本表 **PASS** | 原始教师逐条评分仍未被 Claude 审计 |
| P007B 按真实时间计费的采购 | Codex | 四格本地核验完成；Claude 对零题价格记账 **PASS**、成本解释 **FAIL** | C-B1 已复现，不能将速度差直接归因于题价 |
| 首批两项学生 | Codex | 各256步训练完成；多解于14:53完成1,319题并释放GPU，本地核验通过969/1319；多题评测继续 | 完成后核验全部输出和检查点，再释放资源 |
| 后六项原学生 | Codex | **未启动，已明确撤销** | 保留旧账本；新方案使用独立 campaign |
| 统一 token 计价修订 | Codex 设计；研究者决策 | **研究者已批准；八个 CPU 计划及前缀核验通过；Claude前缀PASS、代码PASS-WITH-NOTES** | 见[冻结方案](experiments/P007B_token_tariff_revision.md)；输入20文件已上传并逐一读回核验；当前两项收尾后开始新对照 |
| 阅读材料 | GPT Pro | 分工已明确；本轮尚未收到可核验的 Pro 新交付 | 用户转交论文链接、关键证据和阅读结论后登记 |
| 独立审计与新增阅读 | Claude | 已收到固定版本审计及36–38号笔记链接 | 按新证据版本继续审计；旧结论不自动覆盖新文件 |

预算：总额$500，保护至少$50；修订后保守预留$366.50（撤销旧六项和审计$111，新八项和审计$147，净增$36），不是实际花费。最近可核验平台计量见[监控/实验日志](../reports/sft_allocation_midpoint_20261011/RUN_LOG.md)，计量有延迟，不是剩余余额。固定收尾截止：10月13日19:00 PDT；目标周二晚结果与内容冻结。

## 时间线（追加记录，保留更正历史）

| 时间（PDT） | 执行者／来源 | 做了什么、得到什么 | 状态与证据 |
|---|---|---|---|
| 2026.10.12 12:08 | Codex | 原四组八条训练与 base 完成核验，主任务资源释放 | [主实验收尾](../reports/sft_allocation_midpoint_20261011/MAIN_CLOSEOUT_20261012.json) |
| 2026.10.12 12:11 | Claude（GitHub 交付） | 提交 F1–F5 方法学意见；其中“排除3pp差异”和种子差异措辞随后更正 | [原评论](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6130876644)、[处理记录](audit/P007_REVIEW_DISPOSITION_20261012.md) |
| 2026.10.12 12:37 | Codex（发布） | 发布教师先导核验与四格成本采购冻结方案 | [80434781](https://github.com/Townzc/2P1R_Reasoning_Post/commit/80434781) |
| 2026.10.12 13:30 | Codex（发布） | 保存多题高题价格故障，明确192条已知输出、50秒重建收费和有限续作；旧输出不重放 | [044fb6d4](https://github.com/Townzc/2P1R_Reasoning_Post/commit/044fb6d4) |
| 2026.10.12 13:41 | Codex（发布） | 四格2,064条输出全部核验，八个原学生计划通过并发布 | [55be82e7](https://github.com/Townzc/2P1R_Reasoning_Post/commit/55be82e7)、[完整采购包](../reports/p007_audit/policy_all_v1/REVIEW_REQUEST.md) |
| 2026.10.12 13:44 | Claude（GitHub 交付） | 审计三个旧包：主实验 PASS-WITH-NOTES，先导紧凑表 PASS；零题价格记账 PASS／成本度量 FAIL，提出 C-B1 | [评论](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6132296156)、[固定审计报告 f02e214b](https://github.com/Townzc/2P1R_Reasoning_Post/blob/f02e214ba73550dfab4165b4f7fcb96431163b6e/audit/claude/20261012/REPORT.md) |
| 2026.10.12 13:45 | Codex（实际运行核验） | 两张 H100 上首批多题／多解学生真实训练，配置、源码、首更新核验一致 | [启动证据](../reports/sft_allocation_midpoint_20261011/P007B_STUDENTS_STARTED.json)；此时 Codex 尚未读取13:44的新审计 |
| 2026.10.12 14:04 | Claude（GitHub 交付） | 提交36–38号阅读笔记：数据受限扩展、评测误差、URIAL；注明剩余阅读任务未完成 | [阅读评论](https://github.com/Townzc/2P1R_Reasoning_Post/issues/12#issuecomment-6132588470)、[笔记提交](https://github.com/Townzc/Obsidian-Vault/commit/0314b091dea9ed70ea19c344a8238c908b989774)；不要登记成 Pro 的工作 |
| 2026.10.12 14:08（收录） | 研究者（本聊天） | 要求检查首批进展、估算八项耗时、读取 Claude 审计、异常及时调整，并建立共享工作总表 | 本表及本轮核查的直接需求；不公开私人聊天全文 |
| 2026.10.12 14:08–14:14 | Codex | 确认两项训练256步完成、评测仍进行；读取固定审计版本并复现低价31%吞吐差，发现高价方向相反 | [审计处理与修订建议](audit/P007_COST_METRIC_REVIEW_20261012.md)；先暂停未启动六项，不中断正常评测 |
| 2026.10.12 14:14–14:17 | Codex | 用保存输出构造统一 token 计价候选；原524,288精确完整回答计划在一格失败，统一调整为524,287后八个CPU计划通过 | 仅CPU方案，不是新模型实验。按长度选择共同剂量，没有查看学生准确率 |
| 2026.10.12 约14:17（整理记录） | Codex → 研究者 | 提交两种计价口径的决策问题：推荐原两项保留先导、统一口径另做八项；或者保留原时间口径完成八项 | **等待明确选择**；不把候选、建议或超时视为执行批准 |

| 2026.10.12 约14:21（收录） | 研究者（本聊天） | 明确选择“采用统一 token 计价”；原两项保留先导，改跑八项同口径比较 | 已批准，不再重复申请同一授权 |
| 2026.10.12 14:25 | Codex（实时对账） | 六项原学生及旧审计无任何claim/intent/unit，记录退休；已有两项继续运行 | [退休绑定](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_RETIREMENT.json) |
| 2026.10.12 14:26–14:29（准备） | Codex | 四格保存轨迹前缀复算，八个524287-target计划通过；补齐输入长度元数据，保留CPU失败检查记录，无新GPU工作 | [新方案](experiments/P007B_token_tariff_revision.md)、[执行准入](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json)；Claude尚未审计此新版本 |

| 2026.10.12 14:33–14:35 | Codex | 新方案普通推送6c127d66；20个输入文件19.27MB独立读回SHA全通过，28项测试与3类真实输入破坏检查通过 | [准备就绪](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_READY.json)；新GPU尚未提交，等待原两项正常收尾 |

| 2026.10.12 14:27／14:39（交付），14:43（读取） | Claude；Codex读取 | Claude第二、三轮审计分别检查36bfa8c5、6c127d66：新计价前缀与数据PASS，学生／汇总代码PASS-WITH-NOTES；提出T1复现脚本、T2剩余比例、T3重复曝光及K1常量意见 | [第二轮](https://github.com/Townzc/2P1R_Reasoning_Post/blob/df68e21ec962de04a6eddb0c24cca67696dabbaa/audit/claude/20261012b/REPORT.md)、[第三轮](https://github.com/Townzc/2P1R_Reasoning_Post/blob/7339a60a2c5726ed1be0a5f19fa22832813aa2d3/audit/claude/20261012c/REPORT.md)；Codex开始逐项处理，尚不把意见写成已解决 |
| 2026.10.12 14:43（收录） | 研究者（本聊天） | 要求汇总首批结果与费用，核验后直接推进已批准新八项，并在工作前后更新总表、查看新审计 | 首批仍在评测；不添加新实验组 |

| 2026.10.12 14:50–14:52 | Codex（审计修订完成） | 公开候选重建和八份计划重建脚本，全部哈希匹配；31项测试通过。接受余额与曝光披露，保留既定训练预算，不额外加组 | [处理记录](audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md)、[新审计包](../reports/p007_audit/token_tariff_v2/REVIEW_REQUEST.md)；新增文件待Claude审计 |

| 2026.10.12 14:53–14:54 | Codex（首个学生收尾） | 多解学生完成1,319题；实际app已停止、容器0，启动只读完整账本与检查点导出；多题继续评测 | 原评分待本地独立重算后报告；新八项尚未启动 |

| 2026.10.12 14:56–14:58 | Codex（首个学生核验完成） | 多解先导969/1,319（73.46%）；861文件和完整state SHA通过，256步／524,288 targets与全部原始评分独立一致；GPU已退出 | [核验证据](../reports/sft_allocation_midpoint_20261011/P007B_FIRST_PILOT_VERIFIED.json)、[Claude可审包](../reports/p007_audit/operational_depth_v1/manifest.json)；多题尚在评测，新八项准备就绪 |

## 维护规则

- 一行对应一个可核验的交付、故障、决定或阶段变化，避免写“正在思考”之类无法回溯的活动。
- 每行写执行者、时间来源、实际状态和证据。由 Codex 代录 Claude／Pro 的材料时标明来源；没有收到的交付写“待同步”。
- 实验细节进入 RUN_LOG；审计结论进入独立审计分支和处理记录；论文笔记进入 Papers 仓库。本表只链接，避免三份摘要互相漂移。
- 使用 Issue 讨论一个具体问题，使用本表看全局；讨论意见不自动变成预算或执行授权。
- 各方提交应先读取当前工作分支，采用普通提交／必要时 PR；不覆盖他人的记录，不强制推送。Claude 的审计文件保留在其独立分支；作者与维护者分开记录。
- 阶段完成更新一次。发生新风险、方案改变或需要研究者决策时立即更新。时间统一用 PDT，并在更正时保留原记录和更正来源。

共享工作流说明：[RESEARCH_WORKFLOW_ZH.md](RESEARCH_WORKFLOW_ZH.md)。
