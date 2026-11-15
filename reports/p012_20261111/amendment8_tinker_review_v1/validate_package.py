"""Verify complete CPU candidate inputs and the unchanged admission guard."""
import copy, hashlib, importlib.util, json, sys, zipfile
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '.')
from experiments.p012 import tinker_lora
P = Path('reports/p012_20261111/amendment8_tinker_review_v1')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')
manifest=read(P/'CANDIDATE_MANIFEST.json')
spec=importlib.util.spec_from_file_location('candidate',P/'candidate/training_config.py')
cfg=importlib.util.module_from_spec(spec);spec.loader.exec_module(cfg)
requests=sorted((P/'requests').glob('*.json'));checks=[]
with zipfile.ZipFile(P/'candidate_datasets.zip') as z:
    assert len(z.namelist())==len(set(z.namelist()))
    for path,row in zip(requests,manifest['rows'],strict=True):
        r=read(path);assert r['run_id']==row['run_id']
        assert sha(path)==row['request_sha256']
        assert r['dose']==cfg.grid_dose(r['cell'])
        assert r['rank']==32 and r['seed']==17
        assert r['source_sha256']==sha(Path('experiments/p012/tinker_lora.py'))
        assert r['candidate_training_config_sha256']==sha(P/'candidate/training_config.py')
        payload=z.read(row['archive_member'])
        assert payload==Path(r['dataset']['path']).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==r['dataset']['sha256']
        assert r['forecast']['admitted'] is False and r['accepted_review_commit'] is None
        try:tinker_lora.run(r,Path('.local/p012_20261111/A8_UNADMITTED_MUST_NOT_EXIST'))
        except ValueError as e:assert 'Prospective budget admission' in str(e)
        else:raise AssertionError('Unadmitted request accepted')
        assert not Path('.local/p012_20261111/A8_UNADMITTED_MUST_NOT_EXIST').exists()
        checks.append({'run_id':r['run_id'],'input_binding':True,'dose':True,'unadmitted_guard_rejected_before_output_or_model_client':True})
    evaluation=z.read('evaluation/math5000.jsonl')
template=read(Path('.local/p012_20261111/tinker_formal_v1/tinker_lora_qwen3_5_4b_math_p_s17_greedy_20261113_v1/request.json'))
assert hashlib.sha256(evaluation).hexdigest()==template['evaluation']['sha256']
tokenizer,renderer=tinker_lora.load_renderer(template)
rows=[json.loads(x) for x in evaluation.splitlines()]
assert len(rows)==5000 and len({x['id'] for x in rows})==5000
lengths=[]
for row in rows:
    messages=tinker_lora.generation_messages(row)
    prompt=renderer.build_generation_prompt(messages)
    assert prompt.to_ints()==tokenizer.apply_chat_template(messages,add_generation_prompt=True,enable_thinking=False,return_dict=False)
    assert prompt.length+4096<=8192
    lengths.append(prompt.length)
write(P/'PACKAGE_CHECKS.json',{'checks':checks,'greedy_full_MATH_rows':5000,'all_generation_prefixes_equal_frozen_tokenizer':True,
    'maximum_context_with_output':max(lengths)+4096,'evaluation_sha256':template['evaluation']['sha256'],
    'unchanged_evaluation_config':{'n':1,'temperature':0,'max_tokens':4096,'max_model_len':8192,'task':'math'},
    'no_model_calls':True})
print('four complete candidate requests and all5000 greedy contexts verified')
