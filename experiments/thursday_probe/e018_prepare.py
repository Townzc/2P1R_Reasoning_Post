"""Reconstruct only the 253 approved training anchors and 64 observed inputs."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from experiments.thursday_probe.common import dump, jsonl, stamp
from scripts.audit_family_matching import verified_tokenizer
from src.real_math_audit import sha, normalized
from src.real_math_engineering import parent_index
from src.sft_data import read_jsonl, encode_row, budget_report, sha256_file

OUT = Path('experiments/thursday_probe/e018_inputs_r1')
PROPOSAL = Path('configs/diagnostics/real_math_p006_proposal.json')


def prepare(parents_path, candidates_path, tokenizer_path):
    if OUT.exists():
        raise FileExistsError('Immutable E018 inputs already exist')
    cfg = json.loads(PROPOSAL.read_text())
    old = json.loads(Path('configs/real_math_e013/overfit.json').read_text())
    freeze = json.loads(Path('reports/real_math_c017_parents_r2/freeze.json').read_text())
    if sha256_file(parents_path) != freeze['private_problem_records_sha256'] or sha256_file(candidates_path) != old['raw_candidates_sha256']:
        raise ValueError('Private C017 source hash differs')
    for name in ('selection', 'training_dose'):
        if sha256_file(cfg['evidence'][name+'_path']) != cfg['evidence'][name+'_sha256']:
            raise ValueError('P006 frozen input hash differs')
    selection = read_jsonl(cfg['evidence']['selection_path'])
    wanted = {d['problem_id'] for d in selection}
    # Examine only ID bytes before parsing an original problem record; reserved
    # question text is never loaded into a parsed record or emitted.
    parents = {}
    with Path(parents_path).open('rb') as f:
        for line in f:
            match = re.search(rb'"id"\s*:\s*"([^"\\]+)"', line)
            if match and match[1].decode() in wanted:
                r = json.loads(line); parents[r['id']] = r
    raw = {(r['problem_id'], r['candidate_index']): r for r in read_jsonl(candidates_path)
           if r['problem_id'] in wanted}
    index = parent_index(old)
    train = []
    tokenizer, tok = verified_tokenizer(Path(tokenizer_path))
    for d in selection:
        p = parents[d['problem_id']]; source = raw[(d['problem_id'], d['candidate_index'])]
        meta = index[d['problem_id']]
        if meta['partition'] != 'audit_draw' or meta['exclusions'] or p['group_id'] != meta['group_id']:
            raise ValueError('Training group identity or partition differs')
        if sha(p['problem']) != meta['problem_sha256'] or sha(p['answer']) != meta['answer_sha256']:
            raise ValueError('Original problem/answer differs')
        if any(source[k] != d[k] for k in ('shard','row_index')) or sha(json.dumps(source['row'], ensure_ascii=False, sort_keys=True)) != d['source_row_sha256']:
            raise ValueError('Response source differs')
        if source['row']['problem_source'] != 'gsm8k' or normalized(source['row']['problem']) != normalized(p['problem']):
            raise ValueError('Source question mismatch')
        response = source['row']['generated_solution']
        if sha(response) != d['response_sha256']:
            raise ValueError('Response bytes differ')
        row = {'problem_id': p['id'], 'group_id': p['group_id'], 'prompt': p['problem'],
               'answer': p['answer'], 'response': response, 'path_id': str(d['candidate_index']), 'source': d}
        enc = encode_row(row, tokenizer, 1024)
        if any(enc[k] != d[k] for k in ('n_prompt','n_supervised','n_processed')):
            raise ValueError('Exact token mask/count differs')
        train.append(row)
    dev = read_jsonl('reports/real_math_e017_inputs_r1/rows.jsonl')
    if {r['group_id'] for r in train} & {r['group_id'] for r in dev}:
        raise ValueError('Train/dev overlap')
    dose = json.loads(Path(cfg['evidence']['training_dose_path']).read_text())
    schedule = [r['row_indices'] for r in dose['updates']]
    encoded = [encode_row(r, tokenizer, 1024) for r in train]
    budget = budget_report(encoded, schedule, 1)
    if len(train) != 253 or len(dev) != 64 or len(schedule) != 64 or budget['supervised_response_tokens'] != 77192:
        raise ValueError('E018 predetermined dose differs')
    OUT.mkdir()
    jsonl(OUT/'train.jsonl', train); jsonl(OUT/'dev.jsonl', dev)
    dump(OUT/'schedule.json', schedule); dump(OUT/'budget.json', budget)
    dump(OUT/'learning_rates.json', cfg['training']['learning_rate']['values_by_one_based_update'])
    quality = set(cfg['training']['quality_sample']['problem_ids'])
    jsonl(OUT/'quality_32.jsonl', [r for pid in cfg['training']['quality_sample']['problem_ids'] for r in train if r['problem_id'] == pid])
    dump(OUT/'manifest.json', {'phase':'E018_INPUTS', 'created_at_utc':stamp(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'tokenizer':tok, 'parents':253, 'quality_sample_count':len(quality),
        'reserved_text_accessed':False, 'official_test_accessed':False,
        'proposal_sha256':sha256_file(PROPOSAL), 'source_files_sha256':{'experiments/thursday_probe/e018_prepare.py':sha256_file(__file__)},
        'files_sha256':{p.name:sha256_file(p) for p in OUT.iterdir() if p.is_file()},
        'attribution':{'questions':'OpenAI GSM8K, MIT, original train only',
                       'responses':'NVIDIA OpenMathInstruct-2, CC-BY-4.0, unchanged selected responses',
                       'source':'https://huggingface.co/datasets/nvidia/OpenMathInstruct-2',
                       'response_revision':'469216e3f46f4dacf476b382e192485ea51a143e'}})
    return {'parents':len(train), 'observed_dev':len(dev), 'updates':len(schedule),
            'supervised_tokens':budget['supervised_response_tokens'], 'quality_review_pending':True}


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--parents',required=True)
    p.add_argument('--candidates',required=True); p.add_argument('--tokenizer-dir',required=True)
    a=p.parse_args(); print(json.dumps(prepare(a.parents,a.candidates,a.tokenizer_dir),indent=2))
