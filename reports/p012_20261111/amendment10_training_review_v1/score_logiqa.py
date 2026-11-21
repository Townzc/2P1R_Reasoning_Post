"""A10 evidence adapter using the audited, unchanged pilot letter scorer.

Requires the combined source review and a published timestamped prediction.
No model calls, private prompts in output, or alternate answer rules.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, '.')
PUBLIC = Path(__file__).resolve().parent.relative_to(Path.cwd())
PILOT = Path('reports/p012_20261111/amendment9_logiqa_v1/logiqa_pilot.py')
PILOT_SHA = '0611b495fbc796f0bd316ca9ee2f854b60971b3889238a098828d62dea7644dc'
AUTHORITY = 'f42dcd1595807406f67ff694e5235447c6814ebc'
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def score(directory):
    accepted=read(PUBLIC/'ACCEPTED_REVIEW.json')
    assert re.fullmatch('[a-f0-9]{40}',accepted['commit'])
    assert accepted['score_adapter_sha256']==sha(__file__)
    assert sha(PILOT)==PILOT_SHA
    spec=importlib.util.spec_from_file_location('frozen_pilot',PILOT)
    pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
    request=read(directory/'request.json');result=directory/'result'
    assert request['accepted_review_commit']==accepted['commit']
    assert request['authority_commit']==AUTHORITY and request['task']=='logiqa'
    assert request['source_sha256']==accepted['runner_sha256']
    assert read(result/'COMPLETE.json')['success']
    generation=result/'generation';manifest=read(generation/'MANIFEST.json')
    cfg=manifest['config']
    assert (cfg['protocol'],cfg['task'],cfg['n'],cfg['temperature'],cfg['max_tokens'],cfg['max_model_len'])==('logiqa_a10','logiqa',1,0,4096,8192)
    evaluation=read(PUBLIC/'EVALUATION_MANIFEST.json')
    assert manifest['input_sha256']==request['evaluation']['sha256']==evaluation['private_input_sha256']
    assert sha(evaluation['public_identities_path'])==evaluation['public_identities_sha256']
    inputs=read(evaluation['public_identities_path']);assert len(inputs)==1572
    raw=generation/'raw.jsonl';records=[json.loads(x) for x in raw.read_text().splitlines()]
    complete=read(generation/'GENERATION_COMPLETE.json')
    assert complete['draws']==1572 and complete['raw_sha256']==sha(raw)
    freeze=read(directory/'PREDICTION_BEFORE_SCORE.json')
    assert freeze['authority_commit']==AUTHORITY and freeze['raw_sha256']==sha(raw)
    assert datetime.datetime.fromisoformat(freeze['utc']).tzinfo is not None
    assert len(records)==1572 and len({r['sequence_id'] for r in records})==1572
    labels=[]
    for i,(r,x) in enumerate(zip(records,inputs,strict=True)):
        assert (r['id'],r['draw'],r['sampling_seed'])==(x['id'],0,request['seed']+i)
        assert r['prompt_sha256']==x['prompt_sha256'] and r['prompt_tokens_sha256']==x['prompt_tokens_sha256']
        assert 'prompt_token_ids' not in r
        labels.append(pilot.label(r,x['gold']))
    dest=directory/'score_v1';dest.mkdir(exist_ok=False)
    (dest/'labels.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in labels))
    correct=sum(x['correct'] for x in labels);normal=sum(not x['unfinished'] for x in labels)
    output={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':request['run_id'],
        'authority_commit':AUTHORITY,'accepted_source_review_commit':accepted['commit'],
        'source_sha256':sha(__file__),'pilot_scorer_sha256':PILOT_SHA,
        'raw_sha256':sha(raw),'labels_sha256':sha(dest/'labels.jsonl'),
        'evaluation_identities_sha256':evaluation['public_identities_sha256'],
        'responses':1572,'correct':correct,'accuracy':correct/1572,
        'unfinished_count':1572-normal,'unfinished_rate':(1572-normal)/1572,
        'answer_only_count':sum(x['answer_only'] for x in labels),
        'answer_only_rate':sum(x['answer_only'] for x in labels)/1572,
        'normally_terminated_count':normal,'normally_terminated_correct':correct,
        'normally_terminated_accuracy':correct/normal if normal else None,
        'missing_box_count':sum(x['missing_box'] for x in labels),
        'invalid_box_count':sum(x['invalid_or_incomplete_box'] for x in labels),
        'independent_result_audit':'pending','exploratory':True,'excluded_from_H0_H3':True}
    (dest/'RESULTS.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ['run_id','responses','correct','accuracy','unfinished_count','answer_only_count']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    score(parser.parse_args().directory)
