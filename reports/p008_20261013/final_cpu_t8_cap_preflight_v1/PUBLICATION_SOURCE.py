from pathlib import Path
import ast,datetime,json,shutil
from experiments.sft_allocation_midpoint.common import read,dump,sha,manifest
r=Path('.local/p008_20261013/main_r1')
p=Path('reports/p008_20261013/final_cpu_t8_cap_preflight_v1')
if p.exists():raise ValueError('Immutable code packet already exists; no repeat publication')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
module=Path('experiments/sft_allocation_p008/modal_audit_t8_cap.py')
tree=ast.parse(module.read_text())
names=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in x.targets))
source={n:sha(n) for n in names};assert len(source)==19
for n,h in read('reports/p008_20261013/final_cpu_replacements_preflight_v1/SOURCE_BUNDLE.json').items():assert sha(n)==h,n
for n,h in read('reports/p008_20261013/student_t8_cap_9600_v1/SOURCE_BUNDLE.json').items():assert sha(n)==h,n
p.mkdir()
dump(p/'SOURCE_BUNDLE.json',source)
shutil.copyfile(r/'final_cpu_t8_cap_tests_r1.log',p/'CPU_TESTS.log')
for name in ('test_p008_audit_t8_cap.py','test_p008_final_cpu_entry_guard.py'):
 (p/'tests').mkdir(exist_ok=True);shutil.copyfile(Path('tests')/name,p/'tests'/name)
for name in ('prepare_final_audit_t8_cap.py','upload_final_audit_t8_cap.py','collect_final_audit_t8_cap.py'):
 ast.parse((r/name).read_text());shutil.copyfile(r/name,p/name)
shutil.copyfile('scripts/p008_final_cpu_guard.py',p/'p008_final_cpu_guard.py')
shutil.copyfile(__file__,p/'PUBLICATION_SOURCE.py')
(p/'REVIEW_REQUEST.md').write_text('''# Future final CPU: exact operational T8 provenance

Code-only review requested. This does not block the separate T8 runtime/numerical review or create any CPU admission. The original final audit remains a single500-cent slot,4CPU/16GiB,2readers,3300seconds from worker entry,3500platform/600startup/full4000local window, no GPU/controller/retry. All21 logical/24 physical sources remain, including the failed D2 parent and two failed zero-update students. No cloud image, input freeze/upload, probe or function was executed.

The owner-approved T8 amendment preserves original config9560 and claim/plan identities while enforcing operational9600 with a separate global40-cent and per-run5-cent reservation. The former17-file CPU implementation did not explicitly inspect this newly introduced provenance. The19-file candidate preserves every former runtime file byte-for-byte, replaces only the entrypoint in the source roster, and adds two modules: audit_cap_binding and audit_t8_cap_records.

The new binding first performs every existing24-source/21-label integrity check. It additionally requires the exact published4ca2c55d amendment, all eight original claims and immutable supplements, archived intent JSON **file bytes**, matching35-file T8 source, both real runtime and numerical reviews, original_N2_passed=false, post_hoc_engineering_deviation=true, originalconfig9560/2048updates4194296targets, effective9600, originalclaim9630deadline, original1253-cent receipt and separate5-cent reservation/result1258. Reservations remain distinct from invoices. The original failed9530 criterion and all-host forecast are unchanged.

The CPU independently rereads all nine immutable cap records before admission and again after completing its source proofs. It compares the actual compact archive's intent/admission to the bound provenance after the original per-file hashes and complete-state checks. No new raw scoring or inference is claimed. Existing full256/1024/2048 state checks remain unchanged. Prior reviewer six torch fixtures were not executable in that environment; this new suite does not imply they were executed or repeat the earlier23 tests.

Nineteen new/revised offline checks passed once:16 cap-provenance refusal checks and3 revised sole-entry guard checks. They use only synthetic in-memory reviews/claims, never trusted acceptance files or model calls. The local current-entry guard now refuses all three historical CPU entries. Only modal_audit_t8_cap may eventually run this queue. Source-PASS from the former17-file bundle cannot authorize the new19-file source.

Three local helpers are prepared and parsed, not run. Freeze requires all24 real terminal/oracle/STOPPED0 proofs and new exact CPU_T8_CAP_CODE_ACCEPTED. It reads the original collected ledgers and intent bytes; it never synthesizes evidence or changes original claims. The I/O proposal must include actual all-source bytes and real timing evidence. New CPU_T8_CAP_NUMERIC_ACCEPTED must bind that proposal, the exact amendment and actual nine ledger records, explicitly retaining the original failed gate. Bounded added metadata reads are not empirically benchmarked or subtracted from timing; actual numerical admission remains pending until the future complete inputs exist. No actual final_audit_t8_cap_r1 or ADMISSION/FINAL_IO_GATE exists yet.

Please review the complete19-file binding/entry, actual compact-read checks, supplemental remote rereads, original failed-lineage preservation, sole-entry guard, finite limits and helper code. A review can accept code only; future real numerical admission remains independent. Student source35, source reviews, inputs and science have not changed.
''')
dump(p/'STATUS.json',dict(utc=now,status='PREPARED_CODE_ONLY_EXTERNAL_PENDING',runtime_source_files=19,
 exact_new_or_revised_cpu_checks=19,scientific_models_called=0,cloud_images_built=0,cloud_cpu_calls=0,uploads=0,
 logical_sources=21,physical_sources=24,original_cpu_slot_cents=500,actual_inputs_exist=False,
 runtime_admitted=False,external_review='pending',blocks_T8_students=False))
dump(p/'MANIFEST.json',manifest(p))
w=Path('docs/WORKBOARD.md');text=w.read_text();text=text.replace('## 当前状态\n','## 当前状态\n\n### 2026.10.13 17:24–17:29 PDT（最终 CPU 工程准备，非云运行）\n\n新最终CPU19源在保留原21逻辑／24物理来源核验的基础上，显式核对T8原9560配置、新9600运行帽、原N2失败及40／5美分附加账本。19项新／修订离线检查通过；旧17源和学生35源字节不变。最终CPU仍需新代码审计、全部结果及实际I/O数值审计，实际输入／调用0；T8两项精确审计仍待回复。\n',1)
old='| P008 v3.1 | Codex工程；Claude审计；研究者 | 两完整采购G1通过；10项T1+base本地完整核验、全部GPU退出；原8项外审PASS，新补跑969/965待审 | [8项事实与局限](../reports/p008_20261013/P008_T1_PROGRESS_20261013.md)、[补跑启动](../reports/p008_20261013/STUDENT_REPLACEMENTS_STARTED.json)；两补跑/新图待审；T8实际N2超准入线约21秒，未派发；最终CPU pending |'
new='| P008 v3.1 | Codex工程；Claude审计；研究者 | 两完整采购G1通过；全部10项T1+base本地和外审核验通过，图表PASS，资源退出 | [完整T1事实与局限](../reports/p008_20261013/P008_T1_PROGRESS_20261013.md)；原T8计时门FAIL保留，owner已批准9600秒/$266.44，精确新运行／数值审计待回复，T8调用0；最终CPU19源待审 |'
assert old in text;text=text.replace(old,new)
start=text.index('预算：总额$500，');end=text.index('\n',start)
text=text[:start]+'预算：总额$500，项目支出上限$450，保护至少$50。当前P008阶段上限及保守预留$266.44（249.68+16.36+0.40），预留不是实际费用；原失败费用全部保留。最新平台延迟计量$162.31184746（23:36UTC读取），billed0，非发票／余额；残余加整阶段预留354.44140093。用户已直接取消有限学生19PDT截止，原队列按真实准入和剂量运行至完成；21PDT材料冻结不变，未完成标pending、后续单列。'+text[end:]
w.write_text(text)
entry=f'\n\n### {now} — Final CPU operational-cap provenance prepared\n\nMotivation: the final integrity audit must distinguish original9560 recipe identity from reviewed operational9600 and retain the failed N2 gate and supplemental accounting. Added19-source candidate with unchanged prior17/runtime35 bytes; original24physical/21logical checks retained and exact intent file SHA, two real T8 review scopes, nine ledger records, claim link,1253+5 reservations and actual compact intent checked.19 new/revised offline tests passed once; no old raw/state oracle or unchanged tests rerun. Three private helpers parsed NOTRUN; new code/actual-byte numeric reviews required before original500-cent CPU slot. Added metadata I/O unbenchmarked and not removed from forecast. No cloud image/call/upload. Reflection: unchanged scientific config does not mean unchanged operational provenance; preserve both explicitly instead of retroactively modifying the old plan or failed criterion.\n'
for n in ('reports/sft_allocation_midpoint_20261011/RUN_LOG.md','AI_USE_LOG.md'):
 with Path(n).open('a') as f:f.write(entry)
print(json.dumps(dict(packet=str(p),source_files=19,tests=19,new_cloud_calls=0)))
