"""First new relaxed-pool inputs after exact CR; no model or old census rerun.

The completed census supplies the full eligible-parent set and answer lengths.
Only selected12096 groups are fetched from the original read-only SQLite index.
Previously encoded selected identities are byte-copied; only genuinely new
selected identities reach the pinned NFC encoder. Both cells share one saved
unique encoding; SMALL is the strict prefix subset. Endpoint bytes are reused.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from experiments.p011 import data_contract as rules, native_nfc_encoding as nfc
from experiments.p011.ext4b_contract import admit, parent_order, choose_from_cached_census, LARGE, SMALL
from experiments.p011.owner_0205_common import create, read, sha, utc
from experiments.p011.long_lr_r2_training import learning_rates


def checked(binding):
    path = Path(binding['path'])
    if sha(path) != binding['sha256']:
        raise ValueError('Bound prerequisite changed: '+str(path))
    return path


def rows_for_parent(db, key):
    return [{'source_file':p, 'source_row':i, 'question':q, 'response':a,
             'metadata':json.loads(m), 'path_id':f'ot3:{p}:{i}'}
            for p,i,q,a,m in db.execute(
                'SELECT source_file,row_index,question,response,metadata FROM rows '
                "WHERE dataset='ot3' AND parent=? ORDER BY source_file,row_index", (key,))]


def run(spec_path, review):
    spec = admit(spec_path, review)
    out = Path(spec['output'])
    out.mkdir(parents=True, exist_ok=False)
    create(out/'ATTEMPT.json', {'utc':utc(), 'spec':spec, 'new_scope':'P011-ext-4B',
           'models':0, 'old_census_or_training_repeated':False, 'automatic_retry':False})
    try:
        for binding in spec['original_metadata_bindings']:
            checked(binding)
        counts = read(checked(spec['census_counts']))
        checked(spec['census_completed'])
        parent_file = checked(spec['census_parents'])
        parents = {}
        with parent_file.open() as stream:
            for line in stream:
                row = json.loads(line)
                if row['parent_sha256'] in parents:
                    raise ValueError('Duplicate census group')
                parents[row['parent_sha256']] = row
        if (len(parents) != counts['different_questions_by_original_A_group_key']
                or sum(x['eligible_responses'] > 0 for x in parents.values())
                   != counts['counts']['questions_with_at_least_1_eligible']):
            raise ValueError('Completed census parent summary differs')
        raw = Path(spec['raw_index'])
        if raw.stat().st_size != spec['raw_index_bytes']:
            raise ValueError('Original immutable raw index size differs')
        db = sqlite3.connect(raw.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
        # Key projection only, not a second full-pool answer census/tokenization.
        keys = [x[0] for x in db.execute("SELECT DISTINCT parent FROM rows WHERE dataset='ot3' ORDER BY parent")]
        if len(keys) != len(parents) or {rules.identity(k) for k in keys} != set(parents):
            raise ValueError('Original A-group keys differ from completed census')
        pool = [k for k in keys if parents[rules.identity(k)]['eligible_responses'] > 0]
        selected = parent_order(pool)
        create(out/'POOL_AND_SELECTION.json', {
            'pool_parent_count':len(pool), 'pool_sorted_parent_hashes':[rules.identity(k) for k in sorted(pool)],
            'selected_parent_hashes':[rules.identity(k) for k in selected],
            'question_shuffle_seed':spec['question_shuffle_seed'],
            'large_questions':12096, 'small_questions':3024,
            'strict_subset_indices':list(range(3024)), 'A7_excluded_or_prioritized':False,
            'pool_definition':'Original A grouping with >=1 original-eligible response',
            'source_census_counts_sha256':spec['census_counts']['sha256']})
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec['tokenizer_path'], local_files_only=True)
        for name, expected in spec['tokenizer_files'].items():
            if sha(Path(spec['tokenizer_path'])/name) != expected:
                raise ValueError('Pinned original tokenizer changed')
        if tok.encode('<|im_end|>', add_special_tokens=False) != [151645]:
            raise ValueError('Original supervised EOS differs')
        newline = len(tok.encode('\n', add_special_tokens=False))
        bench = read(checked(spec['benchmark_binding']))
        decontam = rules.Decontamination([x['problem'] for x in bench])
        chosen = []
        with (out/'RAW_SELECTED.jsonl').open('x') as stream:
            for index, key in enumerate(selected):
                rows = rows_for_parent(db, key)
                prefix_lengths = {}
                for row in rows:
                    q = row['question']
                    if q not in prefix_lengths:
                        prefix, _ = rules.native_text(tok, q, row['response'])
                        prefix_lengths[q] = len(tok.encode(prefix, add_special_tokens=False))
                row, n = choose_from_cached_census(key, rows, parents[rules.identity(key)],
                                                  prefix_lengths, newline, decontam.hit(key))
                saved = {**row, 'parent_sha256':rules.identity(key), 'census_n_supervised':n}
                chosen.append(saved)
                stream.write(json.dumps(saved, ensure_ascii=False)+'\n')
                if (index+1) % 512 == 0:
                    stream.flush(); print(json.dumps({'utc':utc(), 'selected_groups':index+1}), flush=True)
        db.close()
        wanted = {x['path_id'] for x in chosen}
        # The old confirmed encoding is read only to reuse exact selected bytes;
        # no old decoder/oracle/score or old input constructor is called.
        reused = {}
        cache = Path(spec['existing_encoding_cache']['path'])
        old_inventory = read(checked(spec['existing_encoding_cache']['manifest']))
        entry = old_inventory.get('files', old_inventory)['ENCODED.jsonl']
        if entry['sha256'] != spec['existing_encoding_cache']['sha256']:
            raise ValueError('Original accepted encoding-cache manifest differs')
        with cache.open('rb') as stream:
            for line in stream:
                obj = json.loads(line)
                if obj['path_id'] in wanted:
                    if obj['path_id'] in reused: raise ValueError('Duplicate saved encoding')
                    reused[obj['path_id']] = line
        metas, new_encodings, copied = [], 0, 0
        with (out/'ENCODED.jsonl').open('xb') as enc, (out/'ENCODING_PROOFS.jsonl').open('x') as proof:
            for index, row in enumerate(chosen):
                pid = row['path_id']
                if pid in reused:
                    data = reused.pop(pid); obj = json.loads(data); copied += 1
                    note = {'path_id':pid, 'encoding_reused':True, 'exact_original_line_sha256':hashlib.sha256(data).hexdigest()}
                else:
                    obj, note = nfc.encode_complete(tok,row['question'],row['response'],pid)
                    data = (json.dumps(obj,ensure_ascii=False)+'\n').encode(); new_encodings += 1
                if obj['parent_sha256'] != row['parent_sha256'] or obj['n_supervised'] != row['census_n_supervised']:
                    raise ValueError('New selected training tokens disagree with census dose')
                enc.write(data); proof.write(json.dumps(note,ensure_ascii=False)+'\n')
                metas.append({k:obj[k] for k in ('path_id','parent_sha256','n_supervised','n_processed')})
                if (index+1) % 512 == 0:
                    enc.flush();proof.flush();print(json.dumps({'utc':utc(),'encoded_roster_rows':index+1,'new_encodings':new_encodings,'byte_reused':copied}),flush=True)
        create(out/'ROW_METADATA.json', metas)
        budget = sum(x['n_supervised'] for x in metas)
        plans = {}
        for name, rows in [(LARGE,metas),(SMALL,metas[:3024])]:
            plan = rules.whole_schedule(rows,budget,17)
            create(out/(name+'_PLAN.json'),plan)
            plans[name] = {'questions':len(rows),'B':budget,'U':plan['optimizer_updates'],'q':plan['q'],
                           'plan_sha256':sha(out/(name+'_PLAN.json'))}
        create(out/'RATES_S-F15.json',learning_rates(plans[LARGE]['U'],'S-F15'))
        for name,binding in spec['endpoint_reuse'].items():
            # Original native endpoints were already encoded; one byte-copy only.
            src=Path(binding['path']);data=src.read_bytes()
            if hashlib.sha256(data).hexdigest()!=binding['sha256']:
                raise ValueError('Original native endpoint bytes differ')
            with (out/name).open('xb') as stream:stream.write(data)
        create(out/'COMPLETED.json', {'utc':utc(),'new_scope':'P011-ext-4B','cells':plans,
            'unique_selected_questions':12096,'strict_subset_questions':3024,
            'new_answer_encodings':new_encodings,'exact_existing_encoding_lines_reused':copied,
            'full_census_retokenizations':0,'new_endpoint_prompt_encodings':0,
            'same_supervised_B_including_EOS':budget,'same_optimizer_updates':plans[LARGE]['U'],
            'original_science_recomputed':False,'GPU_calls':0,'actual_A2_accepted':False,
            'full_runtime_CR_and_actual_A2_still_required':True})
        inventory={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()}
        create(out/'MANIFEST.json',{'files':inventory})
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        raise


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--review',required=True)
    args=p.parse_args();run(args.spec,args.review)
