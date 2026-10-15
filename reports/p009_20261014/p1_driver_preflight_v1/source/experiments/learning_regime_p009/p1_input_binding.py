"""Bind future complete MATH generations to P1 without decoding or scoring again."""
from pathlib import Path
import json

from experiments.sft_allocation_midpoint.common import read,sha,digest
from experiments.learning_regime_p009.stage0_generation_contract_v2 import DATASETS,load_rows
from experiments.learning_regime_p009.math_scoring import last_box
from experiments.learning_regime_p009.math_scoring_journal import validate_rows

DATASET_ORDER=('math_procurement','teacher_math_zero','qwen_math_zero','qwen_math_four')
RUNS={'math_procurement':'teacher_p2_p3','teacher_math_zero':'teacher_p2_p3',
      'qwen_math_zero':'qwen_p3','qwen_math_four':'qwen_p3'}
GENERATION_SPEC_SHA='e3775978166cf1e5209c864ef3e3e84c03c2751c3c58cbe2c14a58273efa6b24'
GENERATION_TARGET='974efcbf3c6eae6034828ef11c78831cb97dea46'
SOURCE_PATHS=(
    'experiments/learning_regime_p009/__init__.py',
    'experiments/sft_allocation_midpoint/common.py',
    'experiments/learning_regime_p009/high_throughput_v1.py',
    'experiments/learning_regime_p009/stage0_generation_contract_v2.py',
    'experiments/learning_regime_p009/math_scoring.py',
    'experiments/learning_regime_p009/math_scoring_pool.py',
    'experiments/learning_regime_p009/math_scoring_journal.py',
    'experiments/learning_regime_p009/requirements_math.txt',
    'experiments/learning_regime_p009/p1_input_binding.py',
    'scripts/p009_p1_driver.py',
)


def gold_rows(inputs,spec):
    result={}
    for filename,n in [('math_train7500.jsonl',7500),('math500.jsonl',500)]:
        path=Path(inputs)/filename
        if sha(path)!=spec['local_gold_files'][filename]['sha256']:
            raise ValueError('Original full gold file differs')
        with path.open() as f:rows=[json.loads(line) for line in f]
        if len(rows)!=n or len({x['problem_id'] for x in rows})!=n:
            raise ValueError('Missing or duplicate original gold question')
        for row in rows:
            if row['problem_id'] in result:raise ValueError('Cross-file gold identity collision')
            if filename=='math_train7500.jsonl':
                extracted=last_box(row['solution']);answer=extracted['answer']
            else:
                answer=row['answer'];extracted={'status':'curated_math500_answer','answer':answer}
            result[row['problem_id']]=dict(answer=answer,extraction=extracted,
                original_gold_row_sha256=digest(row),gold_file=filename)
    return result


def assemble(ordered_sources,gold):
    """Original complete order, all unsupported gold disclosed; no symbolic work."""
    if list(ordered_sources)!=list(DATASET_ORDER):raise ValueError('Fixed P1 dataset order required')
    rows=[];excluded=[];counts={}
    for name,source in ordered_sources.items():
        expected,decoded=source['expected'],source['decoded']
        if len(expected)!=DATASETS[name]['n'] or len(decoded)!=len(expected):
            raise ValueError('No partial generated denominator')
        kept=0
        for original,record in zip(expected,decoded):
            if (record['id']!=original['candidate_id'] or record['problem_id']!=original['problem_id']
                    or record['attempt']!=original['attempt'] or record['seed']!=original['seed']
                    or record['source_row_sha256']!=original['source_row_sha256']):
                raise ValueError('Full original generation roster/order differs')
            g=gold[record['problem_id']];answer=g['answer']
            if not isinstance(answer,str) or not answer.strip():
                excluded.append(dict(dataset=name,id=record['id'],problem_id=record['problem_id'],
                    gold=g,original_record=record,reason='structurally_unsupported_gold_not_scored_zero'))
                continue
            stop=record['stop']
            rows.append(dict(id=record['id'],dataset=name,problem_id=record['problem_id'],
                attempt=record['attempt'],seed=record['seed'],gold=answer,
                answer_segment=stop['answer_segment'],stop_reason=stop['stop_reason'],
                original_gold=g,original_generation_record=record))
            kept+=1
        counts[name]=dict(generated=len(expected),scorable=kept,unsupported_gold=len(expected)-kept)
    validate_rows(rows)
    return dict(rows=rows,unsupported_gold=excluded,counts=counts,
        generated_total=sum(v['generated'] for v in counts.values()),
        scorable_total=len(rows),structurally_unsupported_gold_rows=len(excluded),
        unsupported_test_gold_blocks_G0=any(x['dataset']!='math_procurement' for x in excluded),
        new_model_calls=0,raw_decoding_repeated=False,symbolic_scoring_performed=False,
        gold_rule='Train: exact final braced box from original solution; MATH500: original answer string. No repair.')


def bind_complete_generations(generation_root,inputs,admission):
    root=Path(generation_root);spec=read(admission)
    if digest(spec)!=GENERATION_SPEC_SHA:raise ValueError('Exact reviewed generation release required')
    for name,h in spec['source_files'].items():
        if sha(name)!=h:raise ValueError('Original generation/oracle code differs')
    review=read(root/'RUNTIME_ACCEPTED.json')
    if (review.get('scope')!='p009-stage0-generation-funded-v2-runtime-and-numeric'
            or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or review.get('target_commit')!=GENERATION_TARGET
            or review.get('spec_sha256')!=GENERATION_SPEC_SHA
            or review.get('source_files')!=spec['source_files']
            or sha(review['local_report_path'])!=review['report_sha256']):
        raise ValueError('Actual funded generation review must accompany complete outputs')
    loaded={};proof={}
    for run in ('teacher_p2_p3','qwen_p3'):
        oracle_path=root/'exports'/run/'evidence/LOCAL_ORACLE_AUDIT.json'
        oracle=read(oracle_path);receipt=read(root/'runs'/run/'result.json')
        closed=read(root/'closeouts'/run/'COMPLETED.json');provider=read(root/'closeouts'/run/'provider.json')
        dispatch=read(root/'runs'/run/'dispatch_intent.json')
        ledger=read(root/'closeouts'/run/'ledger.json')
        if (oracle.get('passed') is not True or oracle.get('run_id')!=run
                or oracle.get('spec_sha256')!=GENERATION_SPEC_SHA
                or oracle.get('artifact_digest')!=digest(receipt['artifact_manifest'])
                or receipt['receipt']['status']!='completed'
                or closed['passed'] is not True
                or closed['original_receipt_sha256']!=sha(root/'runs'/run/'result.json')
                or closed['ledger_sha256']!=sha(root/'closeouts'/run/'ledger.json')
                or ledger['midpoint/'+dispatch['plan']['campaign_id']+'/terminal/'+run]!=receipt['receipt']
                or provider['app_ids']!=spec['P0_app_ids']+[dispatch['provider_app_id']]
                or provider['state']!='stopped' or provider['owned_container_ids']):
            raise ValueError('Complete original raw oracle/receipt/STOPPED0 required before P1')
        loaded[run]=oracle
        proof[run]=dict(oracle_sha256=sha(oracle_path),receipt_sha256=sha(root/'runs'/run/'result.json'),
            closeout_sha256=sha(root/'closeouts'/run/'COMPLETED.json'),
            provider_sha256=sha(root/'closeouts'/run/'provider.json'),
            ledger_sha256=closed['ledger_sha256'],
            original_dispatch_sha256=sha(root/'runs'/run/'dispatch_intent.json'),
            artifact_digest=oracle['artifact_digest'])
    original={n:dict(expected=load_rows(inputs,n),decoded=loaded[RUNS[n]]['decoded'][n]) for n in DATASET_ORDER}
    output=assemble(original,gold_rows(inputs,spec))
    output['generation_proof']=proof;output['generation_spec_sha256']=GENERATION_SPEC_SHA
    output['generation_runtime_review_sha256']=sha(root/'RUNTIME_ACCEPTED.json')
    output['original_gold_files']=spec['local_gold_files']
    return output
