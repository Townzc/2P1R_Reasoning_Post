"""Construct all exact kwargs with the unmodified pinned-wheel Python class.

On macOS only import-time logger/type annotations are adapted. This is not a
Linux/CUDA/V1 engine test and must not be reported as one.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import sys
import types
import typing
sys.path.insert(0,'.')
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.learning_regime_p009.stage0_generation_contract import DATASETS,load_rows,sampling

r=Path('.local/p009_20261014/r1/samplingparams_readiness_r1')
assert not (r/'CONSTRUCTOR_PROOF.json').exists()
wheel=read(r/'WHEEL_READBACK.json')
source=r/'wheel_sampling_params.py'
assert source.read_bytes()==(r/'sampling_params.py').read_bytes()
root=types.ModuleType('vllm');root.__path__=[];sys.modules['vllm']=root
adapters={
    'vllm.logger':dict(init_logger=logging.getLogger),
    'vllm.logits_process':dict(LogitsProcessor=typing.Callable),
    'vllm.transformers_utils.tokenizer':dict(AnyTokenizer=typing.Any),
}
for name,values in adapters.items():
    module=types.ModuleType(name);module.__dict__.update(values);sys.modules[name]=module
spec=importlib.util.spec_from_file_location('vllm.sampling_params',source)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
started=datetime.now(timezone.utc).isoformat();records=[];counts={}
for name,ds in DATASETS.items():
    rows=load_rows(r.parent/'stage0_inputs_r1',name);counts[name]=0
    for row in rows:
        original=sampling(name,row);obj=module.SamplingParams(**original)
        keys=['n','temperature','top_p','top_k','repetition_penalty','max_tokens','seed',
              'stop_token_ids','ignore_eos','detokenize','skip_special_tokens','include_stop_str_in_output']
        assert all(getattr(obj,k)==original[k] for k in keys),(name,row['candidate_id'])
        expected=module.SamplingType.RANDOM_SEED if ds['procurement'] else module.SamplingType.GREEDY
        assert obj.sampling_type==expected
        assert obj.truncate_prompt_tokens is None and obj.min_tokens==0
        records.append(dict(dataset=name,id=row['candidate_id'],kwargs_sha256=digest(original),sampling_type=obj.sampling_type.name))
        counts[name]+=1
assert sum(counts.values())==14450
proof=dict(schema='p009_exact_wheel_sampling_constructor_isolated_v1',passed=True,
    started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
    wheel=wheel,wheel_python_module_sha256=sha(source),github_tag_module_identical=True,
    constructor_module_bytes_modified=False,objects_constructed=14450,counts=counts,
    ordered_objects_digest=digest(records),exact_contract_sha256=sha('experiments/learning_regime_p009/stage0_generation_contract.py'),
    input_file_shas={ds['file']:ds['sha256'] for ds in DATASETS.values()},
    python=sys.version,host=platform.platform(),
    dependency_versions={n:importlib.metadata.version(n) for n in ('msgspec','pydantic','pydantic-core')},
    import_adapters={k:list(v) for k,v in adapters.items()},
    limits='Unmodified wheel SamplingParams class executed with actual msgspec/pydantic; import-time logging/type-only adapters on macOS. No full vLLM package, Linux, V1 sampler, CUDA graph, throughput or model validation.',
    gpu_calls=0,model_calls=0,cloud_calls=0,outputs_generated=0,
    full_linux_runtime_verified=False,reviewer_acceptance_required=True)
dump(r/'CONSTRUCTOR_PROOF.json',proof)
print(json.dumps(proof,indent=2))
