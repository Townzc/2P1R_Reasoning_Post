# P007 工作总表

所有时间使用 **America/Los_Angeles（PDT，UTC−7）**。这是团队进度与决策入口；实验原始证据仍在结果文件、RUN_LOG 和审计包中。时间来自提交、回执或 GitHub 事件；仅知道读取时间时写“收录”，不假定那是实际发生时间。

## 当前状态

| 工作 | 负责人 | 状态 | 下一步 |
|---|---|---|---|
| 原 P007 四组实验 | Codex；Claude 审计 | 已完成；Claude **PASS-WITH-NOTES**，仅限报告列明范围 | 保留 base 解析敏感性、曝光及评测污染限定 |
| P007A 教师供给先导 | Codex；Claude 审计 | 已完成；紧凑计数/成本表 **PASS**；第五轮原始输出重评分 **PASS-WITH-NOTES** | 范围已扩展至教师原始输出；两个百分号解析差异不影响新token学生数据 |
| P007B 按真实时间计费的采购 | Codex | 四格本地核验完成；Claude 对零题价格记账 **PASS**、成本解释 **FAIL** | C-B1 已复现，不能将速度差直接归因于题价 |
| 首批两项学生 | Codex；Claude审计 | 两项完整核验完成：多题953/1319，多解969/1319；GPU均已退出；Claude结果PASS | 仅作为原时间计价先导，保留截断38/33条及其他限制 |
| 后六项原学生 | Codex | **未启动，已明确撤销** | 保留旧账本；新方案使用独立 campaign |
| 统一 token 计价修订 | Codex；Claude审计 | **8/8项本地完整核验：seed17零价963/950、高价927/952；seed23零价958/958、高价949/949（各/1319）；GPU全退出** | 原CPU总审计55分钟到限退出，正在对账部分核验；仅余CPU证据检查，随后发布全两种子汇总/确定性图表。首种子反转未被第二种子重复；Claude第十二轮已覆盖八项raw/终点SHA；最终CPU回执、汇总和实际图表仍待外审 |
| 阅读材料 | GPT Pro | 分工已明确；本轮尚未收到可核验的 Pro 新交付 | 用户转交论文链接、关键证据和阅读结论后登记 |
| 独立审计与新增阅读 | Claude | 已收到固定版本审计及36–38号笔记链接 | 按新证据版本继续审计；旧结论不自动覆盖新文件 |

预算：总额$500，保护至少$50；修订后保守预留$366.50（撤销旧六项和审计$111，新八项和审计$147，净增$36），不是实际花费。最近可核验平台计量见[监控/实验日志](../reports/sft_allocation_midpoint_20261011/RUN_LOG.md)，计量有延迟，不是剩余余额。实验固定收尾截止：10月13日19:00 PDT；研究者最新要求中期所需核验数据、图表与局限清单在10月13日21:00 PDT前齐备。保留更早的实验硬截止，给材料整理留出时间；长期扩展放到中期后。

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
| 2026.10.12 15:09–15:13 | Codex（第二项收尾准备） | 实时检查仅旧多题worker活动、新八项全部无claim；源码和20个输入哈希一致。多题随后完成1,319题，开始收尾核验 | 不以模型自报分数替代本地复算；旧多解已核验，不重复导出 |
| 2026.10.12 15:16 | Codex（旧先导全部核验／新队列启动前） | 多题953/1,319（72.25%）、多解969/1,319（73.46%），全部2,638输出与两个完整state通过；两app停止、workspace容器0；新队列前置核验门通过 | [先导收尾](../reports/sft_allocation_midpoint_20261011/P007B_OPERATIONAL_PILOTS_CLOSED.json)、[审计包](../reports/p007_audit/operational_pair_v1/manifest.json)；准备新八项首对，不混用旧结果 |
| 2026.10.12 15:18–15:21 | Codex（新对照实际启动） | 新首对各提交一次；两张H100硬件、发布源码、配置与首更新逐项匹配。快照多题至少6步、多解至少13步，尚无终点评测；其余六项未启动 | [真实启动证据](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENTS_STARTED.json)；未增加剂量／预留，稳定后30分钟巡检 |
| 2026.10.12 15:39–15:42（巡检开始） | Codex | 读取实际provider与更新回执；新首对均已提交第256步，开始核对完整检查点清单及评测批次。重新查看Claude评论，尚无晚于14:39的新增意见 | 正常评测继续；未启动下一对、不重跑旧任务 |
| 2026.10.12 15:43（阶段核对完成） | Codex | 两项训练末步、冻结计划及检查点清单一致；已连续保存多题288／多解256条终点评测输出，末批原始返回与评分哈希一致；完整state及全量重评分留到收尾 | [阶段证据](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FIRST_PAIR_TRAINED.json)；仍仅2张H100工作，无新失败。15:41平台延迟计量$47.16；下一对待本对核验释放后执行 |
| 2026.10.12 15:47（交付），16:09（读取） | Claude；Codex读取 | Claude第四轮独立复现token v2八份计划和曝光，接受T1/T2/T3/K1处理；旧先导结果PASS，保留512-token截断规则。提出R1依赖清理和L1逐格报告截断数 | [固定报告730e7d06](https://github.com/Townzc/2P1R_Reasoning_Post/blob/730e7d06885bf853fb9fcb1afac2aef83d5fc7d1/audit/claude/20261012d/REPORT.md)；新八项尚无最终结果，不在PASS范围 |
| 2026.10.12 16:11（处理开始） | Codex | 在CPU复现与结果报告侧处理R1/L1；先核对两张原H100正常评测、其余六项未启动 | 不改变数据、训练剂量、生成上限或判分规则；改动完成后发布验证证据 |
| 2026.10.12 16:12（处理完成） | Codex | 八份计划在禁用site-packages的Python中全部按原摘要复现；新增截断统计核验及显式结果列，11项CPU检查通过；确认旧先导截断38/33条 | [处理记录](audit/P007_TOKEN_REVIEW_DISPOSITION_20261012.md)、[报告侧审计包](../reports/p007_audit/token_reporting_v1/REVIEW_REQUEST.md)；新修改待外审，正在运行的全部source字节／输入未变，0新模型调用 |
| 2026.10.12 16:26（新首对收尾开始） | Codex | 新token多题学生完成1,319题，实际app停止／容器0；开始只读完整账本、紧凑输出与完整检查点导出。多解仍正常评测 | 待本地全量评分和state核验后公布分数；高题价下一对尚未提交 |
| 2026.10.12 16:11（交付），16:27（读取） | Claude；Codex读取 | 第五轮独立解码并重评分3,088条教师输出：PASS-WITH-NOTES；仅两处百分号解析差异，token数全部一致 | [固定报告5c660321](https://github.com/Townzc/2P1R_Reasoning_Post/blob/5c6603219e5847cb3cd0adf01430ef073b00edaa/audit/claude/20261012e/REPORT.md)；未覆盖GPU采样日志／服务商时戳／重建收费 |
| 2026.10.12 16:30–16:31（核查／收尾） | Codex | 新多题963/1,319、44条长度截断完整核验；多解评测结束、app停止，开始账本与state导出。独立确认E1两条百分号答案不在新token前缀，保留冻结判分 | 高题价对照仍等待本对全部核验；未改变数据或科学剂量 |
| 2026.10.12 16:34（首对完整核验／下一对启动前） | Codex | 新token多题963／多解950，各1,319题；多题暂高0.99pp。1,722文件、512更新／1,048,574 targets和两个完整state全部一致，截断44／45条保留计错，workspace容器0 | [核验结果](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FIRST_PAIR_RESULTS.json)、[Claude审计包](../reports/p007_audit/token_p0_seed17_v1/REVIEW_REQUEST.md)；准备高题价seed17，未据分数修改协议 |
| 2026.10.12 16:38（高题价实际启动核验） | Codex | 高题价多题／多解各提交一次；两张H100、CUDA／torch、发布源码、冻结输入和首更新匹配，快照至少7／3步，0终点；四项seed23仍未尝试 | [启动回执](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_HIGH_PRICE_PAIR_STARTED.json)；source3ee3e359，原预留内执行，最多2GPU。新结果待Claude审计 |
| 2026.10.12 16:46（交付），17:04（读取） | Claude；Codex读取 | 第六轮审计零题价token首对为PASS-WITH-NOTES；R1/L1修复PASS。指出E2空答案陈述导致单条框内正确答案漏判；不建议运行中改评分 | [固定报告2d811a49](https://github.com/Townzc/2P1R_Reasoning_Post/blob/2d811a49db4c800bbd3b0e2d946ca55d693faa74/audit/claude/20261012f/REPORT.md)；高题价／seed23及独立权重审计不在该范围 |
| 2026.10.12 17:04（核查开始） | Codex | 按用户要求读取真实日志、provider和新版审计；确认两高题价worker正常，均训练256步完成，终点评测尚未完成 | 不提前计算高题价准确率或启动seed23 |
| 2026.10.12 17:10（阶段／审计复核完成） | Codex | 高题价末步计划、524287targets和checkpoint256清单一致；已保存240/80条评测的末批raw/scored哈希与不可变回执一致。E2原始token单条独立解码复现；首对区间独立重算−0.99pp[−3.18,1.21] | [阶段核验](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_HIGH_PRICE_PAIR_TRAINED.json)、[E2处理](../reports/p007_audit/token_p0_review_followup_v1/README.md)；完整state二进制／全量评分留到收尾，主规则不改 |
| 2026.10.12 17:19（评论交付），17:44（读取） | Claude；Codex读取 | 第六轮补充确认：每个学生1,319条、合计2,638条；接受Codex对E2的处理，主结果保持963／950。Codex检查固定修订报告，确认没有扩大审计范围或要求改变运行方案 | [更正评论](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6135161662)、[固定修订报告87f9a233](https://github.com/Townzc/2P1R_Reasoning_Post/blob/87f9a233e96b8f6695622807e969238efa6332ca/audit/claude/20261012f/REPORT.md)；高题价仍正常评测，尚无完整结果，seed23未启动 |
| 2026.10.12 18:14（高题价收尾开始） | Codex | 两项高题价学生均完成1,319题，实际app于18:03停止、容器0；开始只读完整账本、原始输出和完整检查点导出核验 | 待独立全量重评分后报告两档题价对比；四项seed23仍未启动 |
| 2026.10.12 18:18（高题价核验完成／第二种子启动前） | Codex | 高价多题927／多解952，各1,319题，截断48／60条；全部2,638原始输出、512步／1,048,574 targets及两个完整state核验通过，GPU已退出。两档seed17点估计由多题+0.99pp变为多解+1.90pp，交互+2.88pp[−0.23,5.99] | [两档首种子结果](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_SEED17_RESULTS.json)、[待Claude审计包](../reports/p007_audit/token_seed17_two_prices_v1/REVIEW_REQUEST.md)；单seed／单trace局限保留，按原冻结队列推进seed23 |
| 2026.10.12 18:22（第二种子实际启动核验） | Codex | seed23零题价多题／多解各提交一次；两张H100、CUDA12.8、发布源90ba8859、配置和首个更新均一致，快照至少3／11步，尚无终点；最后高题价seed23与CPU审计未尝试 | [启动证据](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_SECOND_SEED_STARTED.json)；原剂量、两GPU、截止与预留不变，按30分钟巡检 |
| 2026.10.12 18:26（收录） | 研究者；Codex排程核对 | 明确中期材料最晚周二21:00齐备，长期研究不抢占汇报准备。原方案只有seed17/23两种子、每种子4格；首种子从15:18启动到18:16本地核验约2小时58分，累计worker约5.19 GPU小时 | 第二种子已运行；按实测预计周一21:30–22:30完成剩余实验与核验，条件为无新故障。实验19:00硬截止及预算不延长 |
| 2026.10.12 18:22（审计交付），18:47（读取／复核开始） | Claude；Codex读取 | 第七轮固定67901abf对seed17四格结果给出PASS-WITH-NOTES；新增两个跨题价补充对比，并指出高价多题也有一例E2格式解析问题。Codex开始独立复核，同时确认seed23零价两项已到256步、正常评测 | [第七轮报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/67901abf56bfa68467661abed903fd691e890aef/audit/claude/20261012g/REPORT.md)；不改主评分或运行中的协议，seed23不在此次外审范围 |
| 2026.10.12 18:53（阶段／审计复核完成） | Codex | seed23零价两项末步、524287 targets和checkpoint256清单一致；已连续保存464／496条终点评测，末批原始返回及评分哈希一致。复现Claude第七轮全部对比与新增E2原始解析例；主评分不变 | [训练阶段](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_SECOND_SEED_TRAINED.json)、[审计处理](../reports/p007_audit/token_seed17_review_followup_v1/README.md)；完整state和全量评分待收尾，最后高价seed23仍未启动 |
| 2026.10.12 18:58（审计交付），19:14（读取／复核开始） | Claude；Codex读取 | 第八轮固定007ed950接受第七轮处理、对follow-up复算和seed23训练阶段记录给出限定范围PASS；强调两训练种子共享每格同一教师轨迹 | [固定报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/007ed950183d547b5a92b8ca250c65fb4bacc588/audit/claude/20261013a/REPORT.md)；Codex核对路径集合与曝光，不把训练重复当采购重复 |
| 2026.10.12 19:16（复核完成） | Codex | 独立核对两种子的路径集合408／474／91／230完全相同，曝光变化每路径至多1；保留“2 training seeds, 1 teacher trace per cell”表述。Claude第八轮接受上一轮处理、通过follow-up数值复算及阶段配置记录 | [种子范围证据](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_TRAINING_SEED_SCOPE.json)；不代表重新采购的方差，seed23终点评分尚未外审 |
| 2026.10.12 19:19（收尾开始） | Codex | seed23零价多题已完成全部1,319题，实际app停止、所属容器0；开始独立账本、输出和完整检查点收回。多解继续正常评测 | 原始模型自报分数待独立复算；下一对未启动 |
| 2026.10.12 19:23（第二项收尾） | Codex | seed23零价多解也完成全部1,319题，app停止、所属容器0；多题861文件与完整state传输SHA通过，独立全量评分进行中；多解开始只读收回 | 两项分数待独立oracle；最后高价对仍未启动 |
| 2026.10.12 19:33（只读修复前） | Codex | seed23零价两项GPU均已释放，多题958/1319及完整state独立通过；多解下载一段超时，已对账269完整文件、26/27有效分块，无模型工作丢失 | [修复规格](../reports/sft_allocation_midpoint_20261011/P007B_EXPORT_RECOVERY_20261013.json)；10项CPU检查通过，先发布后仅补缺失数据，原失败保留 |
| 2026.10.12 19:35（核验完成） | Codex | seed23零价多题/多解均958/1319，各49截断；两份完整state与2,638条raw重评分通过，GPU均停止；只读传输修复完成且原失败保留 | [两种子零价结果](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ZERO_PRICE_TWO_SEEDS.json)、[恢复核验](../reports/sft_allocation_midpoint_20261011/P007B_EXPORT_RECOVERY_CLOSED_20261013.json)；新packet待Claude审计 |
| 2026.10.12 19:36（下一阶段前） | Codex | 发布6项已核验结果后，实时确认原高价seed23两个slot无人占用、未有意图/claim，再各启动一次；不增加剂量或预留 | 原冻结最后一对，最多2H100；末次平台延迟计量$75.56084103，非发票/余额 |
| 2026.10.12 19:40（实际启动核验） | Codex | 最后高价seed23两项各提交一次，H10080GB/CUDA12.8/torch2.8.0、发布源码/计划/首更新一致，快照至少4/11已提交更新；无新CPUcontroller | [真实启动证据](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FINAL_PAIR_STARTED.json)；8个原定学生均已安排，最后两项完成后只剩已预留最终审计 |
| 2026.10.12 20:15（核查进行中） | Codex | 已读取Claude第九轮固定报告；最后两项训练日志已到256更新，正核对清单/末步/最新原始批次；同时复核S9跨种子翻转数和两个新E2案例 | 尚未完成最后评测，不读取部分准确率作结论；不改live评分或计划 |
| 2026.10.12 20:04（GitHub交付；20:14收录） | Claude | 第九轮：零价两种子包PASS-WITH-NOTES，两个seed23完整state SHA独立核对；导出恢复PASS；启动PASS仅记录。提出S9翻转数及两个新E2 | [固定报告385744e3](https://github.com/Townzc/2P1R_Reasoning_Post/blob/385744e387d61fa300b13df3ac71e55645ea744e/audit/claude/20261013b/REPORT.md)；不覆盖逐步权重或最后高价结果 |
| 2026.10.12 20:22（阶段核验/复核完成） | Codex | 最后两项各256更新/524287targets，清单/末步计划/最新raw与done吻合；连续评测384/576仍无终点。S9翻转183/156、策略差异219/208及新E2两例复现，主分不改 | [八项训练阶段完成](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ALL_TRAINING_COMPLETE.json)、[独立审计处理](../reports/p007_audit/token_seed23_p0_review_followup_v1/README.md)；新follow-up待外审 |
| 2026.10.12 20:44（审计读取／收尾检查开始） | Codex | 读取Claude第十轮固定81be9a28：接受第九轮处理、follow-up包PASS；最后高价对仍正常评测，开始核对实际terminal与释放状态 | 不改主评分或剂量；高价seed23最终结果尚不在此次审计范围 |
| 2026.10.12 20:46（最后多解收尾开始） | Codex | 高价seed23多解已返回全部1,319条结果，开始确认app停止后收回完整账本、原始输出和checkpoint256；多题仍正常评测 | 分数待独立oracle，最后CPU总审计尚未启动 |
| 2026.10.12 20:54（第十轮处理／只读修复前） | Codex | Claude第十轮接受上轮处理，follow-up包PASS；最后多解app已停止，但检查点下载超时。独立对账28有效文件、13/27有效分块，无坏文件，准备一次只读补齐 | [故障和修复界限](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_DEPTH_EXPORT_RECOVERY_20261013.json)、[限定审计范围](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ROUND10_REVIEWED.json)；多题继续正常评测，0新增模型工作 |
| 2026.10.12 21:01（最后多解核验完成） | Codex | 高价seed23多解949/1319、60截断；861文件/完整state/256更新/524287targets和全部raw重评分通过，GPU已释放。只读修复复用28文件/13分块，保留原失败与完成回执 | [第七项关闭证据](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_FINAL_DEPTH_CLOSED.json)；最后多题仍评测，价格交互和CPU总审计待全八项 |
| 2026.10.12 21:07（最后多题收尾开始） | Codex | 最后高价seed23多题返回全部1,319条结果，开始独立收回完整账本、原始输出与checkpoint256 | 原GPU正常退出；全部学生不再生成新输出，最终分数仍待本地oracle与CPU总审计 |
| 2026.10.12 21:14（最后传输对账／第十一轮处理） | Codex | Claude独立预审确认多解949/1319与完整state；采用差值区间主图、准确率0–100%辅助图。最后多题下载同类超时，33完整文件/3分块有效，准备只补828文件/24分块 | [修复边界](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_BREADTH_EXPORT_RECOVERY_20261013.json)、[第十一轮范围](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ROUND11_REVIEWED.json)；GPU全部释放，0新增科学剂量 |
| 2026.10.12 21:21（第二次传输对账／修复前） | Codex | 首次补齐取得1个新分块后又在20秒元数据请求超时；原失败全部保留，现33完整文件/4有效分块，无坏文件。准备复用两次有效证据，仅补23分块和其余文件；90秒地址请求/360秒分块/900秒整体硬限 | [有界修复](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_BREADTH_EXPORT_RECOVERY_R2_20261013.json)；0模型调用/远端写入，全部GPU已释放 |
| 2026.10.12 21:26（八项本地核验完成／CPU总审计前） | Codex | 最后多题949/1319、63截断，多解949/1319、60截断；八项共10,552原始输出、2,048更新/4,194,296targets和8份完整state通过，所有GPU已释放。二种子两档均持平，未重复首种子排名反转 | [八项本地核验](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ALL_LOCAL_ORACLES_CLOSED.json)；只读补齐复用4分块、861文件全SHA通过，原两次传输失败保留；下一步仅已预留CPU总审计 |
| 2026.10.12 21:30（CPU总审计实际启动） | Codex | fresh gate确认八份oracle通过、GPU退出、audit无任何尝试后，仅一次提交原CPU审计；实际claim/config与唯一CPU容器一致，14份结果目录核验中 | [CPU实际启动](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_CPU_AUDIT_STARTED.json)；0 GPU/0新生成，原预留$3内执行，最终通知待原回执、输出和CPU释放核对 |

| 2026.10.12 21:43（Claude交付），21:54/21:58（评论/固定报告读取） | Claude；Codex读取 | 第十二轮固定514cec51复核全部10,552输出与8终点state，PASS-WITH-NOTES；撤回将seed17单独跨题价下降作为发现的强调。CPU总审计仍活动 | [固定报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/514cec51b7903d0d53be33f861fcd11929b43722/audit/claude/20261013e/REPORT.md)；实际最终summary/图/事实页不在范围 |
| 2026.10.12 22:00（第十二轮处理完成） | Codex | 从已核验终点记录复核breadth高价的跨seed翻转200题及两seed价格差−2.73/−0.68pp；接受F12-1，不作为重复损伤或稳健价格效应。保留四个已知E2、全部长度截断与原主分 | [限定审计处理](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ROUND12_REVIEWED.json)；最终CPU及图表仍待完成，0新模型调用 |

| 2026.10.12 22:06（保存记录的耗时复盘） | Codex | 八项更新耗时合计56.50 GPU分钟，worker合计9.78 GPU小时；被动样本平均利用率各16.05%–29.69%，显存峰值13.58–16.09 GiB。其余时间含评测、验证与读写，不全部视为训练或评测；未跑硬件优选试验 | [可复算运行诊断](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_RUNTIME_DIAGNOSTICS.json)；0新模型调用，CPU总审计仍活动 |

| 2026.10.12 22:22（存储审计风险／应急准备） | Codex | 原CPU总审计仍活动，逐目录读写速度可能超过原55分钟硬限。已准备仅携带原核验完成目录、补核其余目录的CPU方案；8个CPU合同测试通过，尚无续核准入或提交 | 当前任务不延长/不取消，无新GPU/模型工作；只在原app停止且保存真实部分证据后才可能准入，新方案最多2个并行读取线程 |

| 2026.10.12 22:24（CPU硬限）/22:27（对账中） | Codex | 原CPU审计按55分钟硬限退出124，服务商替换被原claim拦住；provider已停止、容器0。八项学生结果与本地完整核验不受影响。先保存完整账本和部分证据，再确定仅剩CPU核验范围 | [真实中断记录](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_CPU_AUDIT_INTERRUPTED.json)；0新增模型工作，尚未续核提交 |

## 维护规则

- 一行对应一个可核验的交付、故障、决定或阶段变化，避免写“正在思考”之类无法回溯的活动。
- 每行写执行者、时间来源、实际状态和证据。由 Codex 代录 Claude／Pro 的材料时标明来源；没有收到的交付写“待同步”。
- 实验细节进入 RUN_LOG；审计结论进入独立审计分支和处理记录；论文笔记进入 Papers 仓库。本表只链接，避免三份摘要互相漂移。
- 使用 Issue 讨论一个具体问题，使用本表看全局；讨论意见不自动变成预算或执行授权。
- 各方提交应先读取当前工作分支，采用普通提交／必要时 PR；不覆盖他人的记录，不强制推送。Claude 的审计文件保留在其独立分支；作者与维护者分开记录。
- 阶段完成更新一次。发生新风险、方案改变或需要研究者决策时立即更新。时间统一用 PDT，并在更正时保留原记录和更正来源。

共享工作流说明：[RESEARCH_WORKFLOW_ZH.md](RESEARCH_WORKFLOW_ZH.md)。
