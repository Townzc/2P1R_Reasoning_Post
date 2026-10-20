"""Freeze new source closures/specs once; does not execute models or old checks."""
import ast
from pathlib import Path
import json
from experiments.p010.common import dump,read,sha,manifest,utc
from experiments.p010.teacher_contract import SLOTS,rate
ROOT=Path('.')


def closure(roots):
    found=set();todo=list(roots)
    while todo:
        name=todo.pop();p=Path(name)
        if name in found or not p.is_file():continue
        found.add(name)
        if p.suffix!='.py':continue
        for parent in p.parents:
            q=parent/'__init__.py'
            if q.is_file() and str(q) not in found:todo.append(str(q))
        tree=ast.parse(p.read_text())
        for n in ast.walk(tree):
            modules=[]
            if isinstance(n,ast.Import):modules=[a.name for a in n.names]
            if isinstance(n,ast.ImportFrom):
                if n.level:
                    parts=list(p.parent.parts)
                    for _ in range(n.level-1):parts.pop()
                    modules=['.'.join(parts+([n.module] if n.module else []))]
                elif n.module:modules=[n.module]
                modules+= [m+'.'+a.name for m in list(modules) for a in n.names if a.name!='*']
            for m in modules:
                path=Path(*m.split('.'))
                for q in [path.with_suffix('.py'),path/'__init__.py']:
                    if q.is_file() and str(q) not in found:todo.append(str(q))
    return {name:sha(name) for name in sorted(found)}


p=Path('reports/p010_20261019');r=Path('.local/p010_20261019/r1');i=r/'inputs'
old=read('reports/p009_20261014/stage0_generation_runtime_preflight_v2/ADMISSION.json')
for kind,roots,names in [
 ('teacher',['experiments/p010/modal_teacher.py'],['MATH_SOURCE.json','MATH_ROSTERS.json','t15_fixed_requests.json','t7_fixed_requests.json','t72_fixed_requests.json']),
 ('e4',['experiments/p010/modal_e4.py'],[f'e4_n{n}_{s}.json' for n in (400,3200) for s in ['rows','encoded','plan','config']]+['olmo_gsm_zero.json']),
]:
 out=p/(kind+'_runtime_v1');out.mkdir(exist_ok=False)
 source=closure(roots);source['experiments/learning_regime_p009/requirements_p0.txt']=sha('experiments/learning_regime_p009/requirements_p0.txt')
 if kind=='e4':source['reports/p008_20261013/LR_VECTORS.json']=sha('reports/p008_20261013/LR_VECTORS.json')
 inp={n:read(i/'MANIFEST.json')[n] for n in names}
 spec=dict(schema='p010_'+kind+'_runtime_v1',source_files=source,input_files=inp,created_utc=utc(),
  plan_commit='4287537f7733f5c3568ddb11695d47b566ef75fa',no_automatic_retry=True)
 if kind=='teacher':
  spec.update(slots=SLOTS,monetary_rates={m:rate(m) for m in SLOTS},
   measurement_scope='Original20 T72 smoke plus first full256 per teacher; all are within authorized roster, paid and preserved. No extra calibration outputs. Remaining work requires measured full-batch forecast within original worker cap and80percent G remainder.',
   remaining_count_estimates='Fixed roster plus400 conditional retries (T7) /4000 retries+E1d(T72); observed recalculation every batch, hard cap remains authoritative. These are forecast counts, not guaranteed scientific completion.',
   T72_selfhosting_total_cap_usd=30,T72_this_lifetime_reserve_usd=24,T72_cache_reserve_usd=.5,T72_future_E3_max_reserve_usd=5,
   no_extra_new_request_for_T15_saved460=True,scientific_training_updates=0)
 else:spec.update(model=old['models']['olmo'],updates=1024,targets=2097148,seeds=[17],sizes=[400,3200],hard_seconds=4500,reserve_per_cell_usd=6.55,
   observed_timing_proxy='Original all-host NC max16-update43.307480978s;6 endpoint batches20.412141323s each;600s allowance;20%margin. OLMo transfer is not a speed guarantee; actual block interval replaces max if larger.',
   A1_A2_scope='p010-C8-A1-A2',review_required=True,training_core_adapter='Original train/optimizer/gradients/checkpoint/FP32merge unchanged; authorized OLMo model/EOS/input validation adapted.')
 dump(out/'SPEC.json',spec);dump(out/'MANIFEST.json',manifest(out))
 print(kind,len(source),len(inp))
