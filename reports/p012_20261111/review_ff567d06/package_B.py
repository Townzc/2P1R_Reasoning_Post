"""Package completed A8 B outputs; bind existing labels without new scoring/statistics."""
import datetime, hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path
P=Path('reports/p012_20261111');L=Path('.local/p012_20261111')
OUT=P/'amendment8_B_results_review_v1'
AUTH='5e1f9128180f1dcd222fc1e33fe691ec01030f38'
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,x:Path(p).write_text(json.dumps(x,indent=2)+'\n')


def main():
    queue=read(L/'amendment8_v1/BC_QUEUE.json')
    names=[n for n in read(P/'amendment8_BC_admission_v1/LAUNCH_POLICY.json')['ordered_runs'] if n.startswith('a8_b')]
    assert len(names)==7
    published={e['run_id']:e for e in queue['events'] if e['stage']=='result_published'}
    assert set(names)<=published.keys(), 'Wait for all seven B endpoints; no C or T completion gate'
    candidate={r['run_id']:r for r in read(P/'amendment8_modal_review_v1/CANDIDATE_MANIFEST.json')['cells'] if r['group']=='B'}
    assert set(candidate)==set(names)
    assert not OUT.exists();OUT.mkdir();(OUT/'inputs').mkdir()
    pred=read(P/'amendment8_modal_review_v1/A8_PREDICTIONS.json')
    rows=[];table=[];bindings=[]
    for i,name in enumerate(names):
        folder=P/(name+'_results');result=read(folder/'RESULTS.json')
        tr=L/'amendment8_modal_runs_v1'/name;ev=tr.with_name(result['evaluation_run_id'])
        request=read(tr/'request.json');ereq=read(ev/'request.json')
        assert result['prediction_before_score']['prediction']==pred['llama_instruct_gsm8k']['rows'][i]
        assert result['prediction_before_score']['prediction_commit']==AUTH
        assert datetime.datetime.fromisoformat(result['prediction_before_score']['utc']).tzinfo is not None
        assert result['model']=='meta-llama/Llama-3.2-1B-Instruct'
        for path in [folder/'RESULTS.json',folder/'evidence.zip']:
            assert subprocess.check_output(['git','hash-object',str(path)],text=True).strip()==subprocess.check_output(['git','rev-parse','HEAD:'+str(path)],text=True).strip()
        with zipfile.ZipFile(folder/'evidence.zip') as z:
            assert z.testzip() is None
            members={}
            for role,member in {'raw':'evaluation/generation/raw.jsonl','labels':'scores/labels.jsonl',
                'training_manifest':'training/MANIFEST.json','checkpoint_manifest':'training/CHECKPOINT_FILES.json',
                'trainer_state':'training/checkpoint/trainer_state.json','training_log':'training/training.log',
                'training_input':'training/inputs/examples.jsonl','prediction_before_score':'PREDICTION_BEFORE_SCORE.json',
                'hardware':'training/HARDWARE.txt','evaluation_request':'evaluation/REQUEST.json',
                'evaluation_input':'evaluation/inputs.jsonl','evaluation_config':'evaluation/config.json',
                'training_config':'training/config.yaml','score_manifest':'scores/MANIFEST.json'}.items():
                b=z.read(member);members[role]={'archive':str(folder/'evidence.zip'),'archive_sha256':sha(folder/'evidence.zip'),'member':member,'sha256':digest(b)}
            assert members['raw']['sha256']==result['raw_sha256'] and members['labels']['sha256']==result['labels_sha256']
            raw=[json.loads(x) for x in z.read(members['raw']['member']).splitlines()]
            labels=[json.loads(x) for x in z.read(members['labels']['member']).splitlines()]
            assert len(raw)==len(labels)==1319
            assert {(r['id'],r['draw']) for r in raw}=={(r['id'],r['draw']) for r in labels}
            assert len({r['id'] for r in raw})==1319
            assert sum(r['correct'] for r in labels)==result['metrics']['correct']
            assert result['metrics']['accuracy']==sum(r['correct'] for r in labels)/1319
            training=json.loads(z.read(members['training_manifest']['member']))
            assert training['cell']==result['cell'] and training['dose']==result['dose']==request['dose']
            assert training['model']==request['model']==candidate[name]['model'] and training['config']['seed']==17
            assert training['model']['revision']=='9213176726f574b556790deb65791e0c5aa438b6'
            assert training['config']['per_device_train_batch_size']==8 and training['config']['gradient_accumulation_steps']==1
            assert training['config']['learning_rate']==1e-5 and training['config']['lr_scheduler_type']=='cosine'
            assert training['config']['finetuning_type']=='full' and training['config']['max_samples']>=result['dose']['distinct_rows']
            assert training['source_sha256']==request['source_sha256']
            assert 'H100' in z.read(members['hardware']['member']).decode()
            assert training['dataset']['sha256']==members['training_input']['sha256']==result['data_sha256']==candidate[name]['dataset']['sha256']
            assert len(z.read(members['training_input']['member']).splitlines())==result['dose']['distinct_rows']
            state=json.loads(z.read(members['trainer_state']['member']))
            n=[int(x.replace(',','')) for x in re.findall(r'Num examples\s*=\s*([\d,]+)',z.read(members['training_log']['member']).decode())]
            assert state['global_step']==result['dose']['expected_updates']==result['R2']['global_step']
            assert n and set(n)=={result['dose']['distinct_rows']} and n[-1]==result['R2']['Num_examples']
            assert members['checkpoint_manifest']['sha256']==result['checkpoint_files_sha256']==ereq['config']['checkpoint_manifest_sha256']
            assert ereq['config']['training_run_id']==name
            assert result['prediction_before_score']==json.loads(z.read('PREDICTION_BEFORE_SCORE.json'))
            assert result['prediction_before_score']['raw_sha256']==members['raw']['sha256']
            assert ereq['input_sha256']==members['evaluation_input']['sha256']
            assert [r['draw'] for r in raw]==[0]*1319
            ec=ereq['config'];assert ec['max_tokens']==4096 and ec['max_model_len']==8192 and ec['n']==1 and ec['temperature']==0
            assert result['R2']['trainer_state_sha256']==members['trainer_state']['sha256']
            assert result['R2']['training_log_sha256']==members['training_log']['sha256']
            assert [result['dose'][k] for k in ('parents','paths_per_parent','epochs')]==pred['llama_instruct_gsm8k']['rows'][i]['cell']
            assert state['global_step']==candidate[name]['steps']
        assert datetime.datetime.fromisoformat(result['prediction_before_score']['utc'])<datetime.datetime.fromisoformat(published[name]['utc'])
        inp=ereq['input_jsonl'].encode();assert digest(inp)==ereq['input_sha256']
        input_file=OUT/'inputs/gsm8k1319.jsonl'
        if input_file.exists():assert input_file.read_bytes()==inp
        else:input_file.write_bytes(inp)
        assert {r['id'] for r in raw}=={json.loads(x)['id'] for x in inp.splitlines()}
        row={'run_id':name,'result':{'path':str(folder/'RESULTS.json'),'sha256':sha(folder/'RESULTS.json')},
             'input':{'path':str(input_file),'sha256':digest(inp)},'public_evidence':members,
             'dose':result['dose'],'metrics':result['metrics'],'R2':result['R2'],
             'prediction':result['prediction_before_score'],'accepted_source_review':result['accepted_source_review'],
             'source_result_commit':published[name]['commit'],'independent_result_audit':'pending','exploratory':True,'excluded_from_H0_H3':True}
        rows.append(row)
        m=result['metrics'];d=result['dose'];pr=pred['llama_instruct_gsm8k']['rows'][i]
        table.append(f"| B{i+1:02d} | {d['parents']},{d['paths_per_parent']},{d['epochs']} | {result['R2']['Num_examples']} | {result['R2']['global_step']} | {m['correct']}/1319 | {100*m['accuracy']:.3f}% | {pr['pred']:.3f}% | {100*m['length_cap_rate']:.2f}% | {m['loop_count']} | {m['normally_terminated_correct']}/{m['normally_terminated_count']} |")
    existing=read(P/'registered_analysis_169754c4_v1/INPUT_MANIFEST.json')['settings']['llama_instruct_gsm8k']
    sources=read(P/'registered_analysis_169754c4_v1/SOURCE_LOCATIONS.json')
    write(OUT/'REGISTERED_ANCHORS.json',{'setting':'llama_instruct_gsm8k','inputs':existing,'public_source_locations':sources,
        'independent_numeric_audit':'46694f515ff2c6d1f78931761f3f8e47dd0de2cb','note':'Contains both seeds for registered L/P/K8/R, reference only; not newly scored.'})
    write(OUT/'ENDPOINTS.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authority_commit':AUTH,
        'endpoint_count':7,'outputs':9233,'endpoints':rows,'new_model_calls_or_rescoring':0,'new_bootstrap_runs':0})
    for f in ['A8_PREDICTIONS.json','P012_PLAN_v1_AMENDMENT_8.md']:(OUT/f).write_bytes((P/'amendment8_modal_review_v1'/f).read_bytes())
    write(OUT/'CHECKS.json',{'complete_input_raw_label_pairings':True,'public_archives_match_git_and_sha256':True,
        'training_model_seed_cell_dose_input_and_checkpoint_bound':True,'all_seven_global_step_and_Num_examples_verified':True,
        'B07_16384_examples_4096_updates_not_truncated':True,'prescore_UTC_and_raw_hash_bound_to_frozen_predictions':True})
    (OUT/'README.md').write_text('# A8 group B: seven complete endpoints for independent review\n\n'
        'All 7 Llama-3.2-1B-Instruct × GSM8K seed 17 endpoints are complete, with 9,233 raw outputs. Full finetuning on tangzhice H100!, greedy, exploratory, outside H0–H3. Frozen numerical predictions remain 5e1f9128; runtime source accepted ff567d06. This package is released independently of groups C and T.\n\n'
        '| Cell | P,K,E | Num examples | global_step | Correct | Accuracy | Frozen prediction | Capped | Loops | Normal correct/n |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'+'\n'.join(table)+'\n\n'
        'ENDPOINTS.json binds every raw output, label, input, training manifest, model revision, checkpoint manifest, trainer_state, training.log and evaluation configuration to its public archive. All 7 R-2 checks pass. B07 uses 16,384 examples and 4,096 updates; its configured max_samples covers the complete inventory. Each prediction record has UTC, raw-output SHA256 and the frozen authority commit, recorded before scoring.\n\n'
        'Please independently score the seven B endpoints and apply the frozen A8 §5 rules: hit rate, mean residual, K > 1 RMSE against both fixed alternatives, and E = 2 versus E ≠ 2 subsets. B predictions span a narrow range, so the comparison with fixed alternatives is required in addition to hit rate. Check the B contribution to SL-5; SL-7 stays pending until C is complete. REGISTERED_ANCHORS.json supplies the accepted original endpoints as references. No rule is refit, no bootstrap is run, and existing labels stay unchanged.\n\n'
        'A group was accepted at 204ad0ae932f90579cc285ff41483e6b295007a4: partially holds, 7/10 hits, mean residual +1.25pp. A is reference-only and is not submitted for repeated review. C and the released T queue continue under their existing authorization. All A8 checkpoints are retained under 204ad0ae; the earlier delete-after-audit note in individual frozen result files is superseded. Report when the workspace approaches 900 GiB.\n')
    (OUT/'build_packet.py').write_bytes(Path(__file__).read_bytes())
    print(str(OUT))


if __name__=='__main__':main()
