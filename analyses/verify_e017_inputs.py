"""CPU release reconstruction and recorded-token replay; no pretrained weights loaded."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lines(path):return [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]


def verify(tokenizer_dir,ledger,out):
    import torch
    from scripts.audit_family_matching import verified_tokenizer
    from analyses.e017_stopping import TaskBoundaryStop
    from analyses.completion_contract import first_stop
    tokenizer,_=verified_tokenizer(tokenizer_dir)
    root=Path('reports/real_math_e017_inputs_r1')
    release=Path('configs/real_math_e017/release.json')
    manifest=json.loads((root/'manifest.json').read_text())
    assert digest(root/'manifest.json')==json.loads(release.read_text())['manifest_sha256']
    config=Path('configs/real_math_e017/stopping.json');cfg=json.loads(config.read_text())
    assert digest(config)==manifest['config_sha256']
    assert (cfg['max_seconds'],cfg['guard_seconds'],cfg['expected_prior_jobs'],cfg['expected_prior_used_seconds'])==(240,15,20,6921)
    assert (cfg['eval_batch_size'],cfg['max_length'],cfg['max_new_tokens'],cfg['optimizer_updates'])==(8,1024,768,0)
    assert (cfg['rental_cap_seconds'],cfg['required_admission_seconds'])==(900,555)
    for p,h in manifest['source_files_sha256'].items():
        assert digest(p)==h
        assert hashlib.sha256(subprocess.check_output(['git','show',manifest['source_commit']+':'+p])).hexdigest()==h
    assert set(manifest['files_sha256'])=={'rows.jsonl','cases.json','cpu_evidence.json'}
    for name,h in manifest['files_sha256'].items():assert digest(root/name)==h
    assert digest('configs/real_math_e016/release.json')==manifest['parent_e016_release_sha256']
    rows=lines(root/'rows.jsonl');old=Path('reports/real_math_e016_inputs_r1')
    assert (root/'rows.jsonl').read_bytes()==(old/'rows.jsonl').read_bytes()
    assert [r['development_rank'] for r in rows]==list(range(17,81))
    assert len({r['group_id'] for r in rows})==64
    expected=[]
    for row in rows:
        prompt='Problem: '+row['prompt']+'\nSolution:\n'
        ids=tokenizer(prompt,add_special_tokens=False)['input_ids']
        assert tokenizer.eos_token_id not in ids and len(ids)+768<=1024
        expected.append({'problem_id':row['problem_id'],'serialized_prompt':prompt,'prompt_ids':ids})
    assert expected==json.loads((root/'cases.json').read_text())==json.loads((old/'cases.json').read_text())
    state=json.loads(Path(ledger).read_text());assert digest(ledger)==cfg['expected_ledger_sha256']
    assert state['authorized_gpu_seconds']==7200 and len(state['jobs'])==20
    assert len({j['run_id'] for j in state['jobs']})==20
    assert sum(j['charged_seconds'] for j in state['jobs'])==6921
    for job in state['jobs']:
        assert job['status']!='reserved'
        assert job==json.loads((Path('runs')/job['run_id']/'resource_receipt.json').read_text())
    # Replay only already recorded tokens through the actual incremental class.
    # This tests stopping, not model logits or promised future GPU prefixes.
    counts=Counter();streams=0;steps=0;tick=time.monotonic()
    for path in ('runs/gsm8k_overfit_e013_r1/base_dev.jsonl','runs/gsm8k_overfit_e013_r1/final_dev.jsonl',
                 'runs/gsm8k_capability_e016_r1/base.jsonl','runs/gsm8k_capability_e016_r1/e015.jsonl'):
        raw=lines(path)
        for start in range(0,len(raw),8):
            part=raw[start:start+8]
            prompt_ids=[tokenizer('Problem: '+r['prompt']+'\nSolution:\n',add_special_tokens=False)['input_ids'] for r in part]
            width=max(map(len,prompt_ids));prefixes=[[tokenizer.eos_token_id]*(width-len(ids))+ids for ids in prompt_ids]
            stopper=TaskBoundaryStop(tokenizer,width,len(part),768)
            for step in range(768):
                for i,row in enumerate(part):
                    prefixes[i].append(tokenizer.eos_token_id if stopper.events[i] else row['generated_ids'][step])
                done=stopper(torch.tensor(prefixes),None);steps+=1
                if bool(done.all()):break
            for row,event in zip(part,stopper.events):
                oracle=first_stop(row['generated_ids'],lambda ids:tokenizer.decode(ids,skip_special_tokens=True),tokenizer.eos_token_id,768,tokenizer.all_special_ids)
                assert event==oracle
                counts[event['stop_reason']]+=1;streams+=1
    assert streams==160 and counts['new_problem_boundary']==18
    report={'status':'passed_independent_inputs_ledger_and_recorded_token_replay','release_sha256':digest(release),
        'parents':64,'prompt_streams_reconstructed':64,'inputs_byte_equal_to_observed_e016':True,
        'unused_development_reserve':432,'ledger_receipts_reconciled':20,'used_seconds':6921,'remaining_seconds':279,
        'maximum_reservation':255,'remaining_after_maximum':24,'recorded_streams_replayed':streams,
        'incremental_stopping_steps_exercised':steps,'stop_reasons':dict(counts),
        'replay_seconds':time.monotonic()-tick,'scripted_tokens_are_new_gpu_generations':False,
        'new_pretrained_model_calls':0,'server_contacted':False,'official_test_read':False,
        'gpu_runtime_numerics_verified':False,'verifier_sha256':digest(__file__)}
    with out.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer-dir',required=True,type=Path);p.add_argument('--ledger',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();print(json.dumps(verify(a.tokenizer_dir,a.ledger,a.out),indent=2))
