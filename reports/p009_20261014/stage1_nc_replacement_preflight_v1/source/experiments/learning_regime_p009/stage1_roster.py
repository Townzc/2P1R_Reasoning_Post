"""Pure candidate Stage1 roster selection; no scoring, training or admission.

Future binding must supply complete, independently reviewed original corpora and
P1 labels. This core preserves pre-label duplicate choice and attempt01-only S1
eligibility. Its deterministic permutation is fixed before new student outcomes.
"""
import hashlib
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.training_plan import checked_rows,TARGETS

ORDER_DOMAIN='p009-stage1-question-order-v1'
SIZES={17:(100,400,1600,3200),29:(400,3200)}


def math_first_attempt_inventory(train,generated,scored,unsupported_gold_ids):
    """Use existing complete oracle/P1 fields; never parse, decode or rescore."""
    if not train or len({r['problem_id'] for r in train})!=len(train):
        raise ValueError('Unique original source row identities required')
    original={r['problem_id']:r for r in train};first_by_question={}
    for row in train:
        key=row['question_sha256']
        if not isinstance(key,str) or len(key)!=64:raise ValueError('Original normalized-question hash required')
        first_by_question.setdefault(key,row['problem_id'])
    raw={};labels={}
    for row in generated:
        pid,attempt=row['problem_id'],row['attempt'];cid=row['id']
        if (pid not in original or type(attempt) is not int or not 1<=attempt<=4
                or cid!=f'{pid}::attempt{attempt:02d}' or cid in raw):
            raise ValueError('Original procurement identity differs')
        raw[cid]=row
    for row in scored:
        if row['id'] in labels or row['id'] not in raw:raise ValueError('Missing/duplicate P1 identity')
        labels[row['id']]=row
    unsupported=set(unsupported_gold_ids)
    if len(unsupported)!=len(unsupported_gold_ids) or set(labels)&unsupported or set(labels)|unsupported!=set(raw):
        raise ValueError('Every generated row needs one original score or explicit unsupported gold')
    selected=[];excluded=[]
    for question,pid in first_by_question.items():
        cid=pid+'::attempt01'
        if cid not in raw:
            excluded.append(dict(problem_id=pid,reason='original_first_row_not_generated_no_duplicate_rescue'))
            continue
        record=raw[cid];stop=record['stop']
        if cid in unsupported:
            excluded.append(dict(problem_id=pid,reason='unsupported_gold_not_scored_zero'));continue
        verdict=labels[cid]['score']
        if any(type(verdict.get(k)) is not bool for k in ('correct','parsed','teacher_label_eligible')):
            raise ValueError('Original complete Boolean P1 verdict required')
        if (stop['stop_reason']!='native_eos' or verdict['correct'] is not True
                or verdict['parsed'] is not True or verdict['teacher_label_eligible'] is not True):
            excluded.append(dict(problem_id=pid,reason='attempt01_not_complete_parseable_correct'));continue
        text=stop['answer_segment']
        if not isinstance(text,str) or not text.strip():raise ValueError('Complete original answer text missing')
        selected.append(dict(problem_id=pid,path_id=cid,prompt=original[pid]['problem'],response=text,
            question_sha256=question,original_generation_record_sha256=digest(record),
            original_p1_row_sha256=digest(labels[cid]),attempt=1))
    return dict(rows=selected,excluded=excluded,source_rows=len(train),
        normalized_unique_questions=len(first_by_question),
        duplicate_rows=len(train)-len(first_by_question),
        attempted_outputs=len(raw),symbolic_calls=0,runtime_admitted=False)


def nested_encoded_sets(rows,seed,eos_token_id,*,negative_control=False):
    """Whole rows only; inadequate count or dose blocks, with no fallback size."""
    if type(seed) is not int or seed not in SIZES or (negative_control and seed!=17):
        raise ValueError('Only the registered seeds and NC seed17')
    checked_rows(rows,eos_token_id)
    if len(rows)<3200:raise ValueError('At least3200 eligible distinct questions required; no reduced n')
    def key(row):
        return (hashlib.sha256(f'{ORDER_DOMAIN}:{seed}:{row["problem_id"]}'.encode()).hexdigest(),row['problem_id'])
    ordered=sorted(rows,key=key)
    result={}
    for n in ((400,3200) if negative_control else SIZES[seed]):
        chosen=ordered[:n]
        if sum(r['n_supervised'] for r in chosen)>TARGETS:
            raise ValueError('Exact selected whole-answer sum exceeds fixed dose; no q0 or shorter answer substitution')
        result[str(n)]=dict(problem_ids=[r['problem_id'] for r in chosen],
            path_ids=[r['path_id'] for r in chosen],encoded_rows_sha256=digest(chosen),
            once_each_target_sum=sum(r['n_supervised'] for r in chosen))
    return dict(seed=seed,order_domain=ORDER_DOMAIN,
        full_order=[r['problem_id'] for r in ordered],inventory_sha256=digest(rows),
        selections=result,negative_control=negative_control,runtime_admitted=False,
        scientific_gate_evaluated=False)
