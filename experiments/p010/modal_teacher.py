"""One finite P010 lifetime per teacher. No whole-worker retry or old dispatch."""
from pathlib import Path
import modal
from experiments.p010.common import read
ROOT=Path(__file__).resolve().parents[2]
SPEC='reports/p010_20261019/teacher_runtime_v2/SPEC.json'
spec=read(ROOT/SPEC)
app=modal.App('p010-teacher-generation')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .pip_install('math-verify==0.9.0','latex2sympy2_extended==1.11.0','antlr4-python3-runtime==4.13.2','sympy==1.14.0','mpmath==1.3.0')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','VLLM_WORKER_MULTIPROC_METHOD':'spawn','VLLM_USE_V1':'1'}))
for name in list(spec['source_files'])+[SPEC]:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


def worker(model,execution,asset):
    import time,traceback
    from experiments.p010.common import dump,read,verify,utc
    from experiments.p010.runtime_support import source_check,hard_timer,compact
    from experiments.p010.teacher_contract import SLOTS
    from experiments.p010.teacher_runtime import run
    start=time.time();seconds=SLOTS[model]['seconds'];timer=hard_timer(seconds)
    out=Path('/evidence/p010-20261019/teachers')/model
    store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
    try:
        s=read('/workspace/'+SPEC);source_check(s)
        if not store.put('teacher/'+model+'/claim',{'execution':execution,'started':start},skip_if_exists=True):
            raise RuntimeError('Teacher already attempted; no automatic retry')
        volume.reload();out.mkdir(parents=True,exist_ok=False)
        verify('/evidence/p010-20261019/inputs',s['input_files'])
        dump(out/'INTENT.json',dict(execution=execution,model=model,spec=s,asset=asset,worker_start_epoch=start,hard_deadline_epoch=start+seconds))
        volume.commit()
        result=run(model,'/evidence/p010-20261019/inputs',asset,out,store,volume,start,start+seconds)
        packed=compact(out);volume.commit()
        terminal=dict(status='completed',finished_utc=utc(),seconds_including_pack=time.time()-start,result=result,artifact=packed)
        dump(out/'TERMINAL.json',terminal);volume.commit();store.put('teacher/'+model+'/terminal',terminal,skip_if_exists=True)
        return terminal
    except BaseException as e:
        if out.exists():
            dump(out/'FAILURE.json',dict(type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),utc=utc(),retry=False))
            volume.commit()
            store.put('teacher/'+model+'/terminal',dict(status='failed',error=str(e),utc=utc()),skip_if_exists=True)
        raise
    finally:timer.cancel()

settings=dict(image=image,startup_timeout=600,retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
@app.function(gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=3660,**settings)
def teacher15(execution,asset):return worker('t15',execution,asset)
@app.function(gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=5460,**settings)
def teacher7(execution,asset):return worker('t7',execution,asset)
@app.function(gpu='H100!:4',cpu=(8,8),memory=(65536,65536),timeout=4560,**settings)
def teacher72(execution,asset):return worker('t72',execution,asset)

@app.local_entrypoint()
def main(model:str,receipt_dir:str,asset_json:str):
    import subprocess,time
    from experiments.p010.common import dump,require_published,budget_check,sha
    from experiments.p010.teacher_contract import SLOTS,rate
    if model not in SLOTS:raise ValueError('Unknown teacher')
    slot=SLOTS[model];commit=require_published(ROOT)
    for name,expected in spec['source_files'].items():
        if sha(ROOT/name)!=expected or subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Source not exactly published')
    asset=read(asset_json)
    budget=budget_check('G',slot['prior'],slot['reserve'],(slot['seconds']+600)*rate(model))
    # Job's fixed hard cap bounds paid first-batch measurement. Bulk proceeds
    # only with its real full-batch cost forecast inside the same reservation.
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(model=model,execution=commit,budget=budget,asset=asset,epoch=time.time()))
    fn={'t15':teacher15,'t7':teacher7,'t72':teacher72}[model]
    call=fn.spawn(commit,asset);dump(out/'SUBMITTED.json',dict(app_id=app.app_id,call_id=call.object_id,model=model))
    try:dump(out/'RESULT.json',call.get())
    except BaseException as e:dump(out/'ERROR.json',dict(type=type(e).__name__,error=str(e)));raise
