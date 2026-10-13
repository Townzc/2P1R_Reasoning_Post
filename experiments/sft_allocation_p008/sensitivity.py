"""Prepared secondary parser-v2: narrowly fixes E1 percent/E2 empty statements.

Never used for procurement, training selection, stopping or primary reporting.
No gold value enters extraction. Unhandled units remain unresolved. Percentages
are compared in displayed percent units (50%, not0.5); this convention is reported.
"""
import re
from analyses.gsm8k_answer_audit import extract,canonical

VERSION='p008_marked_answer_v2_secondary'
PERCENT=re.compile(r'^\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:/[-+]?\d+)?)\s*\\?%\s*$')


def extract_v2(text):
    original=extract(text);claims=[dict(c) for c in original['claims']];changes=[]
    for c in claims:
        if c['kind'] in ('box','hash') and c['value'] is None and c['payload'] is not None:
            m=PERCENT.fullmatch(c['payload'])
            if m:
                c['value']=canonical(m[1]);changes.append(dict(offset=c['offset'],change='displayed_percentage_unit'))
    explicit=[c for c in claims if c['kind'] in ('box','hash') and c['value'] is not None]
    if explicit:
        kept=[]
        for c in claims:
            if c['kind']=='answer_statement' and c['payload'] is not None and not c['payload'].strip():
                changes.append(dict(offset=c['offset'],change='empty_statement_with_explicit_claim'))
            else:kept.append(c)
        claims=kept
    values={c['value'] for c in claims}
    if original['status']=='embedded_special_token':status=original['status']
    elif not claims:status='missing_marked_answer'
    elif None in values:status='unresolved_marked_answer'
    elif len(values)!=1:status='conflicting_marked_answers'
    else:status='parsed'
    return dict(version=VERSION,status=status,value=next(iter(values)) if status=='parsed' else None,
       claims=claims,changes=changes,new_problem_boundary=original['new_problem_boundary'],
       primary_parser=original,secondary_only=True)


def task_score_v2(row,event):
    parsed=extract_v2(event['answer_segment']);gold=canonical(row['answer'])
    if gold is None:raise ValueError('Unresolved reference')
    completed=event['stop_reason'] in ('native_eos','new_problem_boundary')
    return dict(parsed=parsed,task_answer_correct=bool(completed and parsed['status']=='parsed' and parsed['value']==gold),
        task_completed=completed,secondary_only=True,reasoning_validated=False)
