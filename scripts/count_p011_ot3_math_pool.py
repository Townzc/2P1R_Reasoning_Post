"""New full-pool OT3 census. Read-only original raw index; no GPU or training."""
import argparse
from array import array
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path
import math
import random
import sqlite3
import time

from experiments.p011 import data_contract as rules
from experiments.p011.owner_0205_common import admit, checked_metadata, create, digest, utc


def normalized_question(text):
    """Requested whitespace removal + case unification, without added NFKC."""
    return ''.join(text.split()).casefold()


def dispersion(lengths):
    mean = sum(lengths) / len(lengths)
    return ((max(lengths) / min(lengths)) if min(lengths) else None,
            math.sqrt(sum((x-mean)**2 for x in lengths)/len(lengths))/mean if mean else None)


def prefix_mass(candidates, sizes=(8192, 16384, 32768)):
    """New diagnostic selection, not a training arm or a changed frozen dose."""
    ordered = sorted(candidates)
    random.Random(20261020).shuffle(ordered)
    return {str(p): {'enough_eligible_questions': len(ordered) >= p,
                    'one_pass_supervised_tokens_including_EOS':
                    sum(candidates[k] for k in ordered[:p]) if len(ordered) >= p else None}
            for p in sizes}


def run(spec_path, review_path):
    spec = admit(spec_path, review_path, 'p011-OT3-full-math-pool-census-CR')
    out = Path(spec['output'])
    out.mkdir(parents=True, exist_ok=False)
    create(out/'ATTEMPT.json', {'started_utc': utc(), 'spec': spec,
        'no_model_calls': True, 'no_training_inputs_regenerated': True, 'automatic_retry': False})
    started = time.monotonic()
    try:
        for binding in spec['original_metadata_bindings']:
            checked_metadata(binding)
        from transformers import AutoTokenizer
        import numpy as np
        tok = AutoTokenizer.from_pretrained(spec['tokenizer_path'], local_files_only=True)
        for name, wanted in spec['tokenizer_files'].items():
            from experiments.p011.owner_0205_common import sha
            if sha(Path(spec['tokenizer_path'])/name) != wanted:
                raise ValueError('Census student tokenizer changed')
        if tok.encode('<|im_end|>', add_special_tokens=False) != [151645]:
            raise ValueError('Original supervised EOS policy differs')
        newline_length = len(tok.encode('\n', add_special_tokens=False))
        bench = checked_metadata(spec['benchmark_binding'])
        decontam = rules.Decontamination([x['problem'] for x in bench])
        exact_gold, norm_gold = defaultdict(set), defaultdict(set)
        for row in bench:
            exact_gold[row['benchmark']].add(row['problem'])
            norm_gold[row['benchmark']].add(normalized_question(row['problem']))
        exact_questions, normalized_questions = set(), set()
        exact_overlap, norm_overlap = defaultdict(set), defaultdict(set)
        counts, cardinalities = Counter(), Counter()
        lengths_all, ratios, cvs = array('I'), [], []
        at_least_one, strict_sixteen = {}, {}
        db = sqlite3.connect(Path(spec['raw_index']).resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
        columns = [x[1] for x in db.execute('PRAGMA table_info(rows)')]
        if columns != ['dataset','parent','source_file','row_index','question','response','metadata']:
            raise ValueError('Original raw-index schema differs')
        cursor = db.execute("SELECT parent,source_file,row_index,question,response FROM rows "
                            "WHERE dataset='ot3' ORDER BY parent,source_file,row_index")
        with (out/'PARENT_COUNTS.jsonl').open('x') as parent_log:
            import json
            for parent, group in groupby(cursor, key=lambda row: row[0]):
                rows = list(group)
                if any(rules.parent_key(row[3]) != parent for row in rows):
                    raise ValueError('A-group parent key differs from original raw text')
                answers = [row[4] for row in rows]
                encoded = tok(answers, add_special_tokens=False, truncation=False)['input_ids']
                lengths = [len(ids) for ids in encoded]
                lengths_all.extend(lengths)
                prefix_lengths = {}
                qualified = []
                leaked = decontam.hit(parent)
                for row, n in zip(rows, lengths):
                    question = row[3]
                    exact_questions.add(question)
                    norm = normalized_question(question)
                    normalized_questions.add(norm)
                    for label in exact_gold:
                        if question in exact_gold[label]: exact_overlap[label].add(question)
                        if norm in norm_gold[label]: norm_overlap[label].add(norm)
                    if question not in prefix_lengths:
                        prefix, _ = rules.native_text(tok, question, row[4])
                        prefix_lengths[question] = len(tok.encode(prefix, add_special_tokens=False))
                    # Original A filter: native prompt + literal answer/EOS + ignored newline.
                    total = prefix_lengths[question] + n + 1 + newline_length
                    if not leaked and rules.complete(row[4]) and total <= rules.MAX_TOTAL_TOKENS:
                        qualified.append((row[1], row[2], n+1))
                counts.update(math_rows=len(rows), grouped_questions=1,
                              eligible_responses=len(qualified), decontamination_hit_parents=int(leaked),
                              questions_with_at_least_1_eligible=int(len(qualified)>=1),
                              questions_with_at_least_16_eligible=int(len(qualified)>=16))
                cardinalities[len(rows)] += 1
                ratio, cv = dispersion(lengths)
                if ratio is not None: ratios.append(ratio)
                else: counts['zero_min_length_questions'] += 1
                if cv is not None: cvs.append(cv)
                else: counts['zero_mean_length_questions'] += 1
                # Same original per-parent seed. Filter after shuffling original row identities.
                order = list(zip(rows, lengths))
                random.Random(rules.identity(parent+'p011')[:16]).shuffle(order)
                wanted = {(a,b) for a,b,_ in qualified}
                chosen = next((n+1 for row,n in order if (row[1],row[2]) in wanted), None)
                if chosen is not None: at_least_one[parent] = chosen
                if len(rows)==16 and len(qualified)==16: strict_sixteen[parent] = chosen
                parent_log.write(json.dumps({'parent_sha256':rules.identity(parent), 'responses':len(rows),
                    'eligible_responses':len(qualified), 'answer_lengths':lengths,
                    'max_min_ratio':ratio, 'coefficient_of_variation_population':cv,
                    'fixed_first_eligible_supervised_tokens':chosen})+'\n')
                if counts['grouped_questions'] % 1000 == 0:
                    parent_log.flush()
                    print(json.dumps({'utc':utc(), **counts, 'seconds':time.monotonic()-started}), flush=True)
        db.close()
        if counts['math_rows'] != spec['expected_ingested_math_rows']:
            raise ValueError('Full original math pool not exhausted exactly')
        values = np.asarray(lengths_all, dtype=np.uint32)
        result = {'completed_utc':utc(), 'counts':dict(counts),
            'different_questions_by_original_A_group_key':counts['grouped_questions'],
            'different_questions_by_exact_raw_text':len(exact_questions),
            'different_questions_by_whitespace_removed_casefold':len(normalized_questions),
            'answers_per_A_group_distribution':dict(sorted(cardinalities.items())),
            'questions_with_exactly_16_answers':cardinalities[16],
            'original_A_strict_exactly16_all_eligible_questions':len(strict_sixteen),
            'answer_only_student_token_lengths_no_EOS':{'mean':float(values.mean()),
                'median':float(np.quantile(values,.5,method='linear')), 'p90':float(np.quantile(values,.9,method='linear'))},
            'within_A_group_length_dispersion':{'median_max_min_ratio':float(np.median(ratios)),
                'median_population_coefficient_of_variation':float(np.median(cvs)),
                'zero_min_length_questions':counts['zero_min_length_questions'],
                'zero_mean_length_questions':counts['zero_mean_length_questions']},
            'benchmark_question_overlaps':{b:{'exact_distinct_raw_questions':len(exact_overlap[b]),
                'normalized_distinct_questions':len(norm_overlap[b])} for b in exact_gold},
            'K1_at_least_one_eligible_diagnostic_prefix':prefix_mass(at_least_one),
            'original_A_strict_pool_diagnostic_prefix':prefix_mass(strict_sixteen),
            'selection_note':'Sorted parent keys shuffled with seed20261020; original per-parent seeded row shuffle, first qualified row. One-pass supervised tokens include EOS; not a training dose or new training authorization.',
            'original_parent_key':'NFKC(question).strip()',
            'additional_normalization':'remove all Unicode whitespace then casefold; no extra NFKC',
            'original_eligibility':'boxed completeness, original exact/13-gram decontamination, native total length<=16384; completeness is not correctness',
            'source':'Existing read-only original raw SQLite index of the exact pinned local parquet ingestion; original metadata/source lock bound in SPEC.',
            'new_model_calls':0, 'old_training_encoding_or_filter_result_overwritten':False,
            'elapsed_seconds':time.monotonic()-started}
        create(out/'COUNTS.json', result)
        create(out/'COMPLETED.json', {'completed_utc':utc(),'counts_sha256':digest(result), 'new_model_calls':0})
    except BaseException as exc:
        create(out/'FAILED.json', {'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--spec',required=True);parser.add_argument('--review',required=True)
    args=parser.parse_args();run(args.spec,args.review)
