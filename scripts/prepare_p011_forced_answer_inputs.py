"""Once-only new diagnostic inputs; reuse original token IDs and natural labels."""
import argparse
from collections import Counter
from pathlib import Path
from experiments.p011.owner_0205_common import admit, checked_metadata, create, digest, read, sha, utc
from experiments.p011.forced_answer import CELLS, SUFFIX, expected_math_ids, forced_request, loop_heuristic, original_digest


def run(spec_path, review_path):
    spec = admit(spec_path, review_path, 'p011-forced-answer-complete-path-CR')
    out = Path(spec['input_output'])
    out.mkdir(parents=True, exist_ok=False)
    create(out/'ATTEMPT.json', {'started_utc':utc(),'spec_sha256':sha(spec_path),
        'review_sha256':sha(review_path),'old_prompt_or_generated_token_reencoding':False,'automatic_retry':False})
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec['student_tokenizer_path'],local_files_only=True)
        for name, wanted in spec['student_tokenizer_files'].items():
            if sha(Path(spec['student_tokenizer_path'])/name) != wanted:
                raise ValueError('Pinned student tokenizer changed')
        suffix_ids = tok.encode(SUFFIX,add_special_tokens=False)
        if tok.decode(suffix_ids,skip_special_tokens=False,clean_up_tokenization_spaces=False) != SUFFIX:
            raise ValueError('Fixed suffix roundtrip differs')
        create(out/'SUFFIX.json', {'text':SUFFIX,'token_ids':suffix_ids,'text_sha256':digest(SUFFIX),'token_ids_sha256':digest(suffix_ids)})
        manifest = {'source_spec_sha256':sha(spec_path),'suffix_ids':suffix_ids,'suffix_sha256':digest(suffix_ids),
                    'cells':{},'posthoc_diagnostic':True,'original_primary_results_replaced':False}
        for cell in CELLS:
            cfg = spec['cells'][cell]
            # Only already saved proofs/metadata and original outputs are read here.
            for binding in cfg['metadata_bindings']: checked_metadata(binding)
            decoded = {r['id']:r for r in read(cfg['decoded_path']) if r['id'].startswith('math500:')}
            scoring_rows = {r['id']:r for r in read(cfg['scoring_rows_path']) if r['id'].startswith('math500:')}
            labels = {r['id']:r['score']['correct'] for r in read(cfg['saved_scored_rows_path']) if r['id'].startswith('math500:')}
            if set(decoded)!=expected_math_ids() or set(scoring_rows)!=set(decoded) or set(labels)!=set(decoded):
                raise ValueError('The original MATH500 sampled/greedy scope is not complete')
            raw, source_files = {}, {}
            for path in sorted((Path(cfg['payload_path'])/'raw').glob('eval_*.json')):
                source_files[str(path)] = sha(path)
                for row in read(path):
                    if row['id'].startswith('math500:'):
                        if row['id'] in raw: raise ValueError('Duplicate original raw row')
                        raw[row['id']] = row
            if set(raw)!=set(decoded): raise ValueError('Complete original MATH raw-token roster required')
            selected, diagnostics = [], {}
            exclusions = Counter({f'backend_length_{stop}{ending}':0
                for stop in ('native_eos','invalid_special_token') for ending in ('','_at_16384')})
            for row_id in sorted(raw):
                original = raw[row_id]
                if original_digest(original)!=decoded[row_id]['raw_record_sha256']:
                    raise ValueError('Original raw-to-oracle binding changed')
                if type(labels[row_id]) is not bool:
                    raise ValueError('Every original row requires its saved known Boolean')
                native_stop = decoded[row_id]['stop_reason']
                if native_stop=='length_cap':
                    selected.append(forced_request(original,decoded[row_id],suffix_ids))
                    diagnostics[row_id] = loop_heuristic(decoded[row_id]['answer_text'])
                elif native_stop not in ('native_eos','invalid_special_token'):
                    raise ValueError('Every unselected row needs its original known Boolean and native stop classification')
                elif original['answers'][0]['finish_reason']=='length':
                    exclusions['backend_length_'+native_stop] += 1
                    if len(original['answers'][0]['token_ids']) == 16384:
                        exclusions['backend_length_'+native_stop+'_at_16384'] += 1
            cell_root=out/cell
            create(cell_root/'REQUESTS.json',selected)
            create(cell_root/'ORIGINAL_LABELS_AND_GOLD.json',{'labels':labels,
                'gold':{k:v['gold'] for k,v in scoring_rows.items()}, 'truncation_diagnostics':diagnostics,
                'natural_labels_reused_without_rescoring':True})
            record={'count':len(selected),'ids':[r['id'] for r in selected],
                'request_file_sha256':sha(cell_root/'REQUESTS.json'),
                'original_labels_file_sha256':sha(cell_root/'ORIGINAL_LABELS_AND_GOLD.json'),
                'source_raw_files':source_files,
                'original_job_id':cfg['original_job_id'],'model_path':cfg['remote_model_path'],
                'model_files':cfg['model_files'],'eos_token_ids':cfg['eos_token_ids'],
                'required_context':max((len(r['prompt_token_ids'])+64 for r in selected),default=16449),
                'prefill_tokens':sum(len(r['prompt_token_ids']) for r in selected),
                'all_natural_labels_reused':True,
                'selection':'saved_native_stop_reason_length_cap_only',
                'backend_length_native_exclusions':dict(exclusions)}
            if record['required_context']>32768: raise ValueError('Unexpected context exceeds the reviewed model capacity')
            create(cell_root/'COMPLETED.json',record);manifest['cells'][cell]=record
        create(out/'INPUT_MANIFEST.json',manifest)
        create(out/'COMPLETED.json', {'completed_utc':utc(),'manifest_sha256':sha(out/'INPUT_MANIFEST.json'),
            'forced_rows':sum(x['count'] for x in manifest['cells'].values()),
            'prefill_tokens':sum(x['prefill_tokens'] for x in manifest['cells'].values()),'new_model_calls':0})
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--review',required=True)
    a=p.parse_args();run(a.spec,a.review)
