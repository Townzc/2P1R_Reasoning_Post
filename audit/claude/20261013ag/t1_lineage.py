"""Claude: container-side lineage/dose checks for the eight published T1 packets (git objects only)."""
import json, subprocess, hashlib, re, ast, sys
C='860aa4cb'; R='reports/p008_20261013'; P=R+'/student_t1_eight_v1'
def show(c,f): return subprocess.check_output(['git','show',f'{c}:{f}'],cwd='/home/claude/2P1R_Reasoning_Post')
def J(c,f): return json.loads(show(c,f))
def ls(c,d): return subprocess.check_output(['git','ls-tree','--name-only',c,d+'/'],cwd='/home/claude/2P1R_Reasoning_Post').decode().split()
dg=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
sh=lambda b:hashlib.sha256(b).hexdigest()
spec=J('ed037c1c',R+'/student_lr_replacement_admission_v1/ADMISSION.json')['original_spec']
assert dg(spec).startswith('ab49b0a6')
t=show('c5053814','experiments/sft_allocation_p008/modal_students_completion_lr.py').decode()
SRC=ast.literal_eval(re.search(r'^SOURCES=(\[.*?\])$',t,re.M).group(1))
reviewed={f:sh(show('c5053814',f)) for f in SRC}
LR=J(C,R+'/LR_VECTORS.json'); lr256=LR.get('256') or LR.get(256) or LR['vectors']['256']
runs=['d1_b1_p4_breadth_t1','d1_b1_p4_depth_t1','d1_b8_p0_breadth_t1','d1_b8_p0_depth_t1','d2_b1_p0_breadth_t1','d2_b1_p0_depth_t1','d2_b1_p4_breadth_t1','d2_b1_p4_depth_t1']
summ=J(C,P+'/SUMMARY.json')
out={}
for r in runs:
    d=P+'/'+r; o={}
    sb=J(C,d+'/SOURCE_BINDING.json'); o['src_eq_reviewed32']= sb['source_files']==reviewed
    cfg=sb['config']; o['cfg_eq_spec']= cfg==spec['configs'][r]
    L=J(C,d+'/LEDGER.json'); k='midpoint/p008-students-completion-20261013-r1/'
    claim,intent,term=L[k+'claim/'+r],L[k+'intent/'+r],L[k+'terminal/'+r]
    o['intent_cfg']= intent['config_sha256']==dg(cfg); o['intent_src']= intent['source_sha256']==dg(sb['source_files'])
    o['claim_intent']= claim['intent_sha256']==dg(intent); o['term_claim']= term['claim_sha256']==dg(claim)
    o['term_status']=term['status']; o['attempts']=sorted(x.split('/')[-1] for x in L if x.startswith(k+'attempt/'+r+'/'))
    am=J(C,d+'/artifact_manifest.json'); o['evidence']= term['evidence_sha256']==dg(am)
    env=J(C,d+'/ENVELOPE.json') if 'ENVELOPE.json' in ' '.join(ls(C,d)) else None
    res=J(C,d+'/result.json'); o['updates']=res['updates']; o['targets']=res['targets']; o['wall']=round(res['wall_seconds'],1)
    o['correct']=res['endpoint']['correct']
    rec=J(C,d+'/recipe.json'); o['lrs_frozen']= rec['lrs']==lr256; o['identity_cfg']= rec['identity']['config']==cfg and 'physical_run_id' not in rec['identity']
    # dose from completed per-update records
    done={}
    for f in ls(C,d+'/completed'):
        n=f.split('/')[-1]
        if n.startswith('update_'): done[n]=J(C,f)
    steps=sorted(done); cum=0; ok=True
    sched=rec['schedule']
    for i,n in enumerate(steps,1):
        x=done[n]; cum+=x['supervised_tokens']; ok&= x['step']==i and x['indices']==sched[i-1] and x['cumulative_targets']==cum and x['lr']==lr256[i-1]
    o['dose_ok']=ok and len(steps)==256 and cum==cfg['targets']==524287
    blocks=[f for f in ls(C,d+'/completed') if 'training_block_' in f]; o['blocks']=len(blocks)
    bj=J(C,d+'/block_journal_metrics.json'); o['bj']=(bj['completed_blocks'],bj['completed_local_updates'],bj['block_boundary_calls'])
    rel=J(C,d+'/RESOURCE_RELEASE.json'); o['released']=all(a['state']=='stopped' for a in rel['apps']) and rel['owned_containers']==[] 
    col=J(C,d+'/COLLECTION.json'); o['collection']=(col['collected_after_local_disconnect'],col['new_model_calls'],col['original_network_error_preserved'])
    ck=ls(C,d+'/checkpoint_0256'); o['ckpt_files']=[x.split('/')[-1] for x in ck]
    loa=J(C,d+'/LOCAL_ORACLE_AUDIT.json'); o['oracle']=(loa['passed'],loa['correct'],loa['updates_verified'],loa['targets_verified'],loa.get('state_sha256','')[:8])
    out[r]=o
for r,o in out.items(): print(r, json.dumps(o))
print('SUMMARY keys', list(summ.keys())[:12])
