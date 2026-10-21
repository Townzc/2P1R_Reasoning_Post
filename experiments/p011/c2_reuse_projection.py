"""Prepared C2 projection of already-frozen P1/P010 verdicts and prompt tokens.

No corpus loader, tokenization, decode, model or symbolic scorer. A future full
C2 input consumer must bind actual source-file SHA and their accepted A1 before
calling this adapter. This module is not a production entry or admission.
"""
from experiments.p010.dataset_selection import inventory, usable
from experiments.p011.c2_generation_window import plan_window
from experiments.sft_allocation_midpoint.common import digest


def p1_records(rows, scored, ordered_ids):
    """Project original P1 saved rows/Boolean results without re-extraction."""
    allowed=set(ordered_ids);scores={r['id']:r for r in scored}
    if len(scores)!=len(scored):raise ValueError('Duplicate original P1 score identity')
    result={};proof={}
    for row in rows:
        if row.get('dataset')!='math_procurement' or row.get('problem_id') not in allowed:continue
        attempt=row['attempt'];pid=row['problem_id'];cid=row['id']
        if type(attempt) is not int or not 1<=attempt<=4:continue
        old=row['original_generation_record'];score=scores.get(cid)
        if (cid!=f'{pid}::attempt{attempt:02d}' or cid in result or old['id']!=cid
                or not isinstance(row['answer_segment'],str)
                or not isinstance(old['stop'],dict)
                or old['stop']['answer_segment']!=row['answer_segment']
                or not score or type(score.get('score',{}).get('correct')) is not bool
                or not old.get('raw_file') or len(old.get('raw_file_sha256',''))!=64
                or len(old.get('source_row_sha256',''))!=64):
            raise ValueError('Original P1 saved row/verdict/raw provenance incomplete')
        item=dict(candidate_id=cid,problem_id=pid,attempt=attempt,
            answer_text=row['answer_segment'],stop=old['stop'],score=score,
            gold_supported=True,original_p1_row_sha256=digest(row),
            original_p1_score_sha256=digest(score),reused_original=True)
        item['usable']=usable(item);result[cid]=item
        proof[cid]={'original_row_sha256':digest(row),'original_score_sha256':digest(score),
            'original_generation_record_sha256':digest(old),'raw_file':old['raw_file'],
            'raw_file_sha256':old['raw_file_sha256'],'source_row_sha256':old['source_row_sha256']}
    inventory(result)
    return result,proof


def indexed_records(index,ordered_ids,model):
    """Read original RECORD_INDEX values; no old raw decode or score replay."""
    if model not in ('t15','t72'):raise ValueError('Only original C2 teachers')
    inventory(index);allowed=set(ordered_ids);rows={};proof={}
    for cid,row in index.items():
        if row['problem_id'] not in allowed or row['attempt']>4:continue
        if (type(row.get('score',{}).get('score',{}).get('correct')) is not bool
                or len(row.get('raw_record_sha256',''))!=64
                or row['stop']['answer_segment']!=row['answer_text']):
            raise ValueError('Original index verdict/raw/answer binding incomplete')
        rows[cid]=row;proof[cid]={'original_record_sha256':digest(row),'model':model,
            'raw_record_sha256':row['raw_record_sha256']}
    return rows,proof


def prepare_projection(roster,source,requests,t72_index,t15_index,p1_rows,p1_scored,window_size):
    """Project the original immutable E1d order; never shuffle or replace IDs."""
    ordered=roster['e1d_order'];s1=roster['s1']['400'];lookup={r['problem_id']:r for r in source}
    excluded=set(roster['unsupported'])|set(roster['e2_dev'])
    if (not ordered or len(set(ordered))!=len(ordered) or len(s1)!=400 or len(set(s1))!=400
            or len(lookup)!=len(source) or not set(ordered)<=set(lookup)
            or set(ordered)&excluded):
        raise ValueError('Original E1d/source/exclusion/S1 roster differs')
    first={}
    for row in requests:
        if row['attempt']!=1 or row['problem_id'] not in set(ordered):continue
        pid=row['problem_id'];ids=row['prompt_token_ids']
        if (pid in first or row['candidate_id']!=pid+'::attempt01' or not ids
                or any(type(x) is not int or not 0<=x<151936 for x in ids)
                or len(ids)+1024>2048):
            raise ValueError('Original unique prompt-token source invalid')
        first[pid]=ids
    if set(first)!=set(ordered):raise ValueError('Original full ordered prompt coverage required')
    right,rproof=indexed_records(t72_index,ordered,'t72')
    left,lproof=indexed_records(t15_index,ordered,'t15')
    old,oproof=p1_records(p1_rows,p1_scored,ordered)
    if set(left)&set(old):raise ValueError('Old T15 output overlap must be explicitly reconciled; no overwrite')
    left={**old,**left};lproof={'P1':oproof,'P010':lproof}
    plan=plan_window(ordered,right,left,first,set(s1),window_size)
    parents=plan['window_parents']
    return {'ordered_e1d':ordered,'s1_ids':s1,'t72_records':right,'t15_records':left,
        'source':{pid:lookup[pid] for pid in parents},'prompts':{pid:first[pid] for pid in parents},
        'plan':plan,'reuse_proof':{'t72':rproof,'t15':lproof,
            'original_roster_sha256':digest(roster),'original_request_list_sha256':digest(requests),
            'new_raw_decodes':0,'new_symbolic_scores':0,'new_prompt_encodings':0},
        'actual_input_A1_accepted':False,'model_admitted':False}
