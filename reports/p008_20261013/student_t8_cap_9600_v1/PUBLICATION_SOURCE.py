from pathlib import Path
import ast,shutil,json,datetime
from experiments.sft_allocation_midpoint.common import read,dump,digest,sha,manifest,verify
r=Path('.local/p008_20261013/main_r1');private=r/'t8_cap_9600_r1';p=Path('reports/p008_20261013/student_t8_cap_9600_v1');now=datetime.datetime.now(datetime.timezone.utc).isoformat()
spec=read(p/'ADMISSION.json');assert spec==read(private/'AMENDMENT.json')
module=Path('experiments/sft_allocation_p008/modal_students_t8_cap.py');tree=ast.parse(module.read_text());names=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in x.targets));source={n:sha(n) for n in names};assert len(source)==35
for n,h in read('reports/p008_20261013/student_t8_runtime_preflight_v1/SOURCE_BUNDLE.json').items():assert sha(n)==h
dump(p/'SOURCE_BUNDLE.json',source)
old=spec['original_failed_timing_proposal'];numeric=dict(schema='p008_t8_approved_cap_reapplication_v1',original_proposal_digest=digest(old),spec_sha256=digest(spec),original_N2_passed=False,post_hoc_engineering_deviation=True,
    measurements_reused_unchanged=True,formula_and_20percent_margin_unchanged=True,new_model_calls=0,
    all_eight_runs=spec['runs'],original_cap_seconds=9560,original_threshold_seconds=9530,new_cap_seconds=9600,new_threshold_seconds=9570,
    predictions={n:dict(frozen_with_margin_seconds=old['predictions'][n]['with_margin_seconds'],new_threshold_seconds=9570,
       passes_amended_arithmetic=old['predictions'][n]['with_margin_seconds']<=9570,
       headroom_seconds=9570-old['predictions'][n]['with_margin_seconds']) for n in spec['runs']},
    external_numeric_review='pending',runtime_admission=False,additional_reservation_cents=40,stage_cap_cents=26644)
dump(p/'NUMERIC_REAPPLICATION.json',numeric)
shutil.copyfile(private/'tests_r1.log',p/'CPU_TESTS.log')
shutil.copyfile(private/'prepare_sources.py',p/'PREPARATION_SOURCE.py')
shutil.copyfile(Path(__file__),p/'PUBLICATION_SOURCE.py')
(p/'REVIEW_REQUEST.md').write_text('''# Blocking: exact 9,600-second T8 amendment, source and numerical admission

The owner directly approved the unchanged eight unattempted T8 slots at a 9,600-second worker cap and a $266.44 P008 cap (additional $0.40). The original all-eight N2 criterion failed and remains immutable at 8e1b3463; this is explicitly a **post-hoc engineering deviation**, not a retrospective original-gate PASS. Claude b5c0a754 independently reproduced the failed formula and checked the proposed arithmetic. The new exact implementation and amended numerical admission still require this scoped review.

## Exact implementation

Only `experiments.sft_allocation_p008.modal_students_t8_cap::main` may run this version. Its 35-source bundle preserves all prior runtime files and the original scientific `frozen_lr_block_student_runtime.run` call. All 19 original configs, input bytes, original plan, source admissions, failed N2 data and failed history remain immutable. The config's historical `max_seconds=9560` remains visible in recipe identity; the separate, explicit reviewed operational spec/intent overrides only the worker cap to 9600. Worker timer starts at function entry, soft work cutoff 9570, platform timeout 9660, startup600, local complete-window10300. No additional model/dose/evaluation call is introduced.

The SAME original campaign/run claim is acquired through the SAME RunGuard before any scientific work. An old or new competing worker loses this atomic claim. No migration, retired-slot recreation or updated registered plan is involved. An immutable global supplement record reserves the approved40cents; after winning the original claim, each worker records its5cent supplement bound to that claim. Any partial/conflicting record blocks replay. The original1253cent reservation and receipt remain; intent/result separately report the5cent supplement and total1258. Neither amount is a provider invoice. Full conservative workspace meter162.31184746 plus the entire266.44stage deliberately double-counts already-spent P008 and is428.75184746<450. Failed/setup/storage costs are retained.

The supplementary records add bounded setup/end bookkeeping; the unchanged per-block/evaluation guard read path has no new reads. This extra setup is not empirically benchmarked and is not silently subtracted from timing. There is no guarantee that a future host fits; actual workers stop at their hard cap. The new source/numerical audit must assess this limitation.

Both queues continue to share the original dispatch lock; pending/unknown/unmatched containers count toward max8. Canonical local receipt and remote claim/intent/terminal/unit/directory absence are checked before spawn. Exact13 T1/base terminal dependencies are re-read. No new input upload. All training/scoring rules,2048updates4194296targets,seed17,1319greedy endpoints and1024forensic checkpoint stay fixed.

## Required independent decisions

1. Source/runtime: check exact35source/spec/owner authority, unchanged science and real historical G1 records, original shared claim and create-only supplementary accounting, failure behavior, finite timer/reservation and concurrency. Historical source PASS cannot admit this new entry.
2. Numerical: compare every unchanged forecast and all host/failed provenance to the original failed proposal; apply9570 uniformly. Expected9550.77764–9551.68345 gives18.31655–19.22236seconds headroom. This is only an amended engineering criterion, not a statistical/timeout probability guarantee. Two separate scoped acceptance records must name this exact source and spec, and preserve original_N2_passed=false.
3. Independent local oracle: `scripts/audit_p008_student_t8_cap.py` verifies the original scientific data/state/dose chain plus exact amended operational cap and linked5cent reservation. Originalreceipt1253+supplement5=1258 is explicit, no expense inference.
4. Thirteen new in-memory CPU checks cover both scoped reviews, all-eight configs, mutated authority/input/cap/budget, complete failed-host provenance, shared claim races and partial-claim no-retry behavior. No old oracle/test/model work repeated.

Preparation has made zero cloud images, calls, uploads or ledger mutations. The21PDT material freeze remains; unfinished work is pending/later separately reported. Final CPU will need the actual new T8 operational provenance in its admission; old numerical CPU admission does not exist.
''')
dump(p/'STATUS.json',dict(utc=now,status='OWNER_APPROVED_PREPARED_EXTERNAL_RUNTIME_AND_NUMERIC_PENDING',source_files=len(source),spec_sha256=digest(spec),new_cpu_checks=13,original_N2_passed=False,post_hoc_engineering_deviation=True,stage_reservation_usd=266.44,new_cloud_calls=0,new_uploads=0,new_remote_writes=0))
dump(p/'MANIFEST.json',manifest(p))
# Record the newly read real result/figure/disposition audit without rerunning any scientific oracle.
rec=read(r/'review_453720b6/READ_RECEIPT.json');o=Path('reports/p008_20261013/review_453720b6_accepted_v1');o.mkdir(exist_ok=False)
shutil.copyfile(r/'review_453720b6/REPLACEMENTS_FIGURE_DISPOSITION.md',o/'REPORT.md');shutil.copyfile(r/'review_453720b6/READ_RECEIPT.json',o/'READ_RECEIPT.json')
proof=dict(utc=now,review_commit=rec['review_commit'],review_report=rec['report'],review_report_sha256=rec['sha256'],target_commit='8e1b346378db22b98608b59a333d2ba6be7e4644',replacement_G3='PASS',figure_and_facts='PASS',ag_disposition='PASS',external_binary_state_inspection=False,reviewer_descriptive_CI_suggestion='Not adopted as final analysis; no independent Codex CI calculation in this step',new_model_calls=0,new_raw_oracle_calls=0)
dump(o/'ACCEPTED.json',proof);dump(o/'MANIFEST.json',manifest(o));dump(r/'T1_REPLACEMENTS_AND_FIGURE_REVIEW_ACCEPTED.json',proof)
i=read('reports/p007_audit/INDEX.json');i['as_of_utc']=now
for req in i['review_requests']:
 if req['request_id'] in ['p008-two-t1-replacement-outcomes-r1','p008-t1-figure-and-facts-r1','p008-review-ag-disposition-r1']:
  req.update(status='reviewed',external_review='PASS',review_commit=rec['review_commit'],review_report=rec['report'],review_report_sha256=rec['sha256'],review_read_utc=rec['read_utc'],scope='Full report scoped result/figure/disposition; public state SHA not external binary read; no new T8 admission')
i['p008_v31'].update(status='all_T1_G3_and_figure_PASS_owner_9600_26644_approved_exact_runtime_pending',stage_cap_usd=266.44,hard_reservation_usd=266.44,active_gpu_tasks=0,student_T8_calls=0,student_T8_numeric_admission='Original9530criterionFAIL preserved; owner approved9600/9570 amendment; exact runtime/numeric review pending',latest_engineering_packet=str(p),current_status=str(p/'STATUS.json'))
Path('reports/p007_audit/INDEX.json').write_text(json.dumps(i,ensure_ascii=False,indent=2)+'\n')
f=Path('reports/p008_20261013/P008_T1_PROGRESS_20261013.md');text=f.read_text();text+='\n\n更新（10月13日17:12 PDT收录）：Claude453720b6对两补跑G3、此图/事实页、ag处理均PASS；公开state SHA不等于外审读取binary。全部10项T1现有外审覆盖。owner已直接批准T8改9600秒/$266.44；原9530计时门FAIL不改，新确切source/spec/数值准入仍待审，T8尚无调用。审计建议的描述性CI未直接采用为冻结最终分析。\n';f.write_text(text)
w=Path('docs/WORKBOARD.md');text=w.read_text();marker='## 当前状态\n';text=text.replace(marker,marker+'\n### 2026.10.13 17:07–17:12 PDT（owner答复读取、工程准备与新外审收录）\n\nowner直接批准原8T8各9600秒、总stage266.44；原N2 FAIL永久保留。新35源/独立运行帽与40美分追加记录准备，13项新CPU检查通过，原唯一claim防双跑，0云调用/上传。Claude453720b6真实完整报告已读：两补跑/图事实页/ag处理PASS；新精确运行及数值修订仍待固定版本审计。\n',1);w.write_text(text)
entry=f'\n\n### {now} — Direct cap/budget authority and exact35-source preparation\n\nOwner directly approved9600seconds and266.44stage. Preserve original all8N2FAIL and scientific recipe max_seconds9560 as historical identity; new separate operationalcap is9600,30softmargin/20%forecast unchanged. Same original registered plan/claim prevents any old/new duplicate; immutable global40cent supplement and5cent per-winning-claim record, no budget recycling.13 newCPUchecksPASS; no oldmodel/test/oracle reruns,0cloudcalls/uploads/writes. Newlocaloracle binds operationalcap+supplement and existingraw/fullstate/dose. Addedsetup/end metadata is unbenchmarked; oldper-blockguard unchanged, predictionnotguarantee. Read full453720b6G3/figure/dispositionPASS, preservedscope and noexternalbinaryclaim; reviewerdescriptiveCI suggestion notsilentlyadopted. Papers00:10still ea8befd5, noProdelivery. Exactruntime/numericreview pending, originalT8N2_ACCEPTED remainsabsent. Reflection: ownerauthority changes the bounded engineering limit, not the historical failedcriterion or scientific target.\n'
for n in ('reports/sft_allocation_midpoint_20261011/RUN_LOG.md','AI_USE_LOG.md'):
 with Path(n).open('a') as h:h.write(entry)
print(json.dumps(dict(packet=str(p),sources=35,spec_sha256=digest(spec),new_calls=0)))
