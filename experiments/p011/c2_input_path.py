"""Prepared fixed-path C2 original-output reuse consumer, pending full shared CR."""
from pathlib import Path
import time
from experiments.p011.c2_reuse_projection import prepare_projection
from experiments.p011.c1_admission import fixed_report, PLAN
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,manifest

LOCAL='.local/p011_20261020/r1'
CUTOFF=1792645200
SCOPE='p011-C2-generation-student-complete-path-CR'
FILES={
 'roster':'.local/p010_20261019/r1/inputs/MATH_ROSTERS.json',
 'source':'.local/p010_20261019/r1/inputs/MATH_SOURCE.json',
 'requests':'.local/p009_20261014/r1/stage0_inputs_r1/math_teacher_requests8993.jsonl',
 't72_index':'.local/p010_20261019/r1/teacher_t72_export_r1/evidence/RECORD_INDEX.json',
 't15_index':'.local/p010_20261019/r1/teacher_t15_export_r1/evidence/RECORD_INDEX.json',
 'p1_rows':'.local/p009_20261014/r1/p1_actual_r1/ROWS.json',
 'p1_scored':'.local/p009_20261014/r1/p1_actual_r1/ALL_SCORED_ROWS.json',
}
EVIDENCE=(
 '.local/p010_20261019/r1/teacher_t72_export_r1/COMPLETED.json',
 '.local/p010_20261019/r1/teacher_t15_export_r1/COMPLETED.json',
 '.local/p010_20261019/r1/teacher_t72_export_r1/evidence/E1D_ACCEPTED.json',
 '.local/p010_20261019/r1/t72_datasets_r1/STRUCTURAL_A1.json',
 '.local/p010_20261019/r1/t15_datasets_r1/STRUCTURAL_A1.json',
 '.local/p010_20261019/r1/T72_DATA_A1_ACCEPTED.json',
 '.local/p010_20261019/r1/T15_DATA_A1_ACCEPTED.json',
)


def authority(root,binding,review):
    fixed_report(review)
    if (review.get('scope')!=SCOPE or review.get('original_plan_commit')!=PLAN
            or review.get('source_files')!=binding['source_files']
            or review.get('original_reuse_files')!=binding['original_reuse_files']
            or review.get('original_acceptance_files')!=binding['original_acceptance_files']
            or review.get('input_preparation_authorized') is not True
            or review.get('read_only_original_Boolean_and_prompt_reuse_accepted') is not True
            or review.get('missing_T15_only_first_four_and_original_E1d_order_accepted') is not True
            or review.get('window_size')!=binding['window_size']
            or type(binding['window_size']) is not int or not 1<=binding['window_size']<=700
            or set(binding['original_reuse_files'])!=set(FILES.values())
            or set(binding['original_acceptance_files'])!=set(EVIDENCE)):
        raise ValueError('True full C2 source/original-input reuse CR required')
    for table in ('source_files','original_reuse_files','original_acceptance_files'):
        for name,value in binding[table].items():
            path=Path(name)
            if path.is_absolute() or '..' in path.parts or sha(Path(root)/path)!=value:
                raise ValueError('Fixed original source or reuse evidence bytes differ')


def prepare(root,binding,review):
    """One first reuse projection. No original decoder/scorer/constructor called."""
    root=Path(root);authority(root,binding,review)
    if time.time()>=CUTOFF:raise TimeoutError('Original P011 cutoff')
    out=root/LOCAL/'c2_generation_inputs_r1';fence=root/LOCAL/'C2_GENERATION_INPUT_ATTEMPT.json'
    if out.exists() or fence.exists():raise ValueError('C2 original reuse already attempted; no retry')
    dump(fence,{'epoch':time.time(),'binding':binding,'review_sha256':digest(review),'automatic_retry':False})
    out.mkdir()
    try:
        import json
        values={k:([json.loads(line) for line in (root/v).read_text().splitlines()]
                   if v.endswith('.jsonl') else read(root/v)) for k,v in FILES.items()}
        for model in ('t15','t72'):
            saved=read(root/f'.local/p010_20261019/r1/teacher_{model}_export_r1/COMPLETED.json')
            if saved.get('provider_stopped') is not True:raise ValueError('Saved old complete/STOPPED evidence required')
        old_accept=read(root/EVIDENCE[2])
        if (old_accept['source_order_sha256']!=digest(values['roster']['e1d_order'])
                or type(old_accept['examined_prefix_count']) is not int
                or not 0<old_accept['examined_prefix_count']<=len(values['roster']['e1d_order'])):
            raise ValueError('Original E1d examined prefix proof differs')
        pack=prepare_projection(**values,window_size=binding['window_size'])
        dump(out/'PACK.json',pack)
        parents=pack['plan']['window_parents']
        if pack['plan']['new_requests']:
            dump(out/'GPU_PACK.json',{'plan':pack['plan'],
                'source':{pid:{'problem':pack['source'][pid]['problem']} for pid in parents},
                'prompts':pack['prompts']})
        dump(out/'COMPLETED.json',{'prepared_epoch':time.time(),'original_reuse_files':binding['original_reuse_files'],
            'original_acceptance_files':binding['original_acceptance_files'],
            'old_symbolic_scores_or_raw_decodes_repeated':0,'new_encodings':0,
            'new_request_count':len(pack['plan']['new_requests']),'model_admitted':False,
            'initial_prefix':pack['plan']['initial_prefix'],'actual_input_A1_accepted':False})
        dump(out/'MANIFEST.json',manifest(out));return out
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'error':str(exc),'partial_retained':True,'automatic_retry':False});raise
