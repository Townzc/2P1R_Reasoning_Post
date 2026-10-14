"""Claude: container-side lineage/dose checks for published T8 packets (git objects only)."""
import json, subprocess, hashlib, re, ast, sys, tarfile, io, os
C=sys.argv[1]; runs=sys.argv[2:]; R='reports/p008_20261013'
def show(c,f): return subprocess.check_output(['git','show',f'{c}:{f}'],cwd='/home/claude/2P1R_Reasoning_Post')
def J(c,f): return json.loads(show(c,f))
dg=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
sh=lambda b:hashlib.sha256(b).hexdigest()
t=show('4fef52a3','experiments/sft_allocation_p008/modal_students_t8_cap.py').decode()
SRC=ast.literal_eval(re.search(r'^SOURCES=(\[.*?\])$',t,re.M).group(1)); reviewed={f:sh(show('4fef52a3',f)) for f in SRC}
spec=J('4fef52a3',R+'/student_t8_cap_9600_v1/ADMISSION.json'); assert dg(spec).startswith('4ca2c55d')
lr=J(C,R+'/LR_VECTORS.json')['2048']
for run in runs:
    d=f'{R}/t8_results_v1/{run}'; o={}
    tarb=show(C,d+'/original_evidence.tar.gz'); tf=tarfile.open(fileobj=io.BytesIO(tarb),mode='r:gz')
    mem={m.name:m for m in tf.getmembers()}
    def T(n): return json.loads(tf.extractfile(mem[n]).read())
    em=J(C,d+'/ORIGINAL_EVIDENCE_MANIFEST.json'); o['tar_eq_manifest']=all(sh(tf.extractfile(mem[n]).read())==em[n]['sha256'] for n in em) and set(em)==set(mem)
    am=J(C,d+'/artifact_manifest.json'); o['subset_of_artifact']=all(am[n]==em[n] for n in em)
    sb=J(C,d+'/SOURCE_BINDING.json'); o['src35']=sb['source_files']==reviewed; cfg=sb['config']
    o['cfg']=cfg==spec['configs'][run] and cfg['max_seconds']==9560; o['spec']=sb['spec_sha256']==dg(spec)
    L=J(C,d+'/LEDGER.json'); k='midpoint/p008-students-completion-20261013-r1/'
    cl,it,te=L[k+'claim/'+run],L[k+'intent/'+run],L[k+'terminal/'+run]
    o['chain']=(it['config_sha256']==dg(cfg), it['source_sha256']==dg(sb['source_files']), cl['intent_sha256']==dg(it), te['claim_sha256']==dg(cl), te['evidence_sha256']==dg(am), te['status'], cl['deadline_epoch']-cl['claimed_epoch'], te['actual_cost_cents'], cl['plan_sha256']==spec['plan_sha256'])
    amk=k+'t8_cap_9600_amendment'; sup=L[amk+'/reserved/'+run]
    o['supp']=sup['original_claim_sha256']==dg(cl) and sup['supplement_reserved_cents']==5 and sup['amendment_sha256']==dg(L[amk]) and L[amk]['spec_sha256']==dg(spec)
    rec=T('recipe.json'); plan=J(C,f"{R}/student_admission_v1/inputs/{cfg['plan_file']}")
    o['lr']=rec['lrs']==lr; o['sched']=rec['schedule']==plan['updates']; o['ident']=rec['identity']['config']==cfg
    cum=0;ok=True;cum1024=None
    for i in range(1,2049):
        x=T(f'completed/update_{i:04d}.json'); cum+=x['supervised_tokens']; ok&=x['indices']==plan['updates'][i-1] and x['lr']==lr[i-1] and x['cumulative_targets']==cum
        if i==1024: cum1024=cum
    o['dose']=ok and cum==4194296==plan['supervised_targets']
    blocks=[n for n in mem if n.startswith('completed/training_block_')]; o['blocks']=len(blocks)
    ck=[n for n in mem if n.startswith('checkpoint_')]; o['ckpt_meta']=sorted(ck)
    res=T('result.json'); o['res']=(res['updates'],res['targets'],round(res['wall_seconds']),res['endpoint']['correct'],res['reserved_cost_usd'],res['provider_invoice_usd'])
    loa=J(C,d+'/LOCAL_ORACLE_AUDIT.json'); o['oracle']=(loa['passed'],loa['correct'],loa['updates_verified'],loa['targets_verified'],loa['forensic_checkpoints']['1024']['targets']==cum1024, loa['forensic_checkpoints']['1024']['used_for_selection'])
    S=J(C,d+'/SUMMARY.json'); o['entry_to_terminal']=round(S['actual_entry_to_terminal_seconds'])
    col=J(C,d+'/COLLECTION.json'); o['route']=(col['collection_route'],col['callback_route'],col['new_model_calls'],col['new_remote_writes'])
    rel=J(C,d+'/RESOURCE_RELEASE.json'); o['rel']=all(a['state']=='stopped' for a in rel['apps']) and rel['owned_containers']==[]
    print(run, json.dumps(o))
