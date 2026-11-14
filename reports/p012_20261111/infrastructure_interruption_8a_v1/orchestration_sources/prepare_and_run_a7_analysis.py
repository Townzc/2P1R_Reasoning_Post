"""Freeze all15 bound endpoints, run the accepted adapter once, publish its output."""
import datetime,hashlib,json,subprocess,time,zipfile
from pathlib import Path
from a7_ops import *
from analysis.p012_a7 import MODELS,run_id,ACCEPTED_A7_ANALYSIS_REVIEW,CORE_SHA

REVIEW='8a8fac5c8ae75170e5c505f4215b5f1f9f0948d4'
OUT=PUBLIC/'a7_analysis_8a8fac5c_v1'
assert ACCEPTED_A7_ANALYSIS_REVIEW==REVIEW and sha('analysis/p012_registered.py')==CORE_SHA
assert not OUT.exists()
bound=lambda p:{'path':str(p),'sha256':sha(p)}
inputs=PUBLIC/'results_after6af18b72_and_a7_data_v1/analysis_inputs/math5000.jsonl'
manifest={'authority_commit':AUTHORITY,'accepted_analysis_review_commit':REVIEW,
    'exploratory':True,'excluded_from_H0_H3':True,'inputs':bound(inputs),'models':{}}
new=[];all_rows=[]
for model in MODELS:
    manifest['models'][model]={}
    for seed in ((17,) if model=='9b_base' else (17,29)):
        manifest['models'][model][str(seed)]={}
        for arm in ('short','long','concise'):
            name=run_id(model,arm,seed);d=PUBLIC/name.replace('_20261113','')
            assert (d/'RESULTS.json').exists() and (d/'evidence.zip').exists(),name
            r=read(d/'RESULTS.json');teacher='9b' if model=='9b_base' else model
            data=PUBLIC/'a7_1_concise_data_v1'/teacher/'concise.jsonl' if arm=='concise' else PUBLIC/('a6_2_9b_m512_v1' if teacher=='9b' else 'a6_2_4b_m512_and_cross_teacher_preparation_v1')/(arm+'.jsonl')
            with zipfile.ZipFile(d/'evidence.zip') as z:
                request_sha=hashlib.sha256(z.read('training/REQUEST.json')).hexdigest()
            spec={'archive':bound(d/'evidence.zip'),'result':bound(d/'RESULTS.json'),
                  'training_data':bound(data),'training_request_sha256':request_sha}
            manifest['models'][model][str(seed)][arm]=spec
            row={'run_id':name,'model':model,'arm':arm,'seed':seed,**spec,
                 'raw_sha256':r['raw_sha256'],'labels_sha256':r['labels_sha256']}
            all_rows.append(row)
            if name.startswith('a7_') and r.get('independent_numeric_audit')!='passed':new.append(row)
assert len(all_rows)==15
OUT.mkdir()
(OUT/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
freeze={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted_analysis_review_commit':REVIEW,
    'adapter':bound(Path('analysis/p012_a7.py')),'unchanged_bootstrap_core':bound(Path('analysis/p012_registered.py')),
    'endpoint_count':15,'model_calls':0,'labels_recomputed':False,'before_first_real_statistics':True}
(OUT/'SOURCE_FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n')
(OUT/'SOURCE_LOCATIONS.json').write_text(json.dumps({'inputs':bound(inputs),'endpoints':all_rows},indent=2)+'\n')
input_commit=publish([OUT],'P012: freeze complete15endpoint A7 manifest before first accepted analysis')
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
subprocess.run([PY,'-m','analysis.p012_a7','--manifest',str(OUT/'INPUT_MANIFEST.json'),
                '--output',str(OUT/'RESULTS_NUMERIC.json')],env=ENV,check=True)
assert sha('analysis/p012_registered.py')==CORE_SHA
result=read(OUT/'RESULTS_NUMERIC.json')
result['data_interpretation']=read(PUBLIC/'review_8a8fac5c/DATA_CHARACTERISTIC.json')
result['independent_numeric_audit']='pending'
(OUT/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
receipt={'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'seconds':time.monotonic()-t,'exit_code':0,'accepted_analysis_review_commit':REVIEW,
    'input_freeze_commit':input_commit,'input_manifest_sha256':sha(OUT/'INPUT_MANIFEST.json'),
    'numeric_output_sha256':sha(OUT/'RESULTS_NUMERIC.json'),'annotated_output_sha256':sha(OUT/'RESULTS.json'),
    'bootstrap_core_sha256':CORE_SHA,'new_model_calls':0,'raw_outputs_and_labels_unchanged':True}
(OUT/'RUN_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
(OUT/'NEW_ENDPOINTS_FOR_REVIEW.json').write_text(json.dumps({'count':len(new),'raw_outputs':len(new)*5000,'rows':new,
    'previous_accepted_review':REVIEW,'independent_numeric_audit':'pending'},indent=2)+'\n')
lines=['# A7 首次完整分析：独立数值复核包','',
 '分析适配器已通过8a8fac5c首次使用审查；本次绑定全部15个端点，bootstrap核心保持169754c4版本。原始统计输出、完整输入清单、来源哈希及运行记录均保留。全部为探索性LoRA/Tinker，不进入H0–H3。','',
 '**解读以9B组为主。** 4B的M512 long.jsonl中40/512行只有boxed答案、没有推理；9B没有。4B这些行在concise中反而增加了推理，因此4B是带此限制的重复。冻结数据、标签及原预测均未改动。','',
 '| 模型 | 种子 | OMI短解 | 同源concise | 长解 | concise正常输出平均token |','|---|---:|---:|---:|---:|---:|']
for m,setting in result['models'].items():
    for seed,arms in setting['endpoints'].items():
        normal=arms['concise']['normal_output_tokens']['mean']
        lines.append(f"| {m} | {seed} | {100*arms['short']['accuracy']:.2f}% | {100*arms['concise']['accuracy']:.2f}% | {100*arms['long']['accuracy']:.2f}% | {normal:.2f} |")
lines+=['','| 模型 | 对比 | 两种子均值pp（Base为单种子） | 95%区间 | 两种子同号 |','|---|---|---:|---|---|']
for m,setting in result['models'].items():
    for name,c in setting['comparisons'].items():
        v=c.get('seed_mean',c['by_seed']['17']);direction=c.get('same_nonzero_direction','单种子')
        lines.append(f"| {m} | {name} | {v['delta_pp']:+.2f} | [{v['lower95_pp']:+.2f}, {v['upper95_pp']:+.2f}] | {direction} |")
lines+=['','区间按题联合重采样，条件于这两个已观察训练种子；不估计训练种子的总体方差。每个种子的点估计、区间、截断率、循环数与正常终止分母都在RESULTS.json。','',
 '## 请Claude复核','',
 '1. 按8a8fac5c§4复核首次完整真实输出和INPUT_MANIFEST.json的15个训练/数据/权重/输出绑定，独立重算三组配对差、两种子均值、95%区间和同号标记。',
 f'2. NEW_ENDPOINTS_FOR_REVIEW.json列出此前未审的{len(new)}个新A7端点、{len(new)*5000:,}条输出；逐批独立评分。已通过8a8fac5c及更早的端点不重复。',
 '3. 按22890560判断SC-1至SC-4及S2-1/S2-2，保留4B数据限制和以9B为主的解读。两套concise数据已经全量审过。',
 '4. 4B concise seed17 greedy使用一次基础设施重试；其4510条未完成原输出独立保存在infrastructure_interruption_8a_v1，从未混入本次评分。新完整5000输出使用同一已完成训练权重和同一协议。失败费用仍计入A7。','',
 '[输入清单](INPUT_MANIFEST.json) · [来源定位](SOURCE_LOCATIONS.json) · [原始统计输出](RESULTS_NUMERIC.json) · [带数据说明的结果](RESULTS.json) · [运行记录](RUN_RECEIPT.json)']
(OUT/'README.md').write_text('\n'.join(lines)+'\n')
commit=publish([OUT],'P012: publish first accepted A7 two-seed analysis and six new endpoint evidence bindings')
(META/'A7_NEXT_REVIEW.json').write_text(json.dumps({'commit':commit,'path':str(OUT/'README.md'),
    'first_numeric_audit':'pending','new_endpoints':len(new),'complete_inputs':15},indent=2)+'\n')
print(json.dumps({'commit':commit,'inputs':15,'new_endpoints':len(new),'first_analysis_complete':True}),flush=True)
