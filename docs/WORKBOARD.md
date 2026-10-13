# P007 / P008 工作总表

所有时间使用 **America/Los_Angeles（PDT，UTC−7）**。这是团队进度与决策入口；实验原始证据仍在结果文件、RUN_LOG 和审计包中。时间来自提交、回执或 GitHub 事件；仅知道读取时间时写“收录”，不假定那是实际发生时间。

## 当前状态

| 工作 | 负责人 | 状态 | 下一步 |
|---|---|---|---|
| 原 P007 四组实验 | Codex；Claude 审计 | 已完成；Claude **PASS-WITH-NOTES**，仅限报告列明范围 | 保留 base 解析敏感性、曝光及评测污染限定 |
| P007A 教师供给先导 | Codex；Claude 审计 | 已完成；紧凑计数/成本表 **PASS**；第五轮原始输出重评分 **PASS-WITH-NOTES** | 范围已扩展至教师原始输出；两个百分号解析差异不影响新token学生数据 |
| P007B 按真实时间计费的采购 | Codex | 四格本地核验完成；Claude 对零题价格记账 **PASS**、成本解释 **FAIL** | C-B1 已复现，不能将速度差直接归因于题价 |
| 首批两项学生 | Codex；Claude审计 | 两项完整核验完成：多题953/1319，多解969/1319；GPU均已退出；Claude结果PASS | 仅作为原时间计价先导，保留截断38/33条及其他限制 |
| 后六项原学生 | Codex | **未启动，已明确撤销** | 保留旧账本；新方案使用独立 campaign |
| 统一 token 计价修订 | Codex；Claude审计 | **8/8学生与14目录CPU证据链完整关闭，GPU/CPU容器0**；seed17零价963/950、高价927/952；seed23零价958/958、高价949/949（各/1319） | [完整事实/图表/局限](../reports/sft_allocation_midpoint_20261011/P007B_MIDPOINT_EVIDENCE.md)已齐备；Claude第十五轮最终包/事实页PASS；原图PASS-WITH-NOTES，图v2已获Claude PASS。首seed反转未被次seed重复；原CPU10项+续核4项，原失败保留 |
| P008 v3.1 | Codex工程；Claude审计；研究者 | D1完整/G1；D2失败父保留，唯一续跑已完成；全部7416原始输出及8钱包本地合并G1通过，GPU已退出 | [启动证据](../reports/p008_20261013/D2_CONTINUATION_STARTED_v3.json)；8卡授权及代码审计已过，owner工作区ID与实验CLI匹配；配额截图已证实总GPU上限10，学生继续最多8卡；两采购G1和新完成队列代码/owner/配额范围均通过；18项共同计划及确切输入G1已通过；T1+base正做一次上传/派发准备，T8仍待实际N2计时 |
| 阅读材料 | GPT Pro | 分工已明确；本轮尚未收到可核验的 Pro 新交付 | 用户转交论文链接、关键证据和阅读结论后登记 |
| 独立审计与新增阅读 | Claude | 已收到第十五轮审计及39–42号新笔记；Codex已核查关键原文 | 按新证据版本继续审计；旧结论不自动覆盖新文件 |

预算：总额$500，支出上限$450，保护至少$50。P008预留$249.68／上限$250（含新批准的D2续跑$12）；worker仍须真实审计准入。最新平台延迟计量$116.26183740（本轮读取UTC19:12附近；旧快照保留），billed0，不是发票/余额。旧P007B数据、图表和局限清单已齐备；用户已直接取消学生19PDT截止，有限学生队列按原剂量和预算运行至完成；D2自身时限不改。21PDT材料仍冻结，未完成结果标pending。

## 时间线（追加记录，保留更正历史）

| 时间（PDT） | 执行者／来源 | 做了什么、得到什么 | 状态与证据 |
|---|---|---|---|
| 2026.10.13 13:08（输入准入） | Codex | 原槽位未尝试核对、一次转移及输入回读通过；10项T1+base计时名单已在派发前冻结 | [输入/计时名单证据](../reports/p008_20261013/student_t1_dispatch_admission_v1/README.md)；下一步按固定顺序最多8项并行，T8待N2 |
| 2026.10.13 12:42（Claude评论）/13:00–13:05（读取及准入准备） | Claude；Codex | 确切18计划、两采购输入及新学生spec获PASS-WITH-NOTES；保留length-conditioned曝光限制 | [学生G1接受](../reports/p008_20261013/student_g1_accepted_v1/DISPOSITION.md)；准备T1+base一次上传及派发，T8仍等N2 |
| 2026.10.13 12:19/12:21（Claude评论）/12:34–12:37（读取及复核） | Claude；Codex | 完整D2合并G1与完成队列代码/owner/配额范围均PASS-WITH-NOTES；独立纠正审计表8格零可用题数，原评分/数据不改 | [限定接受及更正](../reports/p008_20261013/review_8d8a9e8b_followup_v1/DISPOSITION.md)；确切输入G1待审，无学生调用 |
| 2026.10.13 12:28（收尾工具准备开始） | Codex | 等待新学生G1期间，准备最终CPU的原失败父/续跑子/新学生22来源冻结、上传与只读收尾工具 | 三个工具已准备并通过语法检查；未运行/无实际CPU输入，实际21项逻辑结果与I/O数值审计仍缺，原13CPU源冻结 |
| 2026.10.13 12:15–12:18（本地准备/数值包） | Codex | 两次采购18训练计划/19配置已冻结，共同监督token为524287及4194296；36输入文件逐项验证。两个旧schema读取失败均发生在输出前并保留；v3仅修读取与group元数据 | [确切输入/G1待审](../reports/p008_20261013/student_admission_v1/REVIEW_REQUEST.md)；0学生上传/调用，N2仍OPEN，23项新最终CPU代码检查通过但未准入 |
| 2026.10.13 12:01（完成）/12:03–12:09（独立收尾） | Codex | D2原3992＋新3424＝7416输出和8钱包完整重放通过；原失败父保留，续跑GPU退出。两采购完整本地oracle均齐备，开始共同训练计划准备 | [完整本地证据](../reports/p008_20261013/D2_MERGED_LOCAL_CLOSED.json)、[新D2审计包](../reports/p008_20261013/pool_d2_merged_v1/README.md)；外审待定，无学生调用 |
| 2026.10.13 12:03（代码准备） | Codex | 新学生完成队列转移20个未尝试slot、预留194.60美元全部来自既有预算；16项新CPU检查通过，原科学/活动D2源未改 | [代码、权限与配额待审](../reports/p008_20261013/student_completion_queue_v1/REVIEW_REQUEST.md)；无新云调用，真实共同计划/G1/N2未豁免 |
| 2026.10.13 11:53–11:55（owner新消息收录） | 研究者直接授权；Codex | matching工作区截图显示总GPU并发10，已保存私有原图和SHA；学生保持8卡。明确学生计算延后至有限队列完成，每项时长/剂量/预算不变；21PDT材料仍冻结 | [直接完成授权](../reports/p008_20261013/OWNER_STUDENT_COMPLETION.json)、[配额范围](../reports/p008_20261013/STUDENT_GPU_QUOTA_EVIDENCE.json)；新学生专用账本/代码须准确审计，活动D2源不改 |
| 2026.10.13 11:43（工程准备开始） | Codex | D2原续跑正常输出期间，准备独立最终CPU入口，把失败父与完成child作为22个物理来源核验；原21逻辑组不变 | 仅本地代码与模拟测试；实际CPU输入/准入/调用尚未生成，31个活动child源不改 |
| 2026.10.13 11:31:49（实际worker开始）/11:33（启动核验）/11:36（工作区核对） | Codex；owner提供ID | 原输入复用、0重传；唯一child实际H100运行，batch146的28个新raw/ID/source/probe/原缓存不相交核验通过。工作区ID与CLI完全一致，配额数仍未知 | [启动证据](../reports/p008_20261013/D2_CONTINUATION_STARTED_v3.json)；实际worker最晚13:31:49PDT停止，早于owner14PDT；不是最终G1。无学生/base/CPU调用 |
| 2026.10.13 11:11–11:12（评论交付）/11:26（读取） | Claude；Codex | D2确切14PDT v3获PASS，31源/7200秒/7份已核验输入不变；学生8卡代码仅PASS-WITH-NOTES，真实配额仍未确认 | [v3审计接受](../reports/p008_20261013/D2_RUNTIME_V3_ACCEPTED.json)；开始唯一续跑的输入复用与实际准入检查。全局19PDT不据转述改变 |
| 2026.10.13 11:17（本地准备开始） | Codex | 等待D2 v3确切审计期间，准备最终CPU核验的失败父／完成子文件验证器；不改31个child源文件 | 10项新模拟检查通过（初次1项夹具错误已修并留证）；原child源未变。仅验证器准备，完整CPU入口/准入尚未就绪 |
| 2026.10.13 11:05（owner直接答复收录）/11:08（准备） | 研究者；Codex | 明确批准D2截止14PDT；仅改截止、plan摘要和确切owner绑定，7200秒/$12/全局19PDT不变。旧调用spawn前拒绝；7文件复用，0新上传/调用。6项新CPU检查通过 | [v3确切时间规格待审](../reports/p008_20261013/d2_continuation_admission_v3/REVIEW_REQUEST.md)，最晚11:48:20PDT派发；不再重复问同一授权 |
| 2026.10.13 10:48（拒绝）/10:50（核验）/11:01（8卡准备） | Codex；研究者直接授权 | D2构建后完整窗口不足，spawn前拒绝，0GPU调用/claim/科学尝试；7个输入读回完成。学生最多8卡获直接授权，10项新离线检查通过；实际实验工作区配额未确认，D2改14PDT提案待答 | [拒绝证据](../reports/p008_20261013/D2_PRESPAWN_WINDOW_FAILURE.json)、[8卡代码待审](../reports/p008_20261013/student_eight_gpu_v1/REVIEW_REQUEST.md)；不重复上传、不自动扩时、无学生调用 |
| 2026.10.13 10:40–10:42（审计读取及owner答复收录） | Claude；研究者；Codex | v2精确provider查询@32777f41获真实PASS，开始唯一prefix上传/读回，尚未child派发。研究者在本聊天另确认学生最多8卡，需配额及代码/数值审计，不改变剂量预算时限 | [v2审计](../reports/p008_20261013/D2_RUNTIME_V2_ACCEPTED.json)、[直接8卡授权](../reports/p008_20261013/OWNER_STUDENT_8GPU.json)；D2派发与并发修订分开 |
| 2026.10.13 10:28（拒绝）/10:30（精确核查及修订） | Codex | 上传前旧app近期列表已过期为空，检查在任何写入前拒绝；按精确ID确认D1/D2仍stopped/0容器。只替换本地生命周期查询，8新CPU检查通过，worker AST和数值/生成不变 | [v2小修订待审](../reports/p008_20261013/d2_continuation_admission_v2/REVIEW_REQUEST.md)；原失败log保留，0上传/云构建/模型调用，最晚10:48:20不变 |
| 2026.10.13 10:25–10:28（读取及派发前核对） | Claude；Codex复核 | 新child固定a385fb38已获限定PASS-WITH-NOTES；实际父任务启动至环境13.72秒，支持按未改公式派发一次，真实主机测速仍可拒绝。学生8f31b0ca仅代码PASS，0学生准入 | [真实审计与N1核对](../reports/p008_20261013/d2_runtime_review_acceptance_v1/DISPOSITION.md)；接下来只上传7个新prefix文件并独立读回，最晚10:48:20PDT派发 |
| 2026.10.13 10:11（准备收尾／实际审计读取10:09） | Codex | 续跑worker固定a385fb38、后续学生证据链固定8f31b0ca均已普通发布并登记独立审计；仍无新Claude结论。上传/运行核验/收尾/失败保全工具已备，0云构建/调用 | [真实待审状态](../reports/p008_20261013/D2_CONTINUATION_REVIEW_PENDING_1710.json)；保留13PDT截止，最晚10:48:20PDT完整窗口派发，无默许准入 |
| 2026.10.13 10:00（准备完成） | Codex | 学生后续入口单独适配D1完成＋D2失败父＋完成child；13新CPU检查通过，原科学执行与独立评分函数保持一致；实际共同计划、G1、N2及云调用仍未开始 | [仅后续学生代码待审](../reports/p008_20261013/student_parent_child_lineage_v1/REVIEW_REQUEST.md)，不替代D2续跑准入 |
| 2026.10.13 09:48（工程准备完成） | Codex | 新续跑worker、11条父子依赖实时检查、固定3次计费主机测速、7200秒入口硬限与独立父子raw核验脚本已准备；15新CPU测试通过，0云构建/调用 | [固定准入包待审](../reports/p008_20261013/d2_continuation_admission_v1/REVIEW_REQUEST.md)；代码PASS前不上传/派发，不把父失败改成completed |
| 2026.10.13 09:36（答复收录／工程开始） | 研究者；Codex执行 | 研究者明确保留两次采购，将D2续跑截止改为13PDT；7200秒、仅未尝试部分、新增$12预留和审计前置不变。开始worker/绑定/父子证据适配 | [授权边界](../reports/p008_20261013/OWNER_D2_CONTINUATION_13PDT.json)；累计预留$249.68，尚无新云调用，19PDT计算硬停不变 |
| 2026.10.13 07:56（实际检查；界线07:48:20） | Codex | 拟议D2续跑10PDT截止方案也已不足7200+700秒完整窗口，且未获owner答复；没有晚启动、缩运行上限或自动改组。Claude评论/分支无更新 | [窗口记录](../reports/p008_20261013/PROPOSED_D2_WINDOW_EXPIRED.json)；0新增调用/预留，19PDT硬停、21PDT材料冻结不变，P007B材料齐备 |
| 2026.10.13 06:42:43（评论），06:57（原文回执读取） | Claude；Codex收录核对 | Claude接受下一动作4缓存+12未生成、公式括号、工期上限不等于ETA三项更正；接受在已准入worker内做计费的加载前测量。无新增科学审计或运行准入 | [原评论](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6146926321)、[范围记录](../reports/p008_20261013/D2_REVIEW_CORRECTIONS_ACKNOWLEDGED.json)；原owner问题待答，0新增模型调用 |
| 2026.10.13 05:57（准备开始） | Codex | 在等待范围/子任务时限选择期间，准备只处理D2未尝试部分的运行核心与父子证据核验；原池和既有学生源码保持冻结 | 仅本地代码及CPU夹具；不创建准入、不上传或调用云模型 |
| 2026.10.13 06:34（新审计处理） | Claude 82b3d69a／39caf811；Codex复核 | D2失败前缀PASS、续跑核心code-only PASS-WITH-NOTES；说明20测试运行命令，独立确认下一depth动作有4缓存+12未生成，修正公式括号；按既定时限核算39.44 GPU小时的上限包络，明确不是ETA或失败概率 | [审计处理](../reports/p008_20261013/d2_review_followup_v1/DISPOSITION.md)；没有新任务准入，联合T/子截止仍待owner选择 |
| 2026.10.13 06:04（准备完成） | Codex | D2续跑核心12项CPU检查通过；实际3992答案前缀绑定一致；原生成循环和虚拟钱包计费保持不变，失败父记录与新增量分开 | [代码待审](../reports/p008_20261013/pool_continuation_core_v1/REVIEW_REQUEST.md)；尚无child云入口/准入/调用，时限或范围选择仍待答；初次3项测试夹具错误已留证修正 |
| 2026.10.13 05:51（实际检查） | Codex | 原D2续跑需保留7200+700秒完整窗口，最晚05:48:20已过；尚未收到延长子任务截止或改为D1单采购的选择 | 没有新GPU调用，原08PDT子任务截止不擅自改动；19PDT全局硬停与21PDT材料冻结保持 |
| 2026.10.13 05:46（本阶段收尾） | Codex；Claude b4a0e5e7 | D1全7420raw/8wallet本地和外部G1通过；D2失败父3992raw、146批、1756文件保全并独立重放，0未知、0待结算动作；纯前缀复原8测试和真实库存检查通过，未调用新模型 | [D1](../reports/p008_20261013/pool_d1_v1/README.md)、[D2](../reports/p008_20261013/pool_d2_reconciliation_v1/REVIEW_REQUEST.md)、[审计更正](../reports/p008_20261013/d1_review_disposition_v1/DISPOSITION.md)；owner时限/范围问题待答 |
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
| 2026.10.12 22:37（中断对账完成／续核前） | Codex | 原审计10项已核验目录证明完整回收并绑定原claim/source/terminal，剩余仅depth_p4_s17/s23及两个旧先导；六个已下载小文件和原完整账本复用，补四个较大JSON和intent。原4MB本地大小门失败保留 | [明确续核准入](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_CPU_AUDIT_CONTINUATION_ADMISSION.json)；只核剩余四目录，2CPU/8GiB/2读取线程/55分钟/额外$3，尚未提交，无新模型工作 |
| 2026.10.12 22:16（审计交付），22:33（固定报告读取） | Claude；Codex读取 | 第十三轮固定d7cb2d0d接受解释更正和运行诊断PASS；评测后端等价性检查仅作中期后建议，未准入，不改本轮结果；不依赖其提及的未确认未来$2700 | [限定处理](../reports/sft_allocation_midpoint_20261011/P007B_TOKEN_ROUND13_REVIEWED.json)；本轮仍$500总额/$450支出上限/$50保护 |
| 2026.10.12 22:38（唯一提交）/22:44（实际核验） | Codex | 仅剩4目录的CPU续核已实际运行，10项原证明已接入；CPU容器、claim、冻结源码逐项一致。无GPU／新模型调用，原失败保留 | [真实启动证明](../reports/sft_allocation_midpoint_20261011/P007B_FINAL_CPU_AUDIT_CONTINUATION_STARTED.json)；原CPU任务不重启，剩余验证结束后收取完整证据链 |
| 2026.10.12 22:51（续核进度核对） | Codex | 两项高题价多解的新增CPU证明与原终点／manifest／完整state哈希匹配，累计12/14标签，尚余两个旧先导；保留3次客户端连接超时警告，同一worker仍推进，未重启 | 仅CPU收尾；22:52平台延迟计量$87.20，非发票／余额；总审计尚未完成，最终数值汇总和图表未执行 |
| 2026.10.12 22:55（云CPU完成）/23:16（收录／最终收尾开始） | Codex | 仅剩四项的CPU续核完成，原10项证明加新4项共14项；实际app停止、workspace容器0。开始只读回收总账本和CPU证据，随后独立绑定全链 | 暂不将云端返回直接当最终本地收尾PASS；未新增模型调用，原55分钟中断和有限续核分别保留 |
| 2026.10.12 22:49（审计交付）/23:20（读取） | Claude；Codex读取 | 第十四轮续核代码PASS-WITH-NOTES、接受流程；要求明确原10项+续核4项，建议未来软截止，并提醒第二次超时的日程风险 | [固定cb823703报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/cb823703880cae47c729bfb75000bbe98919b283/audit/claude/20261013g/REPORT.md)；不自动覆盖后来的最终结果/图表 |
| 2026.10.12 23:20–23:24（完整收尾与发布前检查） | Codex | 17个CPU证据文件62.70MB全SHA、原10+新4证明/全账本/八项既有oracle绑定通过，所有容器0；冻结汇总完成，生成并实看两张PNG。均值多解−多题零价−0.49pp、高价+0.95pp，交互+1.44pp，三个条件区间均跨零 | [最终审计包](../reports/p007_audit/token_final_v1/REVIEW_REQUEST.md)；新包待Claude外审；平台延迟计量$87.20，预留$369.50非花费 |
| 2026.10.12 23:24（展示错误修复） | Codex | 发布前发现unused比例被再次除cap，事实页误显0.00%；按四格cap/charge重算，修为6.14/6.88/12.26/10.90%。原页与hash保留，单位及错误记账拒绝检查通过，零模型调用 | [修复记录](../reports/sft_allocation_midpoint_20261011/P007B_REPORTING_UNITS_CORRECTION.json)；原汇总、数据选择和主分未改 |
| 2026.10.12 23:27（材料与下一轮方案） | Codex | 更新完整事实/图表/局限和工作流：下一轮先拆分评测读写耗时，再设计独立采购重复；提前审计成本和统计单位。没有启动优化或新增科学组 | [未执行的下一轮建议](P007_NEXT_PHASE_PLAN_20261013.md)、[共享工作流](RESEARCH_WORKFLOW_ZH.md)；所有中期技术材料准备完毕，等待新包限定范围外审 |

| 2026.10.12 14:39（仓库提交），23:53（读取） | Claude笔记；Codex读取 | 新39–42号笔记涉及数据过滤、无限算力、缩放外推和污染识别；同时回查原文，记录对B/T与机制解释的限制 | [来源记录](../reports/p008_design_review_20261013/SOURCE_READ_RECORD.json)，不记为Pro交付 |
| 2026.10.12 23:35（GitHub交付），23:53（读取） | Claude第十五轮 | 最终token_final_v1/事实页PASS；原图PASS-WITH-NOTES，要求重合点展示修复，并建议功效规划 | [固定报告3e3e33d3](https://github.com/Townzc/2P1R_Reasoning_Post/blob/3e3e33d3652e813a7685c2fb5bd6315b5448ccb5/audit/claude/20261013h/REPORT.md)；判定目标736b3920 |
| 2026.10.12 23:50（GitHub评论），23:51（开始处理） | Claude提案；研究者请求；Codex | 收到P008 v2和独立评价请求；开始读新笔记、检查目标量/门控/采购重复与成本，保持全部云任务关闭 | [原提案4934d852](https://github.com/Townzc/2P1R_Reasoning_Post/blob/4934d852f375bc79bec99a636edd1fbf8f144604/audit/claude/20261013i/P008_PROPOSAL.md)；提案不是准入 |
| 2026.10.13 00:05（评审整理） | Codex | 复核功效假设及164训练单位/295456次次评测；提出固定预算主比较+独立采购+正交桥接的11学生示例，尚未准入。v2图已实际查看，主分未改 | [评审](audit/P008_V2_DESIGN_REVIEW_20261013.md)、[算术](../reports/p008_design_review_20261013/CALCULATIONS.json)、[v2图](../reports/sft_allocation_midpoint_20261011/figures_token_v2/accuracy_by_price_and_seed.png)；0模型调用/0外部评论 |

| 2026.10.13 00:08（版本绑定） | Codex | 独立评审/新图发布为7cefa253；INDEX绑定固定commit、manifest和阻塞范围，草拟REVIEW REQUEST由owner发送 | [请求草稿](audit/P008_REVIEW_REQUEST_DRAFT_20261013.md)；没有外部发信或P008执行 |

| 2026.10.13 00:12（GitHub交付），00:14（读取） | Claude；Codex读取 | v3接受B/T、更正门控和采购重复；批评11项不足以回答预算变化，提出20学生/90单位。图v2 PASS | [固定回应4dfd22f6](https://github.com/Townzc/2P1R_Reasoning_Post/blob/4dfd22f6b28c0b99e7bbe0d27c4dbf6ca2a4ce74/audit/claude/20261013j/P008_V3_RESPONSE.md)；不是新实验准入 |
| 2026.10.13 00:14（评审开始） | Codex | 按owner“定稿后再执行”先核读v3全文与阅读库；Papers仍ea8befd5，无新笔记 | 无模型调用，未恢复p007 |
| 2026.10.13 00:20（回应完成） | Codex | 接受C.1目标覆盖批评，推荐v3核心，补同训练seed、桥接交互、Phase0上限、缓存成本及备选解释；核算90/74/42/22单位 | [回应](audit/P008_V3_CODEX_RESPONSE_20261013.md)、[核算](../reports/p008_v3_design_review_20261013/CALCULATIONS.json)；无新实验组/付费调用 |

| 2026.10.13 00:21（固定版本；以提交时间为准） | Codex | v3核心认可及限定条款发布为8545c080；INDEX新增p008-v3-protocol-closure-r1，让Claude按固定版本回应。旧v2意见已回应、图v2PASS已关闭 | [回应](audit/P008_V3_CODEX_RESPONSE_20261013.md)；不发#13评论、不启动Phase0 |

| 2026.10.13 00:27（GitHub交付）/00:31（读取） | Claude；Codex读取 | F1–F5全部接受，新增A1归一化LR、A2固定全报告、A3按draw流水审计；方法分歧关闭 | [固定9547f2ea](https://github.com/Townzc/2P1R_Reasoning_Post/blob/9547f2eaf19165ed1a4847eaedb759a424c9947d/audit/claude/20261013k/P008_V3_1_CLOSURE.md) |
| 2026.10.13 00:30（本聊天授权收录） | 研究者；Codex | owner明确“开始推进”；采用v3.1含A1–A3，250阶段内/450总支出/至少50保护，19计算硬停、21材料冻结 | 不再等待重复许可；G0仍须固定版本审计 |
| 2026.10.13 00:54（阶段准备完成） | Codex | 新LR与原256逐位一致、长训练无反弹；28CPU检查通过，冻结dev500/教师1024/工程8更新921targets+16输出。新增桥接q=0边界显式提G0；0新模型调用 | [协议与有限清单](experiments/P008_v3_1_protocol.md)、[CPU证据](../reports/p008_20261013/CPU_CHECKS.json)；当前0容器、平台延迟计量$87.20 |

| 2026.10.13 01:21（G0等待期间的CPU准备） | Codex | 采购重放、共同训练计划、证据打包和统一次要解析器完成CPU检查；共54项通过，未调用模型。固定G0的19source字节未变；main还未准入 | [准备记录](../reports/p008_20261013/main_preparation_v1/README.md)；禁止把CPU准备写成已开始教师池或学生训练 |

| 2026.10.13 01:21（Claude交付）/01:35（本轮读取） | Claude；Codex复核 | G0@f996621d PASS-WITH-NOTES；采纳G0-1(a)把并发等待超时记为测量失败并继续原调用，14CPU检查通过，等待小范围源码复核。尚无上传或GPU派发 | [定向修订](../reports/p008_20261013/phase0_barrier_v2/REVIEW_REQUEST.md)；四卡主队列仍需真实并发证据 |

| 2026.10.13 01:39（Claude交付）/01:44（读取） | Claude；Codex | 610fde47屏障修订 PASS，保留原G0其他结论；真实接受证明已绑定源码、计划和报告哈希。下一步仅一次上传与Phase0派发 | [接受证明](../reports/p008_20261013/phase0_barrier_v2/G0_ACCEPTANCE.json)；main代码尚待独立审计 |

| 2026.10.13 01:47（实际执行） | Codex | Phase0冻结7个输入5,803,684字节已一次上传并逐文件读回核验；原CLI76047/app已初始化和构建镜像，尚不宣称四卡实际工作 | [调用上限](../reports/p008_20261013/PHASE0_ADMISSION.json)；不重复提交 |
| 2026.10.13 01:50（准备交付） | Codex | main有限单调用调度、9项门控检查、打包取证代码已发布供Claude审查；无main云端调用，数值规格需Phase0后绑定 | [固定代码待审包](../reports/p008_20261013/main_runtime_review_v1/REVIEW_REQUEST.md) |

| 2026.10.13 02:12（本地核验完成） | Codex | Phase0全核验及资源释放；1024teacher、8更新921targets、16工程输出、4GPU实测；平台延迟计量87.92美元。预设工期门选择18学生/74单位，全部16主比较保留，撤去2个高T桥接，待数值审计 | [先导证据](../reports/p008_20261013/phase0_results_v1/README.md)、[数值计划](../reports/p008_20261013/main_admission_v1/REVIEW_REQUEST.md) |

| 2026.10.13 02:17（Claude交付）/02:19（读取） | Claude；Codex复核 | 主数值G0@82e1fafd PASS-WITH-NOTES，仅准入D1/D2池；认可18/74工程缩减和237.68硬预留。保留Phase0两条百分号primary差异，学生仍需G1 | [接受及处理](../reports/p008_20261013/main_g0_acceptance_v1/ACCEPTANCE.json)；开始新命名空间一次输入上传 |

| 2026.10.13 02:21/02:24（派发）—02:31（独立首批核验） | Codex | D1/D2各一次有限H100教师池已实际生成；源码、输入、G0、各首16raw与8策略计费回执吻合。学生尚未准入；本地torch元数据误断言修正并保留原证据，0云重试 | [实际启动](../reports/p008_20261013/MAIN_POOLS_STARTED.json)；18学生/74单位，16主比较保留 |

| 2026.10.13 02:39（请求登记） | Codex | 学生专用入口与G1精确绑定准备完成，21项CPU检查通过；池/旧科学字节未改。补强本地pool来源审计与1024state取证检查；尚无学生数值准入 | [待审代码](../reports/p008_20261013/student_runtime_preflight_v1/REVIEW_REQUEST.md)；不冒充G1通过 |

| 2026.10.13 02:48（只读状态与交接） | Codex | 同一两池仍在生成，无terminal；学生未派发。平台延迟计量$91.16；G1原始证据、共同计划、发布/上传/门控工具已准备但未执行，等待实际池完成 | [状态与费用口径](../reports/p008_20261013/MAIN_PREPARATION_STATUS_0246.json)；按30分钟巡检继续 |

| 2026.10.13 02:51（本轮巡检与准备开始） | Codex | 读取原两池日志；继续准备独立CPU收尾工具，原云调用不重发，旧已关闭结果不重复核验 | 两池仍活动，学生尚未准入 |
| 2026.10.13 03:06（代码准备完成） | Codex | 压缩证据与完整state审计、21标签准入和有限CPU入口完成25项检查；原pool/student科学字节未变，未调用CPU云任务 | [代码预审包](../reports/p008_20261013/cpu_audit_preflight_v1/REVIEW_REQUEST.md)；实际最终审计仍须全部真实结果和独立oracle |

| 2026.10.13 03:07（实际读取） | Codex | 同两池实际provider/claim仍正常、无terminal；Papers与Claude无新交付。收尾CPU代码固定33f964bb已推送，INDEX独立请求只阻塞未来CPU审计，学生G1要求不变 | [状态](../reports/p008_20261013/MAIN_PREPARATION_STATUS_0308.json)；0学生调用/0额外预算 |

| 2026.10.13 03:11（Claude交付）/03:21（读取） | Claude；Codex | 学生f944723e/CPU33f964bb代码均PASS-WITH-NOTES；开始逐条处理S1派发边界、S2软截止、S3读取工期。仅代码范围，G1尚待真实池结果 | [固定54d1803d报告](https://github.com/Townzc/2P1R_Reasoning_Post/blob/54d1803dde98294b7e5a050745609fa11747f856/audit/claude/20261013p/STUDENT_AND_CPU_PREFLIGHT.md) |
| 2026.10.13 03:27（独立处理完成） | Codex | 将单项最晚入口与留2小时收尾的排程目标分开；CPU软截止120秒/按实际读写阶段计时，26项检查通过；大文件速率只作情景估算。原两池继续、0学生调用；延迟计量$96.88 | [处理与时间表](../reports/p008_20261013/preflight_review_54d1803d_v1/README.md)、[待审CPU修订](../reports/p008_20261013/cpu_audit_margin_v2/REVIEW_REQUEST.md) |

| 2026.10.13 03:30–03:35（实测） | Codex | 两池读取保存批次；D2批次间隔72–75秒，而一次生成10.18秒；26个账本读串行3.37/7.11秒，并行0.50/1.42秒。原总工期预测出现风险，保持原池源码与时限，不重放 | [实测与风险](../reports/p008_20261013/student_guard_latency_v2/TIMING_RISK.json)；只读诊断，无新增模型调用 |
| 2026.10.13 03:39（修复准备）/03:42（CPU验证与发布） | Codex | 仅给尚未启动的学生入口增加每单元全量并行只读检查，原校验器/原子写入/剂量不变；35项CPU检查通过，失败测试夹具保留。新代码待Claude审计，G1未准入 | [修订请求](../reports/p008_20261013/student_guard_latency_v2/REVIEW_REQUEST.md)；不把旧代码PASS视为新修订PASS |

| 2026.10.13 03:44（记录更正与请求绑定） | Codex | 上一行初次误填03:48，按实际发布时钟改为03:42；新学生读取修订请求固定41c26651，CPU软截止修订请求固定391dedbf，均待新限定审计 | 仅更新记录和INDEX；原池无重启，G1和新学生均未准入 |

| 2026.10.13 04:02（独立处理） | Claude交付；Codex复核 | 两修订代码已获限定PASS；按N2复查旧训练日志时间戳，原工期未充分缩放账本开销，数值门仍开放。只读26并发样本未采用，学生仍0调用 | [N2证据和处理](../reports/p008_20261013/preflight_review_f7a696b8_v1/DISPOSITION.md)；无恢复准入/预算扩张；INDEX本地发布错误已保留并修正 |

| 2026.10.13 04:06（条件预案发布） | Codex | 在原池超时前冻结可能的D2仅剩余工作修复边界：最多一项/$12、累计249.68、零未知重放；必须先真实停止/对账/新源审计。尚无修复代码/准入/调用；T8须先关闭N2 | [条件预案](../reports/p008_20261013/conditional_pool_repair_plan_v1/REVIEW_REQUEST.md)；原两池继续，不替换科学范围 |

| 2026.10.13 04:15（Claude交付）/04:23（读取） | Claude；Codex复核 | 新审计指出T8逐更新读写随训练量增长，旧数值门仍未关闭；开始独立复算及仅未来学生的16步记账块修订。D2方案仅获预案PASS，未准入执行 | [固定审计](https://github.com/Townzc/2P1R_Reasoning_Post/blob/e8d8ea838eb92af0c2ab27d7c2a2450e378b2e6b/audit/claude/20261013r/N2_AND_REPAIR_BLUEPRINT.md)；原两池继续，0学生调用 |

| 2026.10.13 04:31（代码准备与核验） | Codex | 未来学生16步块记账31项CPU检查通过，原训练主体AST一致；明示禁用延迟≤16步和部分块不可重放。修正审计3/8算术，N2仍开放；原两池源未改 | [修订待审](../reports/p008_20261013/student_block_journal_v1/REVIEW_REQUEST.md)；无模型调用/预算增加 |

| 2026.10.13 04:34（Claude交付）/04:52（读取） | Claude；Codex复核 | block16代码限定PASS-WITH-NOTES，N2未关；更正3/8超限算术已接受。新提T1/base先行的时间门，不看分数 | [固定审计](https://github.com/Townzc/2P1R_Reasoning_Post/blob/4d4fc7b77a07613cebe9a2e0a9350acbb10e88c2/audit/claude/20261013s/BLOCK_JOURNAL.md) |
| 2026.10.13 04:58（数值规则准备） | Codex | 对齐255个间隔、纳入最终打包与检查点上界代理，8项CPU测试通过；所有既定T1和base完整耗时的最大值决定T8，实测仍缺失、不造准入 | [规则待审](../reports/p008_20261013/t1_first_timing_policy_v1/REVIEW_REQUEST.md)；原两池正常工作、无学生/补做调用 |

## 维护规则

- 一行对应一个可核验的交付、故障、决定或阶段变化，避免写“正在思考”之类无法回溯的活动。
- 每行写执行者、时间来源、实际状态和证据。由 Codex 代录 Claude／Pro 的材料时标明来源；没有收到的交付写“待同步”。
- 实验细节进入 RUN_LOG；审计结论进入独立审计分支和处理记录；论文笔记进入 Papers 仓库。本表只链接，避免三份摘要互相漂移。
- 使用 Issue 讨论一个具体问题，使用本表看全局；讨论意见不自动变成预算或执行授权。
- 各方提交应先读取当前工作分支，采用普通提交／必要时 PR；不覆盖他人的记录，不强制推送。Claude 的审计文件保留在其独立分支；作者与维护者分开记录。
- 阶段完成更新一次。发生新风险、方案改变或需要研究者决策时立即更新。时间统一用 PDT，并在更正时保留原记录和更正来源。

共享工作流说明：[RESEARCH_WORKFLOW_ZH.md](RESEARCH_WORKFLOW_ZH.md)。

| 2026.10.13 05:21 PDT | Codex | 开始读取原两池终点/provider及新Claude意见。D1日志报告Appcompleted，先核对原receipt/STOPPED0后独立收尾；D2仍按原12:24UTC时限，不重发。 | 核验中，日志不等于G1 |

| 2026.10.13 05:04 PDT（收尾记录；provider读取04:51） | Codex | 已发布 T1-first 计时规则 @485e7410，INDEX 请求待审；Claude4d4fc7b7 仅通过27源代码。原两池继续，无学生/base/CPU/修复调用；N2仍OPEN。12:03UTC平台延迟计量$111.59150740，非发票/余额；预留$237.68不变。 | [固定证据](../reports/p008_20261013/t1_first_timing_policy_v1/REVIEW_REQUEST.md) |

### 2026-10-13T12:27:28.597206+00:00 / Oct13 05:27 PDT — D1 local G1 closed, D2 parent failed

D1 originalcompleted12:20:18UTC/STOPPED05:20:23PDT, collector28973/export63771/oracle99752 allDONE:2793filesSHA,7420physicalraw outputs/2200804completiontokens independently decoded/scored/deduplicated, all8wallets legally replayed withfullcost/nopeeking. Publicpool_d1_v1 externalG1pending; no studentadmission. D2 originalfinite-deadline failureterminal12:24:47UTC/STOPPED05:24:52PDT, noownedcontainers12:25. Originalfailure kept; interruptedpreservation77411 inprogress, nochild/retry. Scientific failure/unknown status requires complete reconciliation, notlogcounts. Only localread-only closeout/newpublication,0new modelcalls.
