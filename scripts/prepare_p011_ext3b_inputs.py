"""Once-only new prefix/plans from completed12096 inputs; zero tokenization.

Neither original SQLite nor a tokenizer is opened. Previously completed token
lines are projected once into the new9072 prefix; no answer is encoded again.
Original raw/eligibility/census evidence is referenced, never reconstructed.
"""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from experiments.p011 import data_contract as rules
from experiments.p011.ext3b_contract import (DATA_SPEC, INPUTS, PRIOR_INPUTS,
    LARGE, SMALL, admit_data, prefix_metadata)
from experiments.p011.long_lr_r2_training import learning_rates
from experiments.p011.owner_0205_common import create,read,sha,utc


def copy_prefix(source, target, metadata):
    h=hashlib.sha256();size=0
    with Path(source).open('rb') as original, Path(target).open('xb') as output:
        for row in metadata:
            line=original.readline()
            if not line:raise ValueError('Saved prefix ended early')
            obj=json.loads(line)
            if any(obj[k]!=row[k] for k in ('path_id','parent_sha256','n_supervised','n_processed')):
                raise ValueError('Saved prefix token row identity/dose differs')
            output.write(line);h.update(line);size+=len(line)
    return {'bytes':size,'sha256':h.hexdigest(),'original_line_bytes_reused':len(metadata),
            'new_encodings':0,'source_full_file_not_rehashed':True}


def run(spec_path, review):
    spec=admit_data(spec_path,review)
    # Metadata bindings are small, independently accepted originals. Large old
    # native/raw archives and the census are not read or hashed a second time.
    for item in spec['prior_metadata_bindings']:
        if sha(item['path'])!=item['sha256']:raise ValueError('Prior metadata binding changed')
    prior=read(PRIOR_INPUTS/'COMPLETED.json');inventory=read(PRIOR_INPUTS/'MANIFEST.json')['files']
    if (prior['unique_selected_questions']!=12096 or prior['strict_subset_questions']!=3024
            or prior['GPU_calls']!=0):raise ValueError('Exact untrained completed original input corpus required')
    large,small=prefix_metadata(read(PRIOR_INPUTS/'ROW_METADATA.json'))
    INPUTS.mkdir(parents=True,exist_ok=False)
    create(INPUTS/'ATTEMPT.json',{'utc':utc(),'scope':'P011-ext-3B','source_CR':read(review),
        'new_encodings':0,'old_constructor_census_or_tokenizer_called':False,'automatic_retry':False})
    try:
        copied=copy_prefix(PRIOR_INPUTS/'ENCODED.jsonl',INPUTS/'ENCODED.jsonl',large)
        create(INPUTS/'ROW_METADATA.json',large)
        create(INPUTS/'PREFIX_SOURCE_BINDING.json',{'prior_input_manifest':spec['prior_metadata_bindings'][0],
            'prior_actual_target':'f679fa5c28f50b011c1d85a3a689c64997cc53d5',
            'prior_encoded':inventory['ENCODED.jsonl'],'prefix':copied,
            'selected_indices':list(range(9072)),'small_indices':list(range(3024)),
            'parent_order_and_answers_unchanged':True,'old_raw_and_eligibility_evidence_referenced_not_rebuilt':True})
        budget=sum(r['n_supervised'] for r in large);plans={}
        for name,rows in ((LARGE,large),(SMALL,small)):
            plan=rules.whole_schedule(rows,budget,17);create(INPUTS/(name+'_PLAN.json'),plan)
            counts=Counter(i for update in plan['updates'] for i in update)
            plans[name]={'questions':len(rows),'B':budget,'U':plan['optimizer_updates'],'q':plan['q'],
                'one_pass_supervised':sum(r['n_supervised'] for r in rows),
                'token_weighted_effective_E':budget/sum(r['n_supervised'] for r in rows),
                'presentation_count_distribution':dict(Counter(counts[i] for i in range(len(rows)))),
                'plan_sha256':sha(INPUTS/(name+'_PLAN.json'))}
        create(INPUTS/'RATES_S-F15.json',learning_rates(plans[LARGE]['U'],'S-F15'))
        # Local links to exact accepted originals; no duplicate endpoint file
        # construction/encoding/copy. The GPU transfer dereferences them once.
        for name in ('ENDPOINT_GPU.json','ENDPOINT_LOCAL.json'):
            (INPUTS/name).symlink_to((PRIOR_INPUTS/name).resolve())
        create(INPUTS/'COMPLETED.json',{'utc':utc(),'scope':'P011-ext-3B','cells':plans,
            'unique_selected_questions':9072,'strict_subset_questions':3024,
            'same_supervised_B_including_EOS':budget,'same_optimizer_updates':plans[LARGE]['U'],
            'relative_to_original_A7_B':budget/41813212,'original_encoded_prefix_byte_copies':9072,
            'new_answer_encodings':0,'new_endpoint_prompt_encodings':0,'new_census_scans':0,
            'GPU_calls':0,'actual_A2_accepted':False,'full_runtime_CR_and_actual_A2_still_required':True})
        files={p.name:({'bytes':copied['bytes'],'sha256':copied['sha256']} if p.name=='ENCODED.jsonl'
            else inventory[p.name] if p.is_symlink() else {'bytes':p.stat().st_size,'sha256':sha(p)})
            for p in sorted(INPUTS.iterdir()) if p.is_file()}
        create(INPUTS/'MANIFEST.json',{'files':files,'endpoint_links_to_original_input':True})
        print(json.dumps(read(INPUTS/'COMPLETED.json')),flush=True)
    except BaseException as exc:
        create(INPUTS/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',default=DATA_SPEC);p.add_argument('--review',required=True)
    a=p.parse_args();run(a.spec,a.review)
