"""Synthetic-only A10 scorer-adapter binding checks; no accepted-review file is installed."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def main():
    path=HERE/'score_logiqa.py'
    spec=importlib.util.spec_from_file_location('a10_score_fixture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    identities=read(HERE/'EVALUATION_IDENTITIES.json')
    passed=[]
    with tempfile.TemporaryDirectory(prefix='score_fixture_',dir='.local/p012_20261111/amendment10_v1') as tmp:
        root=Path(tmp)
        for case in ['valid','swapped_order','wrong_prompt_hash','wrong_prediction','unaccepted_review']:
            public=root/case/'review';directory=root/case/'endpoint';generation=directory/'result/generation'
            module.PUBLIC=public
            identity_path=public/'identities.json';write(identity_path,identities)
            write(public/'EVALUATION_MANIFEST.json',{'private_input_sha256':'fixture-input',
                'public_identities_path':str(identity_path),'public_identities_sha256':sha(identity_path)})
            write(public/'ACCEPTED_REVIEW.json',{'commit':'a'*40,'score_adapter_sha256':sha(path),'runner_sha256':'fixture-runner'})
            request={'accepted_review_commit':'a'*40,'authority_commit':module.AUTHORITY,'task':'logiqa',
                'source_sha256':'fixture-runner','evaluation':{'sha256':'fixture-input'},'seed':17,'run_id':'CPU_SYNTHETIC_ONLY'}
            if case=='unaccepted_review':request['accepted_review_commit']='b'*40
            write(directory/'request.json',request)
            write(directory/'result/COMPLETE.json',{'success':True})
            write(generation/'MANIFEST.json',{'config':{'protocol':'logiqa_a10','task':'logiqa','n':1,
                'temperature':0,'max_tokens':4096,'max_model_len':8192},'input_sha256':'fixture-input'})
            raw=[]
            for i,x in enumerate(identities):
                raw.append({'id':x['id'],'draw':0,'sampling_seed':17+i,'sequence_id':f'cpu-{i}',
                    'prompt_sha256':x['prompt_sha256'],'prompt_tokens_sha256':x['prompt_tokens_sha256'],
                    'text':('word '*20 if i%3==0 else '')+'\\boxed{'+x['gold']+'}',
                    'finish_reason':'length' if i%11==0 else 'stop'})
            if case=='swapped_order':raw[0],raw[1]=raw[1],raw[0]
            if case=='wrong_prompt_hash':raw[0]['prompt_tokens_sha256']='wrong'
            raw_path=generation/'raw.jsonl';raw_path.write_text(''.join(json.dumps(x)+'\n' for x in raw))
            write(generation/'GENERATION_COMPLETE.json',{'draws':1572,'raw_sha256':sha(raw_path)})
            write(directory/'PREDICTION_BEFORE_SCORE.json',{'authority_commit':module.AUTHORITY if case!='wrong_prediction' else 'b'*40,
                'raw_sha256':sha(raw_path),'utc':'2026-11-20T00:00:00+00:00'})
            if case=='valid':
                with contextlib.redirect_stdout(io.StringIO()):module.score(directory)
                result=read(directory/'score_v1/RESULTS.json')
                assert result['correct']==result['normally_terminated_count']==1429
                assert result['unfinished_count']==143 and result['answer_only_count']==1048
                assert result['normally_terminated_accuracy']==1
            else:
                try:module.score(directory)
                except AssertionError:pass
                else:raise AssertionError('Invalid binding accepted: '+case)
                assert not (directory/'score_v1').exists()
            passed.append(case)
    result={'synthetic_only':True,'real_output_scoring_performed':False,'paid_model_calls':0,
        'checks_passed':passed,'identities_per_fixture':1572,'score_adapter_sha256':sha(path)}
    write(HERE/'CPU_SCORING_CHECKS.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
