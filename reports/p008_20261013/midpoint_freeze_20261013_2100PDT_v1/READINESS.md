# P008 中期材料冻结：2026年10月13日21:00 PDT

冻结截止为2026-10-14 04:00 UTC；记录实际写入时间见FREEZE.json。没有延长材料截止，原有限计算“直到完成”的授权继续覆盖必要核验。此目录为不可变快照，后续审计和CPU结果单列更新。

## 已完成

- 18项逻辑学生、74训练单位及base全部计算完成，25,061个终点评测输出完整本地核验，0技术unknown；完整state/剂量/claim/失败谱系证据保留，资源均已释放。
- 全19模型、31个注册/汇总对比及3张图已生成并实际检查可读；全部点估计和区间保留，见FACTS_AND_LIMITS.md、ALL_CELLS.csv、ALL_CONTRASTS.csv。
- T1和base外审通过，8项T8已有7项独立G3通过；公开stateSHA不等于外审读取了私有binary。
- 原P007B已核验事实、图和局限继续作为中期证据，独立于P008，不当第三采购draw。

## 截止时待定

最后D2/p4 depth结果（990/1319，36caps）的G3、完整注册统计/三图G3，以及最终CPU完整性核验尚待各自审查。CPU已冻结24physical/21logical输入，数值提案只是代理预测，尚未上传或调用。03:59:17UTC最后读取审计分支仍为3c15e24c。统一secondaryparser-v2未在学生结果前完成独立审查，按协议标pending；不选择性修正主分。

## 必须保留的解释范围

两采购draw的点估计不同，不声称稳定统一赢家或等效。区间只针对固定模型/语料/已见题目的逐点配对重采样，不代表训练seed或采购总体不确定性，也无familywise覆盖承诺。B与T沿主路径同时增加；缺少B1/T8角，不能识别完整B×T交互或独立归因。原N2门真实FAIL与随后在T8结果前批准的9600秒事后工程修订永远披露。所有失败父、替代和setup/storage费用保留，266.44美元为预留而非实际发票。

## 固定证据入口

- [P007B_MIDPOINT_EVIDENCE.md](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/sft_allocation_midpoint_20261011/P007B_MIDPOINT_EVIDENCE.md)
- [P008_T1_PROGRESS_20261013.md](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/p008_20261013/P008_T1_PROGRESS_20261013.md)
- [P008_T8_PROGRESS_20261014.md](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/p008_20261013/P008_T8_PROGRESS_20261014.md)
- [REGISTERED_PRIMARY_VISUAL_CHECK_0347.json](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/p008_20261013/REGISTERED_PRIMARY_VISUAL_CHECK_0347.json)
- [MANIFEST.json](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/p008_20261013/review_2a236343_accepted_v1/MANIFEST.json)
- [MANIFEST.json](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/p008_20261013/review_3c15e24c_accepted_v1/MANIFEST.json)
- [MANIFEST.json](https://github.com/Townzc/2P1R_Reasoning_Post/blob/72e15f74d135568a583b631756b24dd0e1ced144/reports/p008_20261013/final_audit_t8_cap_proposal_v1/MANIFEST.json)

三张PNG及表格直接复制已发布原字节，没有重跑模型、oracle、统计或绘图。费用快照实际读取03:19:49UTC，为延迟计量，非invoice或余额。
