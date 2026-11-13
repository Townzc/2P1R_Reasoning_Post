"""Regression for correlated server num_samples results; no API/model calls."""
import json
import sys
from types import SimpleNamespace
import pytest
from experiments.p012.tinker_lora import generate


class SamplingClient:
    model_path='fixed-model'

    def __init__(self):
        self.calls=[]

    def sample(self,prompt,*,num_samples,sampling_params):
        self.calls.append((num_samples,sampling_params))
        # A server that repeats one seeded output when asked for n samples.
        seq=SimpleNamespace(tokens=[sampling_params.seed,99],stop_reason='stop',sequence_id=str(sampling_params.seed))
        response=SimpleNamespace(sequences=[seq]*num_samples,prompt_cache_hit_tokens=1)
        return SimpleNamespace(result=lambda:response)


@pytest.mark.parametrize('n,temperature',[(1,0.0),(8,0.7)])
def test_draws_are_independently_seeded_without_changing_greedy(tmp_path,monkeypatch,n,temperature):
    monkeypatch.setitem(sys.modules,'tinker',SimpleNamespace(SamplingParams=lambda **kw:SimpleNamespace(**kw)))
    prompt=SimpleNamespace(to_ints=lambda:[10,11],length=2)
    renderer=SimpleNamespace(build_generation_prompt=lambda messages:prompt,get_stop_sequences=lambda:[99])
    tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**kw:[10,11],decode=lambda tokens,**kw:str(tokens))
    rows=[{'id':str(i),'messages':[{'role':'user','content':'question'}]} for i in range(2)]
    client=SamplingClient();out=tmp_path/'generation'
    usage=generate(client,tokenizer,renderer,rows,{'task':'math','sha256':'frozen'},out,n=n,temperature=temperature,seed=17,concurrency=4)
    records=[json.loads(line) for line in (out/'raw.jsonl').open()]
    assert [(r['id'],r['draw']) for r in records]==[(str(i),j) for i in range(2) for j in range(n)]
    assert len({tuple(r['token_ids']) for r in records})==2*n
    assert all(count==1 and params.temperature==temperature and params.max_tokens==4096 and params.stop==[99] for count,params in client.calls)
    assert [r['sampling_seed'] for r in records]==list(range(17,17+2*n))
    assert usage=={'prefill_tokens_uncached_upper':4*n,'completion_tokens':4*n,'prompt_cache_hit_tokens':2*n}
    if n==1:
        assert [r['token_ids'] for r in records]==[[17,99],[18,99]]
