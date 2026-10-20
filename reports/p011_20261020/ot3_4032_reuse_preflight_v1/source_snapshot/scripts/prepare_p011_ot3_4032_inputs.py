"""One approved new consumer of preserved OT3 data, never a filtering retry.

Requires the direct252/1008/4032 amendment and exact independent CR. Original
failed directory is opened read-only; only already-confirmed eligible parents
are used, in their saved order. First full encoding/planning goes to a new fixed
directory protected by a permanent attempt fence. No inference or scoring.
"""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import random
import sqlite3
import time

from scripts import prepare_p011_long_inputs as old
from experiments.p011 import data_contract as rules

ROOT = Path('.local/p011_20261020/r1')
ORIGINAL = ROOT / 'ot3_inputs_r1'
OUTPUT = ROOT / 'ot3_inputs_4032_r1'
ATTEMPT = ROOT / 'OT3_4032_BUILD_ATTEMPT.json'
SCOPE = 'p011-OT3-4032-confirmed-parent-reuse-construction-CR'
GRID = {'A1': [252, 1], 'A2': [252, 2], 'A3': [252, 4], 'A4': [252, 8],
        'A5': [252, 16], 'A6': [1008, 1], 'A7': [4032, 1], 'A8': [1008, 4]}
SOURCES = (*old.SOURCE_FILES, 'scripts/prepare_p011_ot3_4032_inputs.py')


def admit(args):
    lock, original_sources = old.admit_code(args.original_code_review, args.source_lock,
        args.prior_owner_amendment, args.prior_proposal)
    owner = json.loads(Path(args.owner_amendment).read_text())
    review = json.loads(Path(args.code_review).read_text())
    proof = json.loads(Path(args.preservation).read_text())
    expected = {'source_files': {p: old.sha(p) for p in SOURCES},
        'plan_sha256': rules.PLAN_SHA256, 'source_lock_sha256': old.sha(args.source_lock),
        'owner_count_amendment_sha256': old.sha(args.owner_amendment),
        'owner_prior_R1_R3_sha256': old.sha(args.prior_owner_amendment),
        'proposal_sha256': old.sha(args.proposal),
        'original_failure_preservation_sha256': old.sha(args.preservation),
        'original_code_acceptance_sha256': old.sha(args.original_code_review), 'grid': GRID}
    if (owner['scope'] != 'p011-OT3-252-1008-4032-owner-amendment'
            or owner['authority'] != 'direct_human_reply_in_current_chat'
            or owner['original_plan_sha256'] != rules.PLAN_SHA256
            or owner['proposal_sha256'] != expected['proposal_sha256']
            or owner['prior_R1_R3_owner_sha256'] != expected['owner_prior_R1_R3_sha256']
            or owner['original_failure_preservation_sha256'] != expected['original_failure_preservation_sha256']
            or owner['grid'] != GRID or owner['original_confirmed_eligible'] != 4038
            or owner['selected_confirmed_prefix'] != 4032 or owner['confirmed_unused_tail'] != 6
            or owner['B_rule'] != 'maximum_once_pass_tokens_across_amended_eight_A_cells'
            or owner['U_rule'] != 'ceil_B_divided_by_64000'
            or any(owner[k] is not True for k in ('required_real_re_review',
                'reuse_original_candidate_order', 'original_failed_attempt_retained'))
            or any(owner[k] is not False for k in ('refilter_allowed', 'new_generation_allowed',
                'budget_changed', 'arms_seeds_LR_evaluation_smoke_rules_changed', 'B_C_D_counts_changed'))):
        raise ValueError('Exact direct owner count amendment required')
    if (review['scope'] != SCOPE or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or any(review.get(k) != v for k, v in expected.items())
            or old.sha(review['local_report_path']) != review['report_sha256']
            or len(review['target_commit']) != 40
            or any(review.get(k) is not True for k in ('confirmed_eligible_parents_reused_without_refiltering',
                'original_failed_attempt_retained', 'new_global_attempt_fence',
                'first_full_encoding_only', 'operational_details_accepted'))):
        raise ValueError('Real exact new consumer CR, not old code PASS, required')
    if (proof['state'] != 'EXIT1_CONSUMED' or proof['original_session'] != 88890
            or proof['source'] != str(ORIGINAL) or proof['automatic_retry_allowed'] is not False):
        raise ValueError('Original failed attempt provenance differs')
    original_intent = json.loads((ORIGINAL/'INTENT.json').read_text())
    if (original_intent['source_files'] != original_sources
            or original_intent['review_sha256'] != expected['original_code_acceptance_sha256']
            or original_intent['source_lock_sha256'] != expected['source_lock_sha256']):
        raise ValueError('Original executed input/source chain differs')
    if any((ORIGINAL/name).exists() for name in ('ENCODED.jsonl','FROZEN_DOSE.json','SELECTED_RAW.jsonl',
                                               'CONSTRUCTION_COMPLETED.json','A7_PLAN.json')):
        raise ValueError('Original encoding/planning may already have happened; no duplication')
    return lock, expected, proof


def confirmed_order(path, report):
    """Read original Boolean dispositions only; no completeness/length/tokenizer work."""
    kept, seen, counts = [], set(), Counter()
    with Path(path).open() as stream:
        for number, line in enumerate(stream, 1):
            row = json.loads(line)
            key = row['parent_sha256']
            if (row['candidate_position'] != number or row['row_count'] != 16
                    or not isinstance(key,str) or len(key) != 64 or key in seen
                    or type(row['eligible']) is not bool):
                raise ValueError('Original complete sequential dispositions required')
            seen.add(key)
            counts['eligible' if row['eligible'] else 'excluded'] += 1
            if row['eligible']:
                if any(row['flags'].get(k) is not False for k in
                       ('incomplete','decontamination_hit','any_overlength')):
                    raise ValueError('Confirmed eligibility conflicts with original flags')
                kept.append(key)
    if (counts != Counter(eligible=4038, excluded=49069) or len(seen) != 53107
            or report['counts']['eligible'] != 4038
            or report['counts']['examined_candidate_parents'] != len(seen)
            or report['unexamined_candidates'] != 0 or report['stopped_at_target'] is not False):
        raise ValueError('Original exhausted4038/4096 outcome differs')
    return kept


def restore_keys(db, hashes):
    """Resolve saved identities to original normalized text without re-filtering."""
    wanted = set(hashes)
    if len(hashes) != 4038 or len(wanted) != len(hashes):
        raise ValueError('All4038 original confirmed identities required')
    found = {}
    for (key,) in db.execute("SELECT DISTINCT parent FROM rows WHERE dataset='ot3'"):
        hashed = rules.identity(key)
        if hashed in wanted:
            if hashed in found or key != rules.parent_key(key):
                raise ValueError('Ambiguous or noncanonical original parent')
            found[hashed] = key
    if set(found) != wanted:
        raise ValueError('A confirmed parent is missing; never substitute another')
    return [found[h] for h in hashes]


def select_cells(keys, rows_by_parent):
    if len(keys) != 4038 or len(set(keys)) != 4038:
        raise ValueError('Confirmed4038 order required, no resampling')
    selected, shuffled, path_ids = keys[:4032], {}, set()
    for key in selected:
        rows = list(rows_by_parent(key))
        if len(rows) != 16:
            raise ValueError('Original16 complete rows required')
        for row in rows:
            if rules.parent_key(row['question']) != key or row['path_id'] in path_ids:
                raise ValueError('Foreign/duplicate original answer')
            path_ids.add(row['path_id'])
        # Identical literal hexadecimal seed and original sorted row order as R2.
        random.Random(rules.identity(key+'p011')[:16]).shuffle(rows)
        shuffled[key] = rows
    cells = {cell: [row for key in selected[:p] for row in shuffled[key][:k]]
             for cell,(p,k) in GRID.items()}
    return cells, keys[4032:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-lock','original-code-review','prior-owner-amendment','prior-proposal',
                 'owner-amendment','proposal','preservation','code-review','tokenizer'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    old.check_cutoff()
    lock, expected, proof = admit(args)
    if ATTEMPT.exists() or OUTPUT.exists():
        raise ValueError('New consumer already attempted; preserve partial result, no retry')
    started = time.monotonic()
    old.dump(ATTEMPT, {'utc':old.utc(),'scope':SCOPE,'output':str(OUTPUT),**expected})
    OUTPUT.mkdir()
    db = None
    try:
        old.dump(OUTPUT/'INTENT.json', {'utc':old.utc(), **expected,
            'original_failed_directory':str(ORIGINAL), 'attempt_fence_sha256':old.sha(ATTEMPT),
            'original_failure_retained':True,'old_parent_filter_reexecuted':False,
            'no_training':True,'no_scoring':True,'no_generation':True})
        # New consumer input validation against the already saved preservation;
        # never invoke the old preservation/filtering/construction tools again.
        for name, item in proof['files'].items():
            old.check_cutoff()
            if '/' in name or name.startswith('.') or (ORIGINAL/name).is_symlink():
                raise ValueError('Unexpected original artifact path')
            path = ORIGINAL/name
            if path.stat().st_size != item['bytes'] or old.sha(path) != item['sha256']:
                raise ValueError('Preserved original input bytes changed')
        report = json.loads((ORIGINAL/'INSUFFICIENT_OT3_PARENTS.json').read_text())
        hashes = confirmed_order(ORIGINAL/'PARENT_DISPOSITIONS.jsonl', report)
        db = sqlite3.connect(ORIGINAL.resolve().joinpath('RAW_INDEX.sqlite').as_uri()+'?mode=ro&immutable=1', uri=True)
        db.execute('PRAGMA query_only=ON')
        keys = restore_keys(db, hashes)
        cells, unused = select_cells(keys, lambda k: old.grouped_rows(db,'ot3',k))
        for name,item in lock['tokenizer_files'].items():
            path=Path(args.tokenizer)/name
            if path.stat().st_size!=item['bytes'] or old.sha(path)!=item['sha256']:
                raise ValueError('Original native tokenizer bytes differ')
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True,
                                                   trust_remote_code=False, use_fast=True)
        if not tokenizer.is_fast: raise ValueError('Original fast tokenizer required')
        old.dump(OUTPUT/'CONFIRMED_PARENT_REUSE.json', {'all_confirmed_hashes':hashes,
            'selected_hashes':hashes[:4032], 'unused_tail_hashes':hashes[4032:],
            'grid':GRID,'original_failed_required':4096,'original_eligible':4038,
            'parent_filter_calls':0,'new_sampling_calls':0,'whole_raw_ingest_calls':0,
            'unused_count':len(unused),'owner_count_amendment_sha256':expected['owner_count_amendment_sha256']})
        with (OUTPUT/'BENCHMARKS.json').open('xb') as f:f.write((ORIGINAL/'BENCHMARKS.json').read_bytes())
        # This encoding/planning phase was never reached by the failed parent.
        # Reuse the unchanged accepted native encoding and exact-dose functions.
        failures = old.encode_and_plan(cells,tokenizer,OUTPUT,'ot3')
        dose = json.loads((OUTPUT/'FROZEN_DOSE.json').read_text())
        if (set(dose['once_pass_tokens']) != set(GRID)
                or dose['B'] != max(dose['once_pass_tokens'].values())
                or dose['U'] != (dose['B']+63999)//64000):
            raise ValueError('Inherited planner did not bind the amended eight-cell dose')
        old.dump(OUTPUT/'FROZEN_DOSE_SCOPE.json', {'grid':GRID,
            'inherited_FROZEN_DOSE_sha256':old.sha(OUTPUT/'FROZEN_DOSE.json'),
            'B':dose['B'],'U':dose['U'],
            'effective_definition':'max_once_pass_tokens_across_amended_eight_A_cells',
            'inherited_original_cells_label_means_passed_in_cells':True,
            'owner_amendment_required_is_requirement_not_pending_status':True,
            'owner_count_amendment_sha256':expected['owner_count_amendment_sha256']})
        db.close();db=None
        if failures:
            old.dump(OUTPUT/'PLANNING_FAILURES.json',failures)
            raise ValueError('Exact whole-answer plan infeasible; no dose change or retry')
        old.dump(OUTPUT/'CONSTRUCTION_COMPLETED.json',{'utc':old.utc(),
            'elapsed_seconds':time.monotonic()-started,'confirmed_parents_reused':4032,
            'unused_confirmed_parents':6,'original_parent_filter_reexecuted':False,
            'packages':{p:importlib.metadata.version(p) for p in ('transformers','tokenizers','pyarrow')},
            'actual_A1_accepted':False,'training_admitted':False,'planning_failures':{}})
        old.dump(OUTPUT/'MANIFEST.json',{'files':{p.name:{'bytes':p.stat().st_size,'sha256':old.sha(p)}
                     for p in sorted(OUTPUT.iterdir()) if p.is_file()}})
    except BaseException as exc:
        if not (OUTPUT/'FAILED.json').exists():
            old.dump(OUTPUT/'FAILED.json',{'utc':old.utc(),'type':type(exc).__name__,
                'message':str(exc),'automatic_retry_allowed':False})
        raise
    finally:
        if db is not None: db.close()


if __name__=='__main__': main()
