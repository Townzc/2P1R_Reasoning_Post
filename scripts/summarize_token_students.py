"""All eight fixed-tariff students; no selection, dispatch, or missing-cell fill."""
import argparse
from collections import Counter
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.sft_allocation_acquisition.token_contract import TARGETS
from scripts.summarize_acquisition_students import contrasts,CELLS,SEEDS
from src.sft_data import read_jsonl


def exposure_summary(rows,plan):
    counts=Counter(i for batch in plan['updates'] for i in batch)
    if set(counts)!=set(range(len(rows))):raise ValueError('Missing or foreign training row')
    single=sum(row['source']['n_supervised'] for row in rows)
    targets=sum(rows[i]['source']['n_supervised']*n for i,n in counts.items())
    if targets!=TARGETS or len(plan['updates'])!=256:raise ValueError('Exposure dose differs')
    return dict(unique_answers=len(rows),presentations=sum(counts.values()),
        min_per_answer=min(counts.values()),max_per_answer=max(counts.values()),
        mean_per_answer=sum(counts.values())/len(rows),one_pass_supervised_tokens=single,
        token_weighted_exposure=targets/single,
        histogram={str(n):sum(v==n for v in counts.values()) for n in sorted(set(counts.values()))})


def analyze(root):
    root=Path(root)
    spec=read('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
    inputs=root/'student_preparation_r2/inputs'
    if sha(inputs/'manifest.json')!=spec['input_sha256']:raise ValueError('Frozen inputs changed')
    ids=sorted(x['problem_id'] for x in read_jsonl(inputs/'gsm8k_test1319.jsonl'))
    if len(ids)!=1319 or len(set(ids))!=1319:raise ValueError('Incomplete standard benchmark')
    predictions={};sources={};table=[]
    for cell in CELLS:
        row=dict(cell=cell,tariff_procurement=spec['selection'][cell],seeds={})
        train_rows=read_jsonl(inputs/f'{cell}_train.jsonl')
        for seed in SEEDS:
            run=f'{cell}_s{seed}';receipt=root/'students'/(run+'_run_r1')/'result.json'
            envelope=read(receipt);r=envelope['result']
            ap=root/'student_exports'/run/'LOCAL_ORACLE_AUDIT.json';audit=read(ap)
            if (envelope['receipt']['status']!='completed' or r['status']!='completed'
                    or r['cell']!=cell or r['seed']!=seed or r['supervised_tokens']!=TARGETS
                    or r['committed_updates']!=256 or r['physical_generated_outputs']!=1319
                    or audit['campaign']!=spec['campaign_id'] or audit['run_id']!=run
                    or audit['input_sha256']!=spec['input_sha256']
                    or audit['artifact_digest']!=digest(envelope['artifact_manifest'])
                    or audit['artifact_digest']!=envelope['receipt']['evidence_sha256']
                    or audit['outputs_independently_rescored']!=1319
                    or audit['supervised_tokens_verified']!=TARGETS):
                raise ValueError('Incomplete or mismatched student: '+run)
            qc=r['endpoint']['question_correct']
            if (sorted(qc)!=ids or any(type(x) is not bool for x in qc.values())
                    or sum(qc.values())!=audit['correct'] or sum(qc.values())!=r['endpoint']['correct']):
                raise ValueError('Unknown or inconsistent endpoint')
            stops=audit['endpoint_stop_diagnostics']
            if (stops['n']!=1319 or stops['stop_reasons']!=r['endpoint']['stop_reasons']
                    or stops['length_cap_outputs']!=r['endpoint']['stop_reasons'].get('length_cap',0)
                    or stops['length_cap_scored_incorrect']!=stops['length_cap_outputs']):
                raise ValueError('Independently checked truncation counts differ')
            predictions[run]=qc;sources[run]=dict(receipt_sha256=sha(receipt),local_audit_sha256=sha(ap))
            row['seeds'][str(seed)]=dict(correct=sum(qc.values()),n=1319,accuracy=sum(qc.values())/1319,
                parsed=r['endpoint']['parsed'],stop_reasons=r['endpoint']['stop_reasons'],
                truncated_outputs=stops['length_cap_outputs'],truncation_fraction=stops['length_cap_outputs']/1319,
                train_seconds=r['train_seconds'],wall_seconds=r['wall_seconds'],
                runtime_rate_estimate_usd=r['runtime_rate_estimate_usd'],
                training_exposure=exposure_summary(train_rows,read(inputs/f'{cell}_seed{seed}.json')))
        row['mean_accuracy']=sum(x['accuracy'] for x in row['seeds'].values())/2
        row['truncated_outputs_across_seeds']=sum(x['truncated_outputs'] for x in row['seeds'].values())
        row['truncation_fraction_across_seeds']=row['truncated_outputs_across_seeds']/2638
        table.append(row)
    return dict(schema='p007b_token_tariff_results_v1',table=table,sources=sources,
        contrasts=contrasts(predictions),updates=2048,supervised_targets=8*TARGETS,endpoint_outputs=10552,
        tariff=spec['inputs_manifest']['tariff'],
        interpretation=read('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_INTERPRETATION.json'),
        limitations=spec['limitations']+[
            'Fixed524287 supervised targets and256updates include unequal repetition: approximately4.46/3.97/20.75/8.00 mean presentations for p0breadth/p0depth/p4breadth/p4depth. No isolated reasoning-diversity or repetition-damage causal claim.',
            'Unspent caps6.14%,6.88%,12.26%,10.90% all exceed the original5% exact-spend qualification; this is a common-cap comparison.',
            'Report both within-price contrasts alongside the interaction; an interaction alone is not a winner.',
            'Non-significance is not equivalence. Final-answer correctness is not verified reasoning quality.',
            'Length-capped outputs count as incorrect under the unchanged512-token evaluation rule; report every cell and seed truncation count without removing them from the denominator.',
            'Unused wallets differ; this is a common budget cap, not exactly equal realized spending.'],
        bootstrap=dict(replicates=10000,seed=20261013,unit='shared paired question across eight fixed models',
            interpretation='Conditional on observed models/trace pools; not seed or procurement uncertainty.'),
        original_two_time_priced_students='Retained separately as operational pilots, not pooled into this comparison.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();dump(a.out,analyze(a.root))
