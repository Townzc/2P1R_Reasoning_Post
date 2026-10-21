"""B input consumers for the future shared generation/student full-path review.

The production paths are fixed and create-only. These functions are prepared,
not an authorization to load original inputs, encode training or run a model.
"""
from pathlib import Path
import time

from experiments.p010.common import read, dump, sha, digest, manifest
from experiments.p010.dataset_selection import usable
from experiments.p010.multi_answer_plan import make_plan
from experiments.learning_regime_p009.training_plan import UPDATES, TARGETS, LR_VECTOR_SHA256
from experiments.learning_regime_p009.stage0_generation_contract_v2 import MODELS
from experiments.p011.b_generation_loader import original_inputs
from experiments.p011.short_generation import b_selection
from src.sft_data import encode_row

LOCAL = '.local/p011_20261020/r1'
OWNER_PATH = 'reports/p011_20261020/review_d3f66ec3_B_rule_and_prereview_v1/OWNER_DECISION_B_K1_RULE.md'
OWNER_SHA = '2e0c8af11de76ac34368f9188d3731b2ac89d0e47e5870e8684e3d55c4953f60'
ORIGINAL_INPUTS = {
    'roster':'.local/p010_20261019/r1/inputs/MATH_ROSTERS.json',
    'source':'.local/p010_20261019/r1/inputs/MATH_SOURCE.json',
    'requests':'.local/p010_20261019/r1/inputs/t15_fixed_requests.json',
}
DEADLINE = 1792645200


def source_authority(root, binding, review):
    if (review.get('scope') != 'p011-B-generation-student-complete-path-CR'
            or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or review.get('source_files') != binding['source_files']
            or review.get('owner_B16_sha256') != OWNER_SHA
            or review.get('input_preparation_authorized') is not True
            or len(review.get('target_commit','')) != 40
            or sha(review['local_report_path']) != review['report_sha256']
            or binding['source_files'].get(OWNER_PATH) != OWNER_SHA):
        raise ValueError('Actual shared B full-path source review required')
    for name, value in binding['source_files'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or sha(Path(root)/path) != value:
            raise ValueError('Actual reviewed B source differs')


def generate_inputs(root, binding, review):
    """One first projection of old prompt tokens, no old outputs/scores loaded."""
    root=Path(root); source_authority(root,binding,review)
    if time.time() >= DEADLINE:
        raise TimeoutError('Original P011 cutoff')
    out=root/LOCAL/'b_generation_inputs_r1'
    fence=root/LOCAL/'B_GENERATION_INPUT_ATTEMPT.json'
    if out.exists() or fence.exists():
        raise ValueError('B input projection already attempted; preserve partial')
    if set(binding['original_input_files']) != set(ORIGINAL_INPUTS.values()):
        raise ValueError('Only three original fixed input sources required')
    for name, value in binding['original_input_files'].items():
        if sha(root/name) != value:
            raise ValueError('Original input source bytes changed')
    dump(fence, {'epoch':time.time(),'binding':binding,'review_sha256':digest(review)})
    out.mkdir()
    try:
        pack=original_inputs(*(read(root/ORIGINAL_INPUTS[k]) for k in ('roster','source','requests')))
        dump(out/'PACK.json',pack)
        dump(out/'SOURCE.json',{'original_input_files':binding['original_input_files'],
            'owner_B16_sha256':OWNER_SHA,'source_files':binding['source_files']})
        dump(out/'COMPLETED.json',{'ordered400_sha256':digest(pack['ordered400']),
            'requests_sha256':digest(pack['rows']),'new_requests':6400,
            'new_token_encodings':0,'old_outputs_or_scores_read':0,
            'actual_input_A1_accepted':False,'model_admitted':False})
        dump(out/'MANIFEST.json',manifest(out))
        return out
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'error':str(exc),'retry':False})
        raise


def selected_training_rows(pack, records, selection, k):
    """Exact owner B-only exception: all16 failures are absent from K4/K8."""
    if k not in (1,4,8) or selection != b_selection(pack['ordered400'], records):
        raise ValueError('Original saved Boolean selection and allowed K required')
    if selection['requires_owner_disposition']:
        raise ValueError('Fallback exceeds10percent: report before training preparation')
    rows=[]
    for cid in selection['selected_ids'][str(k)]:
        rec=records[cid]; pid=rec['problem_id']
        if pid not in pack['ordered400'] or (k != 1 and not usable(rec)):
            raise ValueError('Foreign or unusable non-K1 selected answer')
        rows.append({'problem_id':pid,'path_id':cid,'prompt':pack['source'][pid]['problem'],
            'response':rec['answer_text'],'teacher':'t15','temperature':1.0,
            'unverified_fallback':not usable(rec)})
    expected=set(pack['ordered400'])-(set(selection['unverified_fallback_questions']) if k>1 else set())
    if {r['problem_id'] for r in rows} != expected or not rows:
        raise ValueError('Owner-approved actual covered-parent set differs')
    return rows


def student_config(run, k, pack, selection, rows, encoded, plan):
    if run != 'B'+str({1:1,4:2,8:3}[k]):
        raise ValueError('Original mandatory B1/B2/B3 only')
    return {'experiment':'P011','run_id':run,'category':'B','teacher':'t15',
        'temperature':1.0,'seed':17,'P':400,'K':k,'n':len(rows),
        'P_cov':len({r['problem_id'] for r in rows}),
        'covered_problem_ids':list(dict.fromkeys(r['problem_id'] for r in rows)),
        'original_ordered400':pack['ordered400'],
        'unverified_fallback_questions':selection['unverified_fallback_questions'],
        'owner_B16_sha256':OWNER_SHA,'selection_sha256':digest(selection),
        'selected_ids':selection['selected_ids'][str(k)],'model':MODELS['qwen'],
        'updates':UPDATES,'targets':TARGETS,'training_rows_sha256':digest(rows),
        'encoded_rows_sha256':digest(encoded),'plan_sha256':digest(plan),
        'lr_vector_sha256':LR_VECTOR_SHA256,'model_admitted':False}


def student_inputs(root, pack, records, selection, tokenizer, binding, review):
    """First encoding of only new selected B answers, never original P010 data.

    Called only after complete new raw/score proof and the shared exact source
    review. The outer driver must bind those complete proof files in `binding`;
    the consumer independently checks their identities. Actual A1 follows.
    """
    root=Path(root); source_authority(root,binding,review)
    if time.time() >= DEADLINE or tokenizer.eos_token_id != 151643:
        raise ValueError('Original deadline and base-tokenizer EOS required')
    if (binding.get('complete_new_raw_and_score_proof') is not True
            or binding.get('new_raw_outputs') != 6400
            or binding.get('technical_unknown') != 0
            or binding.get('records_sha256') != digest(records)
            or binding.get('selection_sha256') != digest(selection)
            or not binding.get('actual_result_evidence_files')):
        raise ValueError('Full new raw/score/selection proof required; no partial labels')
    for name, value in binding['actual_result_evidence_files'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or sha(root/path) != value:
            raise ValueError('Original new result proof differs')
    out=root/LOCAL/'b_student_inputs_r1';fence=root/LOCAL/'B_STUDENT_INPUT_ATTEMPT.json'
    if out.exists() or fence.exists():
        raise ValueError('First B student encoding already attempted; no retry')
    # Scope checks precede the permanent fence; no encoder/model was called.
    chosen={k:selected_training_rows(pack,records,selection,k) for k in (1,4,8)}
    dump(fence,{'epoch':time.time(),'binding':binding,'review_sha256':digest(review)})
    out.mkdir()
    try:
        # K nesting reuses each newly selected answer encoding across B cells.
        unique={r['path_id']:r for rows in chosen.values() for r in rows}
        encoded={}
        for cid, row in unique.items():
            if time.time() >= DEADLINE:raise TimeoutError('Original result deadline')
            item=encode_row(row,tokenizer,2048)
            encoded[cid]=item
            dump(out/'unique_encoded'/(str(len(encoded)-1).zfill(5)+'.json'),
                 {'path_id':cid,'encoded':item})
        for k, run in ((1,'B1'),(4,'B2'),(8,'B3')):
            rows=chosen[k];items=[encoded[r['path_id']] for r in rows]
            plan=make_plan(items,17,151643)
            config=student_config(run,k,pack,selection,rows,items,plan)
            for name,value in [('rows',rows),('encoded',items),('plan',plan),('config',config)]:
                dump(out/run/(name+'.json'),value)
        dump(out/'COMPLETED.json',{'unique_new_answer_encodings':len(encoded),
            'new_student_cells':['B1','B2','B3'],'original_P010_reencoding':0,
            'selected_answer_truncation':False,'new_training_calls':0,
            'actual_input_A1_accepted':False,'selection':selection})
        dump(out/'MANIFEST.json',manifest(out))
        return out
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'error':str(exc),'retry':False,
            'confirmed_unique_encodings':len(encoded),'partial_must_be_retained':True})
        raise
