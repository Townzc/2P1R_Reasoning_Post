"""One new owner-approved, independently reviewed local encoding continuation.

Keeps both failed parents immutable. Copies 965 confirmed raw/encoded lines
byte-for-byte; encodes only remaining 9115 identities from the same frozen cells.
No parent filtering, new scientific selection, generation, or symbolic scoring.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import time

from experiments.p011 import data_contract as rules
from experiments.p011 import native_nfc_encoding as nfc
from scripts import prepare_p011_long_inputs as old
from scripts import prepare_p011_ot3_4032_inputs as parent

ROOT = parent.ROOT
FAILED = parent.OUTPUT
OUTPUT = ROOT / 'ot3_inputs_nfc_r1'
ATTEMPT = ROOT / 'OT3_NFC_CONTINUATION_ATTEMPT.json'
SCOPE = 'p011-OT3-confirmed-encoding-NFC-continuation-CR'
OWNER_SCOPE = 'p011-OT3-confirmed-encoding-NFC-continuation-owner'
SOURCES = (*parent.SOURCES, 'experiments/p011/native_nfc_encoding.py',
           'scripts/prepare_p011_ot3_nfc_continuation.py')
FLAGS = ('confirmed_965_encodings_reused_byte_for_byte',
         'same_10080_identities_and_cells', 'pinned_NFC_only_roundtrip',
         'original_raw_text_retained', 'both_failed_parents_retained',
         'new_global_attempt_fence', 'no_refilter_or_new_generation',
         'operational_details_accepted')


def admit(args):
    _, prior, _ = parent.admit(args)
    proof = json.loads(Path(args.failure_preservation).read_text())
    binding = {**prior, 'source_files': {p: old.sha(p) for p in SOURCES},
        'parent_reuse_CR_acceptance_sha256': old.sha(args.code_review),
        'failed_encoding_preservation_sha256': old.sha(args.failure_preservation),
        'parent_attempt_fence_sha256': old.sha(parent.ATTEMPT),
        'continuation_proposal_sha256': old.sha(args.continuation_proposal),
        'confirmed_rows': 965, 'remaining_rows': 9115, 'total_unique_rows': 10080}
    owner = json.loads(Path(args.owner_continuation).read_text())
    if (owner.get('scope') != OWNER_SCOPE
            or owner.get('authority') != 'direct_human_reply_in_current_chat'
            or owner.get('decision') != 'APPROVE_ONE_INDEPENDENT_CONTINUATION'
            or owner.get('binding') != binding
            or owner.get('requires_exact_CR') is not True
            or not owner.get('verbatim_reply') or not owner.get('recorded_utc')):
        raise ValueError('Exact new direct owner failure exception required')
    review = json.loads(Path(args.continuation_review).read_text())
    expected = {**binding, 'owner_continuation_sha256': old.sha(args.owner_continuation)}
    if (review.get('scope') != SCOPE or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or any(review.get(k) != v for k,v in expected.items())
            or any(review.get(k) is not True for k in FLAGS)
            or len(review.get('target_commit','')) != 40
            or old.sha(review['local_report_path']) != review['report_sha256']):
        raise ValueError('Real exact new continuation CR required')
    if (proof.get('original_session') != 49691 or proof.get('state') != 'EXIT1_CONSUMED'
            or proof.get('source') != str(FAILED)
            or proof.get('automatic_retry_allowed') is not False
            or proof.get('partial_line') is not False
            or proof.get('confirmed_complete_lines') != {'ENCODED.jsonl':965,'SELECTED_RAW.jsonl':965}
            or proof.get('global_fence_sha256') != binding['parent_attempt_fence_sha256']
            or proof.get('no_dose_or_plan') is not True):
        raise ValueError('Original complete confirmed prefix/failure proof differs')
    forbidden = ['FROZEN_DOSE.json','CELL_INVENTORY.json','CONSTRUCTION_COMPLETED.json',
                 *[c+'_PLAN.json' for c in parent.GRID]]
    if any((FAILED/n).exists() for n in forbidden):
        raise ValueError('Original planning may already have happened')
    return expected, proof


def confirm_prefix(directory, unique):
    """Validate original JSON/schema/identity only; no tokenizer/scorer calls."""
    raw_lines = (directory/'SELECTED_RAW.jsonl').read_bytes().splitlines(keepends=True)
    enc_lines = (directory/'ENCODED.jsonl').read_bytes().splitlines(keepends=True)
    ids = sorted(unique)
    if len(raw_lines) != 965 or len(enc_lines) != 965:
        raise ValueError('Exact965 confirmed complete prefix required')
    summary = {}
    for path_id, rb, eb in zip(ids, raw_lines, enc_lines):
        if not rb.endswith(b'\n') or not eb.endswith(b'\n'):
            raise ValueError('Unconfirmed partial original line cannot be reused')
        raw, enc = json.loads(rb), json.loads(eb)
        if raw != unique[path_id] or enc['path_id'] != path_id:
            raise ValueError('Original prefix identity/raw differs')
        tokens, labels = enc['input_ids'], enc['labels']
        a,b = enc['assistant_start'], enc['assistant_end']
        if (len(tokens) != len(labels) or len(tokens) != enc['n_processed']
                or not 0 < a < b <= len(tokens) <= 16384
                or enc['n_supervised'] != b-a or labels[a:b] != tokens[a:b]
                or labels[:a] != [-100]*a or labels[b:] != [-100]*(len(tokens)-b)
                or enc['eos_token_id'] != 151645 or tokens[b-1] != 151645
                or enc['parent_sha256'] != rules.identity(rules.parent_key(raw['question']))):
            raise ValueError('Confirmed prefix encoded structure differs')
        summary[path_id] = {k:v for k,v in enc.items() if k not in ('input_ids','labels')}
    return raw_lines, enc_lines, summary


def append_remaining(unique, summary, tokenizer, out):
    """Only unconfirmed paths reach the new encoder. No resume behavior."""
    ids = sorted(unique)
    if list(summary) != ids[:965] or len(ids) != 10080:
        raise ValueError('Exact confirmed prefix and full frozen roster required')
    with (out/'SELECTED_RAW.jsonl').open('ab') as raw, (out/'ENCODED.jsonl').open('ab') as enc, \
            (out/'NATIVE_NORMALIZATION.jsonl').open('x') as evidence:
        for path_id in ids[:965]:
            evidence.write(json.dumps({'path_id':path_id,'encoding_reused':True,
                'normalization_changed_text':False,
                'basis':'Original successful strict raw-text roundtrip; no encoding repeated.'})+'\n')
        for path_id in ids[965:]:
            old.check_cutoff()
            row = unique[path_id]
            obj, proof = nfc.encode_complete(tokenizer,row['question'],row['response'],path_id)
            summary[path_id] = {k:v for k,v in obj.items() if k not in ('input_ids','labels')}
            raw.write((json.dumps(row,ensure_ascii=False)+'\n').encode())
            enc.write((json.dumps(obj,ensure_ascii=False)+'\n').encode())
            evidence.write(json.dumps(proof,ensure_ascii=False)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-lock','original-code-review','prior-owner-amendment','prior-proposal',
                 'owner-amendment','proposal','preservation','code-review','tokenizer',
                 'failure-preservation','continuation-proposal','owner-continuation','continuation-review'):
        parser.add_argument('--'+name,required=True)
    args = parser.parse_args()
    old.check_cutoff()
    expected, proof = admit(args)
    if ATTEMPT.exists() or OUTPUT.exists():
        raise ValueError('Continuation already attempted; preserve, never retry')
    old.dump(ATTEMPT,{'utc':old.utc(),'scope':SCOPE,**expected})
    OUTPUT.mkdir()
    started=time.monotonic();db=None
    try:
        old.dump(OUTPUT/'INTENT.json',{'utc':old.utc(),**expected,
            'failed_parents':[str(parent.ORIGINAL),str(FAILED)],
            'attempt_fence_sha256':old.sha(ATTEMPT),'no_generation_or_scoring_or_filter':True})
        for name,item in proof['files'].items():
            path=FAILED/name
            if '/' in name or name.startswith('.') or path.is_symlink():
                raise ValueError('Unexpected failed-prefix artifact')
            if path.stat().st_size!=item['bytes'] or old.sha(path)!=item['sha256']:
                raise ValueError('Preserved failed encoding bytes changed')
        reuse=json.loads((FAILED/'CONFIRMED_PARENT_REUSE.json').read_text())
        if (reuse['grid']!=parent.GRID or reuse['selected_hashes']!=reuse['all_confirmed_hashes'][:4032]
                or reuse['unused_tail_hashes']!=reuse['all_confirmed_hashes'][4032:]
                or len(reuse['all_confirmed_hashes'])!=4038 or reuse['unused_count']!=6):
            raise ValueError('Original approved confirmed parent order differs')
        # Source already immutable-preserved by original failed constructor;
        # validate source bytes once as this new input, not via old preserver.
        original=json.loads(Path(args.preservation).read_text())
        dbpath=parent.ORIGINAL/'RAW_INDEX.sqlite';item=original['files']['RAW_INDEX.sqlite']
        if dbpath.stat().st_size!=item['bytes'] or old.sha(dbpath)!=item['sha256']:
            raise ValueError('Preserved source database changed')
        db=sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        db.execute('PRAGMA query_only=ON')
        keys=parent.restore_keys(db,reuse['all_confirmed_hashes'])
        cells,unused=parent.select_cells(keys,lambda k:old.grouped_rows(db,'ot3',k))
        db.close();db=None
        unique={x['path_id']:x for rows in cells.values() for x in rows}
        if len(unique)!=10080 or len(unused)!=6:
            raise ValueError('Frozen unique answer roster differs')
        rawlines,enclines,summary=confirm_prefix(FAILED,unique)
        for name,data in [('SELECTED_RAW.jsonl',rawlines),('ENCODED.jsonl',enclines)]:
            with (OUTPUT/name).open('xb') as f:f.writelines(data)
        for name in ['BENCHMARKS.json','CONFIRMED_PARENT_REUSE.json']:
            with (OUTPUT/name).open('xb') as f:f.write((FAILED/name).read_bytes())
        lock=json.loads(Path(args.source_lock).read_text())
        for name,item in lock['tokenizer_files'].items():
            p=Path(args.tokenizer)/name
            if p.stat().st_size!=item['bytes'] or old.sha(p)!=item['sha256']:
                raise ValueError('Pinned tokenizer bytes differ')
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,
                                                trust_remote_code=False,use_fast=True)
        if not tokenizer.is_fast:raise ValueError('Original fast tokenizer required')
        summary=append_remaining(unique,summary,tokenizer,OUTPUT)
        small={c:[summary[x['path_id']] for x in rows] for c,rows in cells.items()}
        once={c:sum(x['n_supervised'] for x in rows) for c,rows in small.items()};budget=max(once.values())
        old.dump(OUTPUT/'FROZEN_DOSE.json',{'B':budget,'U':(budget+63999)//64000,
            'once_pass_tokens':once,'dose_definition':'max_once_pass_tokens_across_amended_eight_A_cells',
            'fixed_before_any_student_outcome':True,'owner_amendment_required':False,
            'A7_exactly_one_pass_required':False})
        failures={}
        for cell,rows in small.items():
            old.check_cutoff()
            try:plan=rules.whole_schedule(rows,budget)
            except ValueError as exc:failures[cell]=str(exc)
            else:old.dump(OUTPUT/(cell+'_PLAN.json'),plan)
        old.dump(OUTPUT/'CELL_INVENTORY.json',{'cells':{c:[x['path_id'] for x in v] for c,v in small.items()},
            'whole_answer_planning_failures':failures,'training_admitted':False})
        if failures:
            old.dump(OUTPUT/'PLANNING_FAILURES.json',failures)
            raise ValueError('Exact whole-answer plan infeasible; no change or retry')
        old.dump(OUTPUT/'CONSTRUCTION_COMPLETED.json',{'utc':old.utc(),
            'elapsed_seconds':time.monotonic()-started,'reused_confirmed_encodings':965,
            'new_encodings':9115,'total_unique_encodings':10080,'parents':4032,
            'actual_A1_accepted':False,'training_admitted':False,'planning_failures':{}})
        old.dump(OUTPUT/'MANIFEST.json',{'files':{p.name:{'bytes':p.stat().st_size,'sha256':old.sha(p)}
            for p in sorted(OUTPUT.iterdir()) if p.is_file()}})
    except BaseException as exc:
        if not (OUTPUT/'FAILED.json').exists():old.dump(OUTPUT/'FAILED.json',
            {'utc':old.utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry_allowed':False})
        raise
    finally:
        if db is not None:db.close()


if __name__=='__main__':main()
