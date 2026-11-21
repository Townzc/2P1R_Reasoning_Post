"""CPU-only privacy and regression checks; no service client or paid calls."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, '.')
from experiments.p012 import tinker_lora as original

HERE = Path(__file__).parent
LOCAL = Path('.local/p012_20261111/amendment10_v1')
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    candidate = load('experiments.p012.a10_candidate', HERE/'candidate/tinker_lora.py')
    config = load('a10_config_candidate', HERE/'candidate/training_config.py')
    manifest = read('reports/p012_20261111/amendment10_s1_v1/MANIFEST.json')
    request = manifest['student']; tokenizer, renderer = candidate.load_renderer(request)
    inputs = read(request['input_path'])
    rows = [{'id':r['id'], 'messages':[{'role':'user','content':r['prompt']}]} for r in inputs]
    assert len(rows) == 1572
    output_tokens = tokenizer.encode('\\boxed{A}<|im_end|>', add_special_tokens=False)

    class Client:
        model_path = 'CPU_fixture_no_model_call'
        calls = 0

        def sample(self, prompt, num_samples, sampling_params):
            assert num_samples == 1 and sampling_params.max_tokens == 4096
            assert sampling_params.temperature == 0
            self.calls += 1
            response = SimpleNamespace(prompt_cache_hit_tokens=0, sequences=[SimpleNamespace(
                tokens=output_tokens, stop_reason='stop', sequence_id='cpu-'+str(sampling_params.seed))])
            return SimpleNamespace(result=lambda:response)

    with tempfile.TemporaryDirectory(prefix='cpu_candidate_', dir=LOCAL) as tmp:
        dest = Path(tmp)/'logiqa'; client = Client()
        candidate.generate(client,tokenizer,renderer,rows,{'task':'logiqa','sha256':'cpu-fixture'},dest)
        raw = [json.loads(x) for x in (dest/'raw.jsonl').read_text().splitlines()]
        assert len(raw) == client.calls == 1572
        for r,inp in zip(raw,inputs,strict=True):
            assert r['id'] == inp['id']
            assert 'prompt_token_ids' not in r
            assert r['prompt_tokens_sha256'] == inp['prompt_tokens_sha256']
            assert r['prompt_sha256'] == inp['prompt_sha256']
            assert inp['prompt'] not in json.dumps(r,ensure_ascii=False)
        assert read(dest/'MANIFEST.json')['config']['protocol'] == 'logiqa_a10'
        for n,temp,subset in [(8,.7,rows),(1,0,rows[:20])]:
            try:
                candidate.generate(Client(),tokenizer,renderer,subset,{'task':'logiqa','sha256':'fixture'},Path(tmp)/str(n),n,temp)
            except ValueError as exc: assert 'full1572' in str(exc)
            else: raise AssertionError('Invalid LogiQA dose accepted')
        legacy = [{'id':'fixture','problem':'What is 1 + 1?'}]
        original.generate(Client(),tokenizer,renderer,legacy,{'task':'math','sha256':'fixture'},Path(tmp)/'before')
        candidate.generate(Client(),tokenizer,renderer,legacy,{'task':'math','sha256':'fixture'},Path(tmp)/'after')
        for name in ['raw.jsonl','MANIFEST.json','GENERATION_COMPLETE.json','USAGE.json']:
            assert (Path(tmp)/'before'/name).read_bytes() == (Path(tmp)/'after'/name).read_bytes()
    row = {'parent_id':'synthetic','problem':'PRIVATE_PROMPT_MARKER','solution':'\\boxed{A}',
           'solution_hash':hashlib.sha256(b'\\boxed{A}').hexdigest(),'draw':0}
    _,rendered = candidate.rendered_datum(row,tokenizer,renderer)
    safe = candidate.render_samples([row],[rendered],True)
    assert 'PRIVATE_PROMPT_MARKER' not in json.dumps(safe)
    assert not ({'problem','input_token_ids','rendered_text','loss_weights'} & safe[0].keys())
    assert candidate.render_samples([row],[rendered]) == [dict(row,**rendered)]
    before = {x.name:ast.dump(x) for x in ast.parse(Path('experiments/p012/tinker_lora.py').read_text()).body if isinstance(x,ast.FunctionDef)}
    after = {x.name:ast.dump(x) for x in ast.parse((HERE/'candidate/tinker_lora.py').read_text()).body if isinstance(x,ast.FunctionDef)}
    unchanged = ['epoch_order','cosine_lr','load_renderer','normalize_batch','generation_messages']
    assert all(before[k] == after[k] for k in unchanged)
    assert sha(HERE/'candidate/tinker_lora.py') == sha('reports/p012_20261111/amendment10_overlength_review_v1/proposed_tinker_lora.py')
    assert config.grid_dose('A10_R8')['expected_updates'] == 512
    result = {'paid_model_calls':0,'real_frozen_test_prompts_checked':1572,'public_prompt_privacy':True,
        'generation_prefix_matches_pilot_for_all1572':True,'invalid_doses_rejected':2,
        'legacy_math_generation_byte_identical':True,'private_training_preview':True,
        'unchanged_functions':unchanged,'R8_updates':512,
        'accepted_LogiQA_length_review_commit':'f0369f2590dfd4f70dab909c81a9d386bde672ae',
        'candidate_equals_accepted_overlength_proposal':True,
        'candidate_sha256':sha(HERE/'candidate/tinker_lora.py'),
        'training_config_candidate_sha256':sha(HERE/'candidate/training_config.py')}
    (HERE/'CPU_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
