"""Saved verdict selection; exclude all unmapped rows, including K1 fallback."""
from experiments.p010.dataset_selection import inventory,usable,text_key
from experiments.p011.b_generation_loader import score_rows
from experiments.sft_allocation_midpoint.common import digest

def mapped(row):return not row['transport']['unmapped_model_token_ids']

def select(ordered400,records):
    if len(ordered400)!=400 or len(set(ordered400))!=400:raise ValueError('Original400 required')
    groups=inventory(records)
    if set(groups)!=set(ordered400):raise ValueError('Full original400x16 roster required')
    chosen={1:[],4:[],8:[]};fallback=[];absent=[];short={4:[],8:[]}
    for pid in ordered400:
        attempts=groups[pid]
        if set(attempts)!=set(range(1,17)):raise ValueError('Every original attempt required')
        eligible=[attempts[a] for a in range(1,17) if mapped(attempts[a])]
        first=next((x for x in eligible if usable(x)),eligible[0] if eligible else None)
        if first is None:absent.append(pid)
        else:
            chosen[1].append(first['candidate_id'])
            if not usable(first):fallback.append(pid)
        seen=set(); candidates=[]
        for row in eligible:
            key=text_key(row['answer_text'])
            if usable(row) and key not in seen:seen.add(key);candidates.append(row['candidate_id'])
        if candidates and (first is None or candidates[0]!=first['candidate_id']):raise ValueError('Nested first usable differs')
        for k in (4,8):
            chosen[k].extend(candidates[:k])
            if len(candidates)<k:short[k].append(pid)
    return dict(selected_ids={str(k):v for k,v in chosen.items()},unverified_fallback_questions=fallback,
        all16_unmapped_absent_questions=absent,nesting_conflicts=fallback+absent,
        underfilled_questions={str(k):v for k,v in short.items()},K1_attempt_window=16,
        requires_owner_disposition=len(fallback)/400>.10,report_fallback_above_10pct=len(fallback)/400>.10,
        report_underfill_above_10pct={str(k):len(v)/400>.10 for k,v in short.items()},
        all_unmapped_training_rows_excluded=True,training_admitted=False)

def selected_records(pack,raw,transports,scored):
    rows=score_rows(pack,raw,transports)
    if ([r['id'] for r in rows]!=[x['id'] for x in scored]
            or any(type(x['score'].get('correct')) is not bool for x in scored)):
        raise ValueError('All6400 frozen ordered Boolean verdicts required')
    records={}
    for row,decoded,verdict in zip(rows,transports,scored):
        item=dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],attempt=row['attempt'],
            answer_text=row['answer_segment'],stop=decoded['stop'],transport=decoded['transport'],
            score=verdict,gold_supported=True,raw_record_sha256=row['raw_record_sha256'],
            decoded_record_sha256=digest(decoded))
        item['usable']=usable(item)
        if not mapped(item) and item['usable']:raise ValueError('Unmapped row cannot be usable')
        records[item['candidate_id']]=item
    return records,select(pack['ordered400'],records)

def denominator_report(records):
    if len(records)!=6400:raise ValueError('Full6400 records required')
    rows=list(records.values());excluded=[r for r in rows if not mapped(r)];kept=[r for r in rows if mapped(r)]
    return dict(main_attempted=6400,main_usable=sum(usable(r) for r in rows),
        unmapped_attempted_unusable=len(excluded),unmapped_not_proven_incorrect=True,
        sensitivity_without_unmapped_denominator=len(kept),sensitivity_without_unmapped_usable=sum(usable(r) for r in kept),
        batch_unmapped_counts=[sum(not mapped(r) for r in rows[i:i+256]) for i in range(0,6400,256)])
