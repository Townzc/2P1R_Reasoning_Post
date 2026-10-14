# P007 / P008 工作总表

所有时间使用 **America/Los_Angeles（PDT，UTC−7）**。这是团队进度与决策入口；实验原始证据仍在结果文件、RUN_LOG 和审计包中。时间来自提交、回执或 GitHub 事件；仅知道读取时间时写“收录”，不假定那是实际发生时间。

## 当前状态

### 2026-10-14 11:46:29 PDT（MATH评分候选独立准备完成；P0仍待审）

新隔离本地依赖math-verify0.9.0/latex2sympy1.11.0/ANTLR4.13.2/SymPy1.14锁定。最终boxed、符号False不可被字符串覆盖、解析/工具失败专属fallback、进程超时及错误教师标签资格分别记录；11新合成检查通过，未评分任何新模型输出。初r1一fixture错误把(x)等同x，纠正fixture不放松解析；后追加不解析错误box不得进入C的守卫，所有日志保留。50真实教师训练输出分歧检查仍未执行，不能把codePASS当P1。新packet固定4c652b03，12manifest成员Git原字节核验，已请求独立代码审计，不阻塞P0。

旧19P0sources/spec/输入和旧数据均未改，仍0P009云镜像/上传/调用。两份共享日志新条目尾部空行曾触发style警告，本次仅规范新尾部换行，历史原源snapshot告警仍保留。新p009ACTIVE、旧两monitorPAUSED。

[候选MATH评分器](../reports/p009_20261014/math_scorer_candidate_v1/README.md)。

### 2026-10-14 11:41:07 PDT（P009确切P0准备送审，0云调用）

已固定新19sourceP0入口，两个1319端点仅评测base638和正确969原检查点，无训练。1,200秒worker/1,260平台/600startup、$2.48预留及首4完整批次每role的计时例外均请求Claude确切审计；0image/upload/claim/model。9pure+3mockedflow共12不同CPUchecks通过，不当CUDA/模型已验证。初依赖方案在发布前修正为已观测vLLM0.11/NumPy2.2.6加PEFT，原未提交包保留；新测试本地临时目录已约束仓库。历史两个源snapshot末尾空行告警保留，不能称全范围stylePASS。

完整读Claude166dc7e6只给教师context排除建议、未核实已发布数据包；不扩大成A0。实际七题/teacher和student全评测长度结果已在e6350f0b；100美元与5未分配已有owner直接批准，无需再问。新p009有限30min巡检已创建ACTIVE，旧p007/automation4保持PAUSED。新代码包fixed6b8c5764的36个manifest成员逐Git原字节核验。待A0+真实P0runtime/numeric通过后才一次上传/派发。

[确切P0包](../reports/p009_20261014/p0_runtime_preflight_v1/README.md) · [context意见回应](../reports/p009_20261014/review_166dc7e6_disposition_v1/DISPOSITION.md)。

### 2026-10-14 11:22:12 PDT（P009五组设计和Stage0输入固定送审；未派发）

用户直接批准总帽$100、Stage2 A/B/C/B′/D五组×2seed，并选择保持教师context2048、7题不支持且不生成。Stage0固定7493首次+500×3追加=8993上限；MATH-500与训练0规范化重叠，4完整dev按长度规则均容纳，D1 3436题两tokenizer完整可编码。Llama401采用原方案允许的OLMo；不是新模型临时替换。

新A0/输入包固定e6350f0b，8个新纯CPU门槛检查通过；A0与确切A1/runtime仍pending，0P009模型/云上传。首builder旧seed域错误在输出前停止并保留，明确P009域修复后一次成功。原OLMo模型卡1处尾空白保持原字节，全范围stylecheck有告警；排除此原始卡的代码检查通过。未重跑任何旧模型/测试/oracle。全部旧p007与automation-4实际回读PAUSED不变。

[方案与数据](../reports/p009_20261014/design_and_inputs_v1/README.md)。范围内各阶段在科学门槛、真实审计、预算/完整窗口/无旧claim通过后自动推进，失败停下报告；12小时是目标而非保证。

### 2026-10-14 03:59:53 PDT（探索性最终交接关闭；automation-4已暂停）

最终材料固定e1ac125a已普通push并独立核对远端。应用工具已暂停automation-4，保存配置实际回读确认PAUSED，原prompt/节奏未改；p007原PAUSED及更新时间均未变。准确核对后清理本地有限caffeinate；0活动实验GPU/CPU，无新科学调用或旧工具重跑。[最终结果与材料](../reports/exploratory_20261014/final_handoff_20261014_v1/README.md) · [暂停回执](../reports/exploratory_20261014/AUTOMATION_4_PAUSED_20261014.json)。旧原包中的pending为发布时历史状态，由新datedacceptance承接，不回写证据。

### 2026-10-14 03:57:24 PDT（最后探索性结果G3通过；只剩发布后的自动化暂停）

完整读取Claude8573632e报告；审计事件03:34:50PDT、实际读取03:54:06PDT，三项full1319独立解码共3957行，停止事件/评分0不一致。结果823/904/934和9/54/43截断不变，所有provider已STOPPED0。原496输出含48未ack及256步检查点来源保留，无重训/重复生成/旧工具重跑。

[最终交接](../reports/exploratory_20261014/final_handoff_20261014_v1/README.md)保留429错误答案来自101题的混杂；reviewer新增探索性bootstrap不替换原主分析，也不作为新的Codex统计或答案真假因果结论。费用仍是10:23UTC六app延迟计量$11.19667285，非发票。原$30帽不变；p007已确认保持PAUSED，automation-4在这次材料普通发布后暂停。

### 2026-10-14 03:30:08 PDT（三个探索性完整评测均本地闭合，实际结果G3待审）

base4-shot823/1319（62.40%）、官方Instruct904（68.54%）、错误教师学生934（70.81%）；截断9/54/43均按错计，0技术未决。最后两项原调用已退出、所属容器为零，收集/导出/合并核验各一次完成；base旧收尾未重复。错误学生复用原256步/524287targets检查点，未重训；完整3957题来源与496旧前缀对齐。现有正确breadth对照969，差35题仅作描述；429错误答案来自101题，不能孤立归因答案真假。

[完整结果与证据](../reports/exploratory_20261014/completed_endpoints_v1/README.md) · [实际结果G3请求](../reports/exploratory_20261014/COMPLETED_ENDPOINTS_REVIEW_REQUEST.md)。最新10:23UTC六app延迟费用11.19667285美元，非最终发票/余额，原$30总帽不变。全部计算结束；automation-4只等结果外审和最终交付后暂停，p007保持暂停。

### 2026-10-14 03:00:49 PDT（探索性 base4-shot 完整本地核验通过）

原调用09:53:28UTC完成、02:53:30PDT资源退出；collector89209/export66382/oracle92307各一次完成。完整1,319题为823正确（62.40%），9截断按规则算错，0技术未决；原272题与新1,047题来源对齐，原失败父保留。其余两原调用尚无完成/错误回执；继续原任务。三项完整结果齐备后统一提交实际G3，当前不称已外审。47运行源码与$30范围不变，p007仍暂停。[本地完成记录](../reports/exploratory_20261014/BASE_4SHOT_LOCAL_CLOSED.json)。

### 2026.10.14 01:42:59 PDT（探索性续跑确切代码待审）

用户已直接批准复用保存输出和256步检查点完成三个评测，并要求睡后继续完成。496旧输出首次独立解码核验通过，48条未确认原记录保留；新15检查通过。确切47源码/真实prefix/费用范围已发布，1047/1175/1239题待生成，0新训练、0新调用。$7原停止费用包络+$20.16续跑帽+$2.84其他余量=$30；非发票保证，Claude数值审计仍待。p007保持暂停。入口：[续跑审计包](../reports/exploratory_20261014/continuation_admission_v1/README.md)。

### 2026.10.13 23:18:52 PDT（最终交接关闭；p007已暂停）

最后CPU实际G3 PASS及最终汇总已普通发布，固定031462f9与remote一致。应用工具已暂停原p007，并从保存配置独立确认PAUSED；其余设置未变。无活动实验计算，本地有界caffeinate已自然退出；无新模型、费用查询或旧工具重跑。原材料不回写，A3deferred保留。[最终汇总](../reports/p008_20261013/final_handoff_20261013_v1/README.md) · [暂停回执](../reports/p008_20261013/P007_PAUSED_20261013.json)。

### 2026.10.13 23:16:24 PDT（最终交接；最后CPU外审事件23:04:06PDT）

完整读取Claude24ef9fd7固定报告：原CPU证明包b1b9de5b实际G3 PASS。至此18学生+base、19格/31对比/3图、最终CPU和本地校验全部关闭；24物理/21逻辑、26state/3失败父/9修订记录保留，0新模型/CPU/旧工具重复。外审只核公开proof，私有binary及原call/app/log对应关系的公开可复核范围明确限定。原21:00冻结材料不改，A3按协议deferred。已整理[最终材料总入口](../reports/p008_20261013/final_handoff_20261013_v1/README.md)，普通发布后按用户指令暂停p007。

### 2026.10.13 22:32:01 PDT（本地最终校验完成；CPU22:25:34终点）

原CPU一次完成并STOPPED/0所属容器；24来源/21逻辑、26完整state、3失败父与9补充记录对齐。一次收集86030、导出12512（78文件）和已审finalizer真实通过，0新模型/重评分/本地state重载。原152.001秒入口至终点是这台主机观测，不是未来上界。[最终证明包](../reports/p008_20261013/final_cpu_integrity_v1/README.md)已生成，实际CPU结果G3待审。新延迟计量224.36194750美元，残余+整阶段354.10574154<450，非发票/余额；21:00冻结材料不改。

### 2026.10.13 22:21:35 PDT（完整报告读取；审计事件22:07:48）

Claude dbb0bcff接受原21:00冻结完整性、冻结后解读，以及确切本地finalizer代码（限定代码PASS-WITH-NOTES）。原图表/科学结果不改；顶层真实proof流程仍未执行，实际CPU结果须另行G3。原CPU CLI35194正在原入口预检，未重复派发；只上传补缺13814已34/34回读通过。[三项审计处理](../reports/p008_20261013/review_dbb0bcff_accepted_v1/DISPOSITION.md)。

### 2026.10.13 22:15 PDT（传输修复完成；实际回读时间见原记录）

原CPU批量上传因SSL连接关闭中断，未触发CPU；一次只读对账确认34文件全部缺失。随后逐文件、有界补齐并立即核SHA，34/34通过、0覆盖、原失败日志保留。仅完成输入传输，CPU核验尚未执行；原19源码与5USD/3300秒不变。[传输证据](../reports/p008_20261013/final_cpu_upload_reconciliation_v1/README.md)。

### 2026.10.13 21:57:38 PDT（最终CPU一次准入完成，上传/调用尚未开始）

原admit78789完成：19源码、24物理/21逻辑、原3失败父、全部原appSTOPPED0/claims和9补充记录核对通过；33输入成员、binding08416dc3/specfeba9e73。将普通发布后一次上传/readback，再调用原5USD、3300秒CPU任务；无新增模型或旧oracle重跑。本地finalizer代码外审仍独立待定。

### 2026.10.13 21:52:58 PDT（最终CPU确切数值审计通过，尚未派发）

Claude fe5b49f7完整报告04:51:07读取／事件04:31:05UTC，24物理/21逻辑、26state实际字节和9补充账本PASS-WITH-NOTES。3003.28秒只是未校准工程估计；保留每label真实耗时，失败不得自动重试。新费用快照224.34193173美元延迟meter，残余+整阶段354.10073538<450；不是发票/余额。开始原5USD一次CPU准入准备，本地finalizer代码仍待审。

### 2026.10.13 21:23:46 PDT（完整结果/3图G3已通过；04:02事件、04:21读取）

Claude8aada22d完整报告给最后T8及全19模型/31对比/3图PASS，T8累计8/8外审通过。R1明确D2高B带题价depth优势在D1未复现；原均值不当独立重复、区间含零不当等效。只读现有表核对27/31区间含零，不重跑统计。新增[冻结后解读](../reports/p008_20261013/post_freeze_results_review_v1/FACTS_ADDENDUM.md)保留原图/数据；其措辞本身待审，21:00快照不改。CPU数值/执行及本地finalizer代码仍待审，0运行任务。

### 2026.10.13 21:15:42 PDT（最终CPU本地校验代码准备，未执行）

新增只读校验工具绑定24物理来源/21逻辑标签、26份state原SHA、全部CPU proof/原账本及原应用STOPPED证据。12项proof夹具和3项独立provider夹具通过；不是实际CPU核验，无新云调用。原19CPU源码与21:00冻结材料均未改。局部检查补强了原应用日志身份绑定，保留准确测试范围；精确代码外审待定，仅阻塞新本地finalizer。[代码请求](../reports/p008_20261013/final_cpu_local_finalizer_preflight_v1/REVIEW_REQUEST.md)。

### 2026.10.13 21:02:04 PDT（21:00材料截止快照已记录，后续另列）

材料截止21:00PDT/04:00UTC，快照元数据实际21:01:18PDT写入；只复制截止前已发布的全19表/3图/费用原字节，未生成任何截止后的新科学内容。03:59:17UTC最后审计读取仍3c15e24c，T8七项G3PASS，最后一项/统计G3/CPU数值与执行/A3待定均如实列出。[冻结材料](../reports/p008_20261013/midpoint_freeze_20261013_2100PDT_v1/READINESS.md)。有限核验继续，原快照不回写。

### 2026.10.13 20:53:59 PDT（最终CPU实际输入已冻结；仅数值提案，未派发）

24physical/21logical全部原terminal/claim/STOPPED0及本地oracle齐备；freeze27242完成，原失败父保留。实际传输5.892GB含5.776GB state，原19CPU源码不改。全部26原HTTP导出回执+最后一次必要oracle真实本机耗时组成3003.28秒代理预测，低于3180线；3x/4x/300秒均未校准场景假设，不是4CPU/FUSE实测或未来上界。新精确数值外审待定，CPU上传/调用仍0。原5USD预留、3300worker和完整4000窗口不变。

### 2026.10.13 20:47:07 PDT（全部18学生+base本地闭合；注册统计/3图已生成）

最后D2/p4 depth=990/1319、36caps，2048/4194296、1024+2048完整state通过；03:37:42UTC完成/20:37:44PDT STOPPED0，第四wave76455/export78367/oracle68339与原字节publisher全部DONE。全19注册分析一次生成31个对比和共享题10k bootstrap，3图实际检查可读，均待最终G3。Claude3c15e24c真读接受D2p0对，T8累计7/8外审PASS；最后1项新包及最终CPU仍待各自审查，无运行GPU。原N2FAIL/事后修订及所有失败父永保，不把预留当费用。

### 2026.10.13 20:28:19 PDT（5项T8真实G3通过；最后1项仍评测）

Claude2a236343完整报告20:26:49读取/事件20:21:11：D1全部4项T8与D2/p4 breadth的6595原始输出/完整剂量/来源核验PASS，state仅公共SHA、外审未读binary。D2/p0两项已本地通过待G3。实际20:26:00巡检仅D2/p4 depth原worker存活，2048/4194296 ack与1056 endpoint名单保存；不是部分分数或完整oracle。原receipt1253是预留而非报告中所称实际花费；原N2 FAIL与事后修订不因已见5个host提前结束而取消。

### 2026.10.13 20:21:45 PDT（7项T8本地闭合；最后1项待完成）

新增D2/p0 breadth956/1319（51 caps）与depth971（45），各4701文件/1319raw/2048updates4194296targets/full1024+2048state/0unknown。第三wave75040、exports23879/28995、oracles86485/22954、原字节publisher均DONE；累计7项本地通过，G3和全19统计/CPU仍pending。唯一待完成D2/p4 depth原CLI74595，不重发。实际20:19:49PDT延迟meter224.56193173，P008标记135.30891807；残余+整阶段355.69301366<450，非invoice/余额，保守预留266.44不当花费。

### 2026.10.13 20:16:38 PDT（5项T8本地闭合；实际provider20:14:25 PDT）

新增D1/p0 depth965/1319（50 caps）与D2/p4 breadth935（45），两项完整原始输出/2048updates4194296targets/两份state通过；累计5项本地oracle通过。第二wave88072、两export10976/98355、oracle75773/24739与publisher均DONE。D2/p0两项也已STOPPED0，第三disjoint wave75040正在收集；仅D2/p4 depth仍运行。T8 G3/全19注册分析/最终CPU均pending，未重放科学调用。

### 2026.10.13 20:05:16 PDT（3项T8本地完整核验完成；外审待定）

D1 B8/p0 breadth=967/1319（39 caps），D1 B8/p4 breadth=945（56），depth=939（47）。每项4701文件SHA、1319原始输出、2048更新/4194296 targets、1024取证与2048最终state全部本地核验，0技术unknown。只读3项wave/3exports/3oracles/3原字节publisher均一次完成，未重放模型。其余5项结果包、全19模型注册分析与最终CPU仍pending；原N2 FAIL/事后9600修订披露不变。[事实与原证据](../reports/p008_20261013/P008_T8_PROGRESS_20261014.md)。

### 2026.10.13 19:56:57 PDT（收尾开始；provider 实际读取19:54:56 PDT）

3项原T8已完成并STOPPED/0容器，5项仍评测。已完成项为D1 B8/p0 breadth与D1 B8/p4两策略；开始一次不重叠3项只读收集，完整raw/state oracle尚未执行。Claude1bf72559已对确切公共COLLECTION publisher v2给出代码PASS；不等于实际结果G3。所有原科学调用/源/剂量/时长帽不变。

### 2026.10.13 19:26:19 PDT（审计处理；实际provider读取19:21:10PDT）

8原T8仍各1个容器／无terminal/result/error，6项保存完整2048步后进入终点评测，末2项保存2000/1520步；不报告部分分数，最终raw/state核验尚未执行。2路只读巡检全8成功，上次限流历史保留。Claude7034ad9d报告19:22:11读：A1/A2报告及只读收尾工具分别PASS，已真绑定；4行usable重叠独立核算，purchased交集仅审内部算术，不扩大外审范围。新每T8公共COLLECTION来源标记publisher v2仅准备待审，原收集/恢复/科学35/CPU19源不改。

[限定范围与L1处理](../reports/p008_20261013/review_7034ad9d_accepted_v1/DISPOSITION.md)；[来源标记代码](../reports/p008_20261013/t8_collection_provenance_preflight_v1/REVIEW_REQUEST.md)。全部已完成旧工作均未重复。

### 2026.10.13 19:20:59 PDT（本轮只读巡检开始）

按间隔核对8项已提交T8的真实provider/claim及保存进度；读取新Claude固定审计，不重复任何启动核验、模型、收尾或已完成统计。

### 2026.10.13 19:03:24 PDT（新审计处理及报告补全；非新模型阶段）

Claude014c2b41原注册统计代码限定PASS-WITH-NOTES（审计事件18:41:45／读取18:51:59PDT），不等于实际T8结果G3。已从原已审评分与计费记录一次汇总全部16钱包：无题池耗尽，结余0.702–14.914%，D1/D2高B的已购/可用题目重叠分别列出；平台延迟费用与虚拟token费用/预留分开。3项新增CPU算术检查通过，0新模型/旧oracle。未来最终页面publisher v2仅准备并另提精确审计，原统计核心/活动35源/CPU19源不改；所有T8收尾及完整统计仍未执行。

证据：[审计范围](../reports/p008_20261013/review_014c2b41_disposition_v1/DISPOSITION.md)；[完整采购与费用表](../reports/p008_20261013/procurement_reporting_v1/ACCOUNTING.md)；[新增报告代码待审](../reports/p008_20261013/procurement_reporting_v1/REVIEW_REQUEST.md)。

### 2026.10.13 18:51:48 PDT（新审计收录；完整报告读取前）

01:51UTC轮询发现Claude新的014c2b41／comment6158987800（事件18:41:45PDT），注册统计代码有新反馈。正在读取固定版本完整报告，核对限定范围及最终成本披露要求；8项原T8调用不变，本轮尚未重复provider巡检。

### 2026.10.13 18:44:30 PDT（读取与发布；实际provider快照18:41:49 PDT）

8项原T8全部首次调用，8项首16更新核验通过；实际8个H100容器、无terminal/result。6项保存进度读取成功，2项遇Volume列表限流，仅进度标unknown，不当云失败且本轮不重查。未来只读巡检降为2路，无自动重试、活动35源不变。新可选批量收集/回执取回工具仅准备，3项完全mocked检查通过，实际收集/导出/oracle/最终CPU均0。21PDT材料按已核验状态冻结；最新费用快照18:24:45读得166.55184746，延迟计量非发票。

### 2026.10.13 18:40:27 PDT（本轮读取；启动核验收尾前）

已从原 submitted 回执确认8项T8均已首次提交；7项首16更新证明已存在，第8项原日志已越过首16更新。接下来只完成第8项一次启动核验及全8项只读状态快照，不重发模型、不重做已完成证明。

### 2026.10.13 18:03–18:15 PDT（T8首次提交及统计准备，读取时间见回执）

前三项T8已原调用提交，前两项实际H100首16更新核验通过，第四项正在预检。旧模型/输入/源码不重放或改动；9600修订是真实双审通过，原N2失败保留。新配对题目bootstrap核心6项合成检查通过，全18结果统计、图表和紧凑原字节证据发布工具仅准备、尚未执行。最终数字/图仍需实际结果G3。

### 2026.10.13 17:39–17:41 PDT（Claude交付）／17:52（读取与准入绑定）

Claude4edd8399：35源9600运行修订PASS-WITH-NOTES，全部8项修订后数值门PASS；原9530门FAIL保留。19源未来CPU仅代码PASS-WITH-NOTES，仍需全结果及实际I/O数值审计。预算旧显示标签用新不可变更正说明，原spec不改；补充记账失败只读保全、占位不清零流程已记录。正在准备原8项首次T8派发，尚无调用。

### 2026.10.13 17:24–17:29 PDT（最终 CPU 工程准备，非云运行）

新最终CPU19源在保留原21逻辑／24物理来源核验的基础上，显式核对T8原9560配置、新9600运行帽、原N2失败及40／5美分附加账本。19项新／修订离线检查通过；旧17源和学生35源字节不变。最终CPU仍需新代码审计、全部结果及实际I/O数值审计，实际输入／调用0；T8两项精确审计仍待回复。

### 2026.10.13 17:07–17:12 PDT（owner答复读取、工程准备与新外审收录）

owner直接批准原8T8各9600秒、总stage266.44；原N2 FAIL永久保留。新35源/独立运行帽与40美分追加记录准备，13项新CPU检查通过，原唯一claim防双跑，0云调用/上传。Claude453720b6真实完整报告已读：两补跑/图事实页/ag处理PASS；新精确运行及数值修订仍待固定版本审计。

### 2026.10.13 16:46 PDT（Claude交付）/16:48–16:49（读取与处理）

Claude b5c0a754独立从原包重建全部计时，确认8项原N2 **FAIL**；40秒/$0.40提案仅算术PASS，仍待owner及新确切准入。原失败保留；任何采用均披露为事后工程门偏离。审计关于超时概率及赶不上21PDT的判断不当作实测保证，按真实完成/核验状态冻结材料。


### 2026.10.13 16:36–16:41 PDT（核验与材料）

两替代全892文件/完整state/2638raw核验通过，多题969/多解965；原failed父保留。全部10T1+base齐备且资源退出。实际全主机N2预测9550.78–9551.68秒，原9530线未通过，T8调用0。补跑包、图表及数值提案送固定版本外审；9600秒/+$0.40仅有界提案，未授权。


### 2026.10.13 16:31 PDT（只读核对；事件时间另存）

两项原替代均已有 completed terminal 和原 result.json；当前实际容器 0。开始各一次原回执收集、完整 state/1319 raw 独立核验，不重发模型。新 Claude 62fb9c5b 完整报告已读取：原8 T1结果 PASS、T8代码 PASS、17文件最终CPU代码 PASS-WITH-NOTES；数值 N2/CPU I/O 门仍未关闭。


| 工作 | 负责人 | 状态 | 下一步 |
|---|---|---|---|
| 原 P007 四组实验 | Codex；Claude 审计 | 已完成；Claude **PASS-WITH-NOTES**，仅限报告列明范围 | 保留 base 解析敏感性、曝光及评测污染限定 |
| P007A 教师供给先导 | Codex；Claude 审计 | 已完成；紧凑计数/成本表 **PASS**；第五轮原始输出重评分 **PASS-WITH-NOTES** | 范围已扩展至教师原始输出；两个百分号解析差异不影响新token学生数据 |
| P007B 按真实时间计费的采购 | Codex | 四格本地核验完成；Claude 对零题价格记账 **PASS**、成本解释 **FAIL** | C-B1 已复现，不能将速度差直接归因于题价 |
| 首批两项学生 | Codex；Claude审计 | 两项完整核验完成：多题953/1319，多解969/1319；GPU均已退出；Claude结果PASS | 仅作为原时间计价先导，保留截断38/33条及其他限制 |
| 后六项原学生 | Codex | **未启动，已明确撤销** | 保留旧账本；新方案使用独立 campaign |
| 统一 token 计价修订 | Codex；Claude审计 | **8/8学生与14目录CPU证据链完整关闭，GPU/CPU容器0**；seed17零价963/950、高价927/952；seed23零价958/958、高价949/949（各/1319） | [完整事实/图表/局限](../reports/sft_allocation_midpoint_20261011/P007B_MIDPOINT_EVIDENCE.md)已齐备；Claude第十五轮最终包/事实页PASS；原图PASS-WITH-NOTES，图v2已获Claude PASS。首seed反转未被次seed重复；原CPU10项+续核4项，原失败保留 |
| P008 v3.1 | Codex工程；Claude审计；研究者 | 两完整采购G1通过；全部10项T1+base本地和外审核验通过，图表PASS，资源退出 | [完整T1事实与局限](../reports/p008_20261013/P008_T1_PROGRESS_20261013.md)；原T8计时门FAIL保留，owner已批准9600秒/$266.44，精确新运行／数值审计已通过，原8项均在运行且首16更新核验通过；最终CPU19源仅代码PASS，实际I/O数值待全结果 |
| 阅读材料 | GPT Pro | 分工已明确；本轮尚未收到可核验的 Pro 新交付 | 用户转交论文链接、关键证据和阅读结论后登记 |
| 独立审计与新增阅读 | Claude | 已收到第十五轮审计及39–42号新笔记；Codex已核查关键原文 | 按新证据版本继续审计；旧结论不自动覆盖新文件 |

预算：总额$500，项目支出上限$450，保护至少$50。当前P008阶段上限及保守预留$266.44（249.68+16.36+0.40），预留不是实际费用；原失败费用全部保留。最新平台延迟计量$162.31184746（23:36UTC读取），billed0，非发票／余额；残余加整阶段预留354.44140093。用户已直接取消有限学生19PDT截止，原队列按真实准入和剂量运行至完成；21PDT材料冻结不变，未完成标pending、后续单列。

## 时间线（追加记录，保留更正历史）

| 时间（PDT） | 执行者／来源 | 做了什么、得到什么 | 状态与证据 |
|---|---|---|---|
| 2026.10.13 15:51:48（原Volume/provider读取） | Codex | 同两项补跑末训练块各256updates/524287targets，连续保存656／528条评测，仍运行且无terminal | [保存进度](../reports/p008_20261013/REPLACEMENT_PROGRESS_1552.json)，非最终分数／全stateoracle；最终CPU17源代码固定63fee8e6待审 |
| 2026.10.13 15:44（代码准备完成、实际本地时间） | Codex | 新最终CPU17源覆盖21逻辑／24来源，23项离线检查通过；冻结LR字节与失败/替代身份严格核对 | [代码包](../reports/p008_20261013/final_cpu_replacements_preflight_v1/REVIEW_REQUEST.md)仅待审；原5美元slot无调用，实际I/O数值准入尚无 |
| 2026.10.13 15:39（准备开始） | Codex | 准备最终 CPU 的独立新入口，覆盖21逻辑实验／24实际来源及冻结学习率原始字节；保留两项零更新失败和两项独立补跑 | 仅本地工程准备；活动替代34源不变，实际CPU输入／I/O数值审核／调用尚未准入 |
| 2026.10.13 15:24（新审计/阅读检查）/15:28–15:29（费用刷新）/15:30（发布核实） | Codex | Claude35172ba9、Papers ea8befd5均无新；最新平台延迟计量153.88184242，P008标签65.86146319，残余加整阶段预留354.06037923 | 8项结果及T8代码固定860aa4cb经INDEX待审，74b89f2d普通push已核实；未来T8 helper仅准备，未调用 |
| 2026.10.13 15:12:14/15:18:42（补跑容器启动）/15:16:26/15:20:59（首更新核验）/15:21（原8项全部oracle完成） | Codex；原始证据 | 原8项10552输出/8完整state/剂量全部通过，8原回执只读恢复；两项独立补跑各首次真实训练。单collector错误有界修复完成 | [新事实页](../reports/p008_20261013/P008_T1_PROGRESS_20261013.md)；11项T8新准入检查通过（首NaN夹具预期范围错误保留），仅代码待审、不准入T8 |
| 2026.10.13 15:18（工程准备） | Codex | 8项原T1已完成，7项独立oracle通过、最后1项账本收集中；首补跑首16更新已独立核验，第二项原CLI首次准入检查中 | 准备未来T8专用双队列容量与运行时N2强制检查；不改活动34源或科学函数，不调用T8 |
| 2026.10.13 14:56:52（Claude评论）/15:04:20（完整读取） | Claude；Codex | 34源及两项补跑精确数值规格PASS，来源字节复核一致；两原失败保留，已恢复回执加独立COLLECTION来源标记；预算无需再问 | [限定接受](../reports/p008_20261013/student_lr_replacement_accepted_v1/DISPOSITION.md)；下一步运行时实时检查后各派发一次，N2仍OPEN |
| 2026.10.13 14:52:23（原云端快照）/14:54（回执取回） | Codex；原Volume/账本 | 8项原T1中的5项已终止完成并释放容器；5份原回执只读取回，0重提交；其余3项保存1088/1248/1248输出 | 完整账本、raw评分和完整state核验开始；不是最终分数或T8计时准入 |
| 2026.10.13 14:51（本轮开始） | Codex | 核对原云端保存的完成记录及资源状态，准备在原任务结束后恢复睡眠期间丢失的本地回执 | 只读取原证据，不重新提交；补跑34源确切审计仍待回复 |
| 2026.10.13 14:10:55（审计评论）/14:24（唤醒核查）/14:35后（代码准备） | Claude；Codex；原云端记录 | base638/1319获独立PASS；8个本地DNS断开但原云端8容器活跃，0重提交。两项授权补跑34源及完整谱系准备，20新CPU检查通过（初夹具错误保留） | [补跑确切审计](../reports/p008_20261013/student_lr_replacement_admission_v1/REVIEW_REQUEST.md)、[审计更正与睡眠核查](../reports/p008_20261013/review_f5a29c04_disposition_v1/DISPOSITION.md)；0补跑调用，N2未关闭 |
| 2026.10.13 13:54–13:57（直接答复收录、顺序恢复派发） | 研究者；Codex | owner批准两项各一次独立补跑及P008上限$266.04。另5次本地互斥拒绝核验为0worker调用，原未尝试槽位顺序完成首次提交 | [直接授权](../reports/p008_20261013/OWNER_STUDENT_LR_REPLACEMENTS.json)、[零调用对账](../reports/p008_20261013/student_predispatch_lock_reconciliation_v1/DISPOSITION.md)；8项原T1已提交，替代源码/谱系仍待审，N2不豁免 |
| 2026.10.13 13:38:34（base退出）/13:46:38（oracle完成）/13:50–13:51（T1派发） | Codex；原回执/完整oracle | base全1319raw独立重评分638正确、41长度上限计错；LR修订首项16更新绑定核验后，余7项各原CLI派发一次 | [base完整证据](../reports/p008_20261013/base_v1/README.md)、[T1派发事实](../reports/p008_20261013/T1_FROZEN_LR_DISPATCH_2051.json)；旧两失败保留，替代预算直接确认待答，T8仍不准入 |
| 2026.10.13 13:34（Claude评论）/13:42–13:44（读取与接受） | Claude；Codex | 固定32源LR修订PASS，8项尚未尝试T1获准；base13:38:34退出，独立收尾开始 | [限定准入](../reports/p008_20261013/student_frozen_lr_accepted_v1/DISPOSITION.md)；失败替代尚未准入，旧计时名单保留，N2仍OPEN |
| 2026.10.13 13:24:35（原只读保全完成）/13:30（发布） | Codex | 两项失败原8文件、完整账本、provider停止、前后清单及SHA全部核验；均0update/0endpoint/0unknown，计费与失败保留 | [完整失败处置](../reports/p008_20261013/student_lr_failures_closed_v1/DISPOSITION.md)；base继续，16未尝试项等修订审计；失败重试未准入 |
| 2026.10.13 13:12/13:13（失败）/13:15–13:24（独立诊断与修订） | Codex；实际原日志及Linux主机 | 两项学生在训练前严格LR比较失败；Linux余弦重算与原冻结值差最多1.36e−20；base正常，冻结原始LR不改 | [仅未尝试项修订](../reports/p008_20261013/student_frozen_lr_amendment_v1/REVIEW_REQUEST.md)；7项新CPU回归检查通过，完整失败保全仍进行，无自动重试 |
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


## 2026-10-14 00:09:33 PDT — new exploratory follow-up prepared, zero cloud calls

Direct owner approval authorizes exactly base4shot, official generalInstruct0shot and one wrong-teacher student, $30 total, each once/no retry, Claude code/data review first. P008 and its immutable materials remain closed; p007 stays paused. D1 original frozen eligibility yields864; first429 from101questions selected, versus correct-control429from429 and969/1319. First4reserveddev examples and all1319 prompt IDs fit2048 with512new; original256LR and schedule yield524287targets. Thirteen new CPU fixtures pass. New37source package and I/O helper prepared; no image/upload/function calls. Read reports/exploratory_20261014/REVIEW_REQUEST.md.

Motivation: owner-requested post-result exploratory controls; coverage/length/exposure confounds explicitly disclosed. Failures: first billing CLI range month rejected, emptyJSON read failed; corrected this month GET saved independently. Capacity helper signature fixed before tests; prepublication oracle metadata/weight binding tightened with two new fixtures (prior11 not rerun). Papers remains ea8befd5. No old oracle/tests/models rerun. Budget $24.78 worker envelopes+$5.22 nonworker reserve; newproject conservative envelope384.09574154<450, delayed meter notinvoice.


## 2026-10-14T07:26:20.495901+00:00 / Oct14 00:25 PDT — exploratory exact review accepted

Claude5f64cb77 fullreport PASS-WITH-NOTES binds37sources/spec/input/I/O; N2 localtransformers4.56.2 confirmed. Existing969/965 references will be descriptive; reviewer AI label judgments are not new Codex labels or scoring corrections. Upload/three once-only scientific calls now admitted subject to original runtime guards. No old work repeated; p007 stays paused. Read-only log lookup initially used nonexistent root RUN_LOG.md, then located the actual midpoint log; no mutation or scientific failure.


## 2026-10-14T07:47:55.539910+00:00 / Oct14 00:48 PDT — all three exploratory calls running

One original call each: base07:36:25UTC, Instruct07:40:44UTC, wrong student07:44:47UTC. Startup readback07:46:23 confirms three H10080GB, exactsource37/config/claim and official Instruct weightSHA. Serialized15-file input transfer/readback complete, no retry. GPU generation logs alone do not establish final result or exact total ETA; complete raw/state oracle and STOPPED0 still required. Original6001-second hardcaps, $30 envelope, no extra runs, p007PAUSED. See reports/exploratory_20261014/started_v1/README.md.


## 2026-10-14T07:59:45.126788+00:00 / 2026-10-14 00:59:45 PDT — exploratory timing risk and isolated proposal

Original three calls continue; no retries or hot changes. Saved ack intervals show base72–100seconds per16 and initialInstruct174seconds, so prior ETA was optimistic and original6001caps may prevent complete endpoints. New local64lookup diagnostic identifies repeated len(tokenizer) as a likely substantial overhead, not fully isolated cloud timing. Unapplied cache proposal passes4new edge cases and32saved stop-event comparisons with no scoring/generation. Live37source unchanged. Owner stop/preserve versus original-cap question pending; no additional-call authorization. reports/exploratory_20261014/vocab_cache_proposal_v1/README.md.


## 2026-10-14T08:08:03.242940+00:00 / 2026-10-14 01:08:03 PDT — owner-stopped exploratory calls; preservation active

Owner explicitly approved stopping the three original calls and preserving their saved evidence/checkpoint, then preparing a repair for review. Exactly three app-stop commands succeeded at08:05:16–18UTC; independent provider read08:05:47 found allSTOPPED/0containers. Original callbackerrors retained and CLIexit1 consumed once. No repeat scientific call, livepatch, newbudget or remoteclaim writes. Once-only read-only preservation89666 active, two readers plus one campaignledger snapshot, create-only files and bounded1200local seconds; no completed-onlycollector or full endpoint claim. Newcacheproposal remains unapplied, old4fixture+32saved-event checks are not repeated. Reflection: generation-only seconds omitted costly checking overhead; the earlier ETA was too optimistic, and actual immutablebatchintervals triggered the explicit owner stop decision before the original caps.


## 2026-10-14T08:15:10.130913+00:00 / 2026-10-14 01:15:10 PDT — all three original exploratory calls stopped and preserved

Ownerstop commands08:05:16–18UTC and independent exactprovider08:05:47 show3STOPPED/0containers. Originalcallbacks consumedexit1 and original3failedterminals retained. Once-only preservation89666 completed08:11:48:690files/231420287bytes, before/after Volume lists identical, one campaignledger. New local reconciliation82166 completed08:12:18: base272raw/256ack,Instruct144/128,wrong80/64; eachlast16savedbutunacknowledged,0attemptedmissingraw. No independent endpointdecode/rescore orpartialaccuracyclaim. Originalwrongfullcheckpoint45d38712 loadedonce,256updates/524287targets/16blockacks/frozenLRschedule/finiteoptimizer andRNG verified,0newtraining/restore. Source37 untouched.

Three interruptionstacks pinpoint repeatedlen(tokenizer) inreferencevalidation; earlier4cachefixtures/32savedeventchecks notrerun. Exactunappliedproposal1a3c910e alreadyINDEXpending, no future runtime/continuation admission. Newstoppedpreservationpacket contains originalcompact evidence without.pt/privateintent; alloriginalhashes andstateproof retained. Poststop08:08delayedthree-appmeter5.43330865/workspace230.53207550, notinvoice/finalcost/balance; residual+fullP008266.44+fullnew30=384.84256089<450 with50protected. Allfailure/setup/download/storagecosts retained; no additional budget. p007staysPAUSED.


## 2026-10-14T08:18:54.684610+00:00 / 2026-10-14 01:18:54 PDT — repair proposal code PASS; original calls remain stopped

ActualClaude0b63a809 reportSHAe68a609f read08:16:26UTC/event08:04:07 gives PASS only to isolatedcacheproposal1a3c910e. VOCAB_CACHE_PROPOSAL_CODE_ACCEPTED binds exactsource/diff/report, no executablecontinuation/retry/newbudget. Reviewer earlier continue-to-cap suggestion does not override directownerstop. Reviewer partialcount/CI projections are not observedresults or adoptedanalysis; removingin-workeraudit is notimplemented. Stoppedpreservationpacket fixedbdf2ffd36ffe07ac94b7cd5c03290f0a20092c1d newlyrequested independentreview; no newruntimeadmission.

Initialpacketcommit omitted ignored.tar.gz; caught beforepublication, added exactarchive in a separatecommit, allGitmanifestbytesverified. Acceptancepacket wascompleted before an INDEX write failed because common.dump is create-only; error preserved, only still-unwritten mutable INDEX/docs tail completed afterward. No packetbuilder/recollection/oracle/test repeat, all37sciencefilesunchanged. Alloriginalfailedclaims/fees/Volume remain.


## 2026-10-14T09:04:55.227031+00:00 / October14 02:04 PDT — continuation authorization status clarified

The README now reflects the owner-approved evaluation-only continuation and separate finite overnight monitor. Exact47-source/runtime-numeric review remains pending; no new cloud call/upload/image or repeated scientific work. Latest review branch ea518a9f contains a Pro-response/adjudication follow-up only. Its prefix-conditional scientific readings are not full1319 results or causal evidence; no labels, parser, arms or doses were changed. Original690-file preservation,496-prefix oracle and15 continuation checks remain DONE. No new permission is needed; the remaining prerequisite is the actual exact-scope external review.


## 2026-10-14T09:22:29.013248+00:00 / 2026-10-14 02:22:29 PDT — exact exploratory suffix review accepted

Real Claude ae553bd2 fullreport read2026-10-14T09:21:32.596179+00:00, event09:17:43UTC: PASS-WITH-NOTES exact47source/spec154a7f83/prefixbfc786ca/budget36b7ea56. Three remaining suffixes admitted subject to unchanged live guards. N1 student-first/4800cap and residual-time uncertainty retained; N2 prefix-results-viewed disclosure required; N3 failedparents and48unacknowledged saved outputs retained. Reviewer14/15 with torch unavailable, existing Codex15/15 not rerun. No newscience/dose/budget/source changes; no childcall yet. Original parentsSTOPPED0, no upload or weight redownload. p007paused, separate finiteovernightmonitoractive.


## 2026-10-14T09:45:58.823020+00:00 / 2026-10-14 02:45:58 PDT — all three suffixes running and first acknowledgements verified

Exact47source remains accepted68c8bad5, execution4e6beb52. Original CLI51624student/32851base/52223Instruct eachsubmitted once; startup35993/89564/9906 allDONE, no retraining or saved-prefix overlap. Actualentries09:32:55.782/09:38:05.909/09:42:43.060UTC, hardstops10:52:55.782/10:58:05.909/11:02:43.060UTC. Inspector51769DONE read2026-10-14T09:44:34.738133+00:00:3ownedcontainers,3claims, no terminal/result/callbackerror; saved suffixacks304student/400base/48Instruct, not partialscores or finaloracle. Next stable provider about30min later. Real firststudentbatchtiming31.859/24.721s withaudit0.243/0.252s; no futurecompletionguarantee. Gate48858, inputreuse, firsttiming84654 allDONE, neverrepeat. No new model/image/input upload/checkpoint training beyond these admitted3calls. Data/weights alreadyonVolume, codeimage prepared normally. LatestPapers09:32 samee097b0cb. Privatepublisher reporttext now explicitlydiscloses pre-completion prefix score exposure, remainsNOTRUN.

### 2026-10-14 11:54:48 PDT（P009 A0实际报告与两条预输出定义）

实际报告e1d8d469/comment6175549931事件18:35:06UTC，完整读取18:49:40.942572UTC；总体PASS-WITH-REQUIRED-CLARIFICATIONS，Stage0输入PASS，不是runtime准入。R1固定S1 Stage1只用attempt01自身正确且格式合格，2–4次不得救资格；NC/S2源数据可到8次的差异披露。R2固定D从原seed17未按正确性筛选题序第一题起买、格式失败照收费；B上限包括遍历跳过题所有已尝试费用，A/B同P_nat。上述不改五组/剂量/100总帽。新补充包f1e6abd9de4d26150a33c285989236c663ed1acc共9成员逐Git字节核验、17资源tar回读；原15输入和P0源19未改。

原审计未取得OLMo编码/完整dev候选，现附原分词器配置/卡和7个MATH原test分片。新本地BOS诊断2638默认/显式no-special/原存token均一致，0前导BOS；未下载权重/生成/评分。短示例4shot仅描述，不加3072实验。N3单批2美元是非阻塞建议，实际248cent/四prefix批P0精确方案另审，没把两者混成PASS；DESIGN/RUNTIME_ACCEPTED均未造。两个只读路径假设错误（review请求文件和INPUT_MANIFEST文件名）未写科学产物，改用实际目录；保留工具记录。新p009ACTIVE，旧两monitorPAUSED，0P009云调用。

### 2026-10-14 12:01:41 PDT（P009未来完整答案训练计划候选，独立于P0）

为减少后续训练准入等待，准备纯CPU计划/校验器；直接复用P008已发布1024LR向量14ac59d2及原文件cb9c2e04，不重算hostcos，不重启旧模型。固定1024updates/2097148targets、seed17/29、所有所选答案至少一次、q/q+1、完整EOS/遮罩/context2048；旧q0桥接与0.1%降量不继承。7新fixtures先通过；随后补整数metadata拒绝并只运行新增第8fixture（其setup也用最终源构造完整合成计划），不冒充最终源重跑全部7或真实训练。原两日志保留；实际学生数据计划/runtime/GPU均未建立。

新immutablepacketc23ed87558685f152b2c03b4af9a75cef6c18ca7的13成员已逐Git字节核验；请求p009-training-plan-code-r1只挡未来计划代码，不挡P0。源snapshot保原字节，style检查排snapshot并准确限定。独立审计待真实反馈，0新增科学/收费调用。只读查找先猜不存在frozen_lr.py和zsh空glob失败，随后用rg实际文件定位，无写科学产物。旧两巡检PAUSED，新p009ACTIVE。

### 2026-10-14 12:08:26 PDT（P009 P0确切运行/首次测量例外通过，准备单次派发）

真实Claude0fabdde8完整bb/bc报告19:05:51读取、comment事件18:55:02。bb明确19source/spec cdb52f9b/248cent/1200worker/每role首4完整prefix批例外PASS-WITH-NOTES，并明确将原A0对Stage0限定为PASS-WITH-NOTES；原整体required-clarifications与后续R1/R2审计仍保留。已保存真实DESIGN_ACCEPTED/RUNTIME_ACCEPTED，没修改旧源或造PASS。bc仅候选评分代码PASS，实际P1尚缺；fallback超过2%须固定hash最多25人工/AI抽查、报告无bracebox/不支持gold与计时，长期进程池建议尚未实现，不能代替审计。

必要新费用快照19:06:28阶段请求已完成，workspace235.101855delayed/billed0；保守近高235.6920755加25lag估计，再加新100=360.6920755<450（账本向上取整360.70），不称invoice/balance/严格上界。P0单slot248c在Stage0$10内，失败费用/旧claim均保留。原1024LR新纯计划候选c23ed875、bootstrap method预输出冻结e5c79962、duplicate925canonical预正确性选择defba927均不更改P0源19；后两无实际统计/模型输出。

此条记录时0P009云调用；之后一次上传/回读/真实source/provider/无旧claim检查满足才提交ONLYmodal_p0。估计500–1300秒和EOS行为为reviewer预计，不是实测保证；若失败只保全原尝试，禁止自动重跑。

### 2026-10-14 12:18:30 PDT（P009 P0原调用进行中；MATH持久进程池候选）

原P0 CLI43936于19:09:26UTC仅调用一次，应用ap-laRv7V5oQp7J6kKZdPolnd已建，镜像构建结束后仍在派发前检查；本条读取尚无canonical submitted/result/error，不把CLI启动当GPU生成。原3文件上传75218及readback/gates已DONE，不重复。live19源与标量MATH源均原字节保留。新只读provider/4已知账本key核对46752进行中，不枚举全部旧账本或产生模型调用。

为解决bc-N1每题重复import耗时，新独立两进程池准备完毕：原symbolic/decide不改、每进程主线程2秒alarm/父8秒外帽，启动等待不挤占其他活动任务的外帽；exact(gold,extractedanswer)含失败只算一次，每原row身份/stop/来源保留。8新合成检查（含真实固定依赖进程）一次PASS；旧11测试/真实输出评分均未重跑。包0b714161dcc23a93cc44b52f4948eae271eaeb27的12成员逐Git字节核验，请求仅新CPU调度代码；实际P1首100计时、durabledriver、50分歧与>2%fallback抽查仍未执行。

几次只读路径查询命中了不存在的audit目录、docs/RUN_LOG和猜测helper/request名称，未修改科学产物；改用实际reports/p007_audit/INDEX与reports/sft_allocation_midpoint_20261011/RUN_LOG。无需新owner许可，后续严格真实审计和科学门。

