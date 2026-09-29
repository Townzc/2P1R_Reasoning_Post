"""Frozen arithmetic decoding with cached metadata and durable raw batches.

The completion oracle, stopper, scoring, seed and sampling recipe are unchanged.
Only tokenizer metadata lookup frequency and pre-audit journaling differ from
``thursday_probe.arithmetic_eval.generate``.
"""
import json
import os
from pathlib import Path
import time

from experiments.thursday_probe.common import dump
from experiments.thursday_probe.arithmetic_eval import score
from src.sft_data import prefix


class _TokenizerMetadataCache:
    """Delegate tokenization while reusing immutable evaluation metadata.

    The unchanged TaskBoundaryStop queries these properties at each batch start.
    This proxy avoids querying the underlying tokenizer again for those starts.
    """
    def __init__(self, tokenizer, vocab_size, special_ids):
        self._tokenizer = tokenizer
        self._vocab_size = vocab_size
        self.all_special_ids = tuple(special_ids)

    def __len__(self):
        return self._vocab_size

    def __getattr__(self, name):
        return getattr(self._tokenizer, name)


def generate(model,tokenizer,rows,path,budget,samples=1,sampling=False,max_new_tokens=512,seed=2026091603,forced=None):
    import torch
    from transformers import GenerationConfig,StoppingCriteriaList
    from analyses.e017_stopping import TaskBoundaryStop
    from analyses.completion_contract import first_stop
    path=Path(path)
    if path.exists(): raise FileExistsError('No prediction overwrite')
    expanded=[(r,s) for r in rows for s in range(samples)]
    budget.reserve(path.name,len(expanded)); model.eval(); torch.manual_seed(seed)
    args={'do_sample':sampling,'num_beams':1,'max_new_tokens':max_new_tokens,
          'eos_token_id':tokenizer.eos_token_id,'pad_token_id':tokenizer.eos_token_id,'use_cache':True}
    if sampling: args.update(temperature=.7,top_p=.95,top_k=0)
    config=GenerationConfig(**args); dump(path.with_suffix('.generation.json'),{**args,'seed':seed,'samples':samples,'batch_size':8})
    vocab_size=len(tokenizer)
    special_ids=set(tokenizer.all_special_ids)
    stopping_tokenizer=_TokenizerMetadataCache(tokenizer,vocab_size,special_ids)
    records=[]
    with path.open('x') as f, path.with_suffix('.raw_batches.jsonl').open('x') as journal:
        for start in range(0,len(expanded),8):
            batch=expanded[start:start+8]
            prefixes=[(forced or {}).get(r['problem_id'],'') for r,_ in batch]
            ids=[tokenizer.encode(prefix(r['prompt'])+p,add_special_tokens=False) for (r,_),p in zip(batch,prefixes)]
            width=max(map(len,ids))
            if width+max_new_tokens>1024: raise ValueError('Generation context exceeded')
            inputs=torch.tensor([[tokenizer.eos_token_id]*(width-len(x))+x for x in ids],device='cuda')
            masks=torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids],device='cuda')
            stopper=TaskBoundaryStop(stopping_tokenizer,width,len(batch),max_new_tokens)
            tick=time.monotonic()
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                output=model.generate(input_ids=inputs,attention_mask=masks,generation_config=config,
                                      stopping_criteria=StoppingCriteriaList([stopper]))
            torch.cuda.synchronize(); seconds=time.monotonic()-tick
            # Persist the full returned tensors/events BEFORE any prefix, oracle
            # or score audit. A failed/interrupted audit must not lose generation.
            raw=dict(batch_index=start//8,start_index=start,batch_seconds=seconds,
                padded_prompt_width=width,problem_ids=[r['problem_id'] for r,_ in batch],
                sample_indices=[s for _,s in batch],forced_prefixes=prefixes,
                prompt_ids=ids,input_ids=inputs.tolist(),attention_mask=masks.tolist(),
                output_ids=output.tolist(),stop_events=stopper.events)
            journal.write(json.dumps(raw,allow_nan=False)+'\n');journal.flush();os.fsync(journal.fileno())
            if not torch.equal(output[:,:width],inputs): raise ValueError('Prompt prefix changed')
            all_ids=output[:,width:].tolist()
            decode=lambda ts:tokenizer.decode(ts,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            for (r,s),p,tokens,event in zip(batch,prefixes,all_ids,stopper.events):
                # Same independent whole-stream oracle and exact invalid-ID rule.
                oracle=first_stop(tokens,decode,tokenizer.eos_token_id,max_new_tokens,
                                  special_ids|{t for t in tokens if t>=vocab_size})
                if event!=oracle or any(t!=tokenizer.eos_token_id for t in tokens[event['retained_tokens']:]):
                    raise ValueError('Independent stop/padding audit failed')
                record={'problem_id':r['problem_id'],'sample_index':s,'task':r['task'],
                        'category':r.get('category'),'forced_prefix':p,'stop':event,
                        'generated_ids':tokens[:event['retained_tokens']],'batch_output_ids':tokens,
                        'prompt_ids':tokenizer.encode(prefix(r['prompt'])+p,add_special_tokens=False),
                        'batch_index':start//8,'batch_seconds':seconds,'score':score(r,event,p)}
                records.append(record); f.write(json.dumps(record,allow_nan=False)+'\n');f.flush()
            if len(records)%64==0 or len(records)==len(expanded):
                print(json.dumps({'evaluation':path.name,'generated':len(records),'reserved':len(expanded)}),flush=True)
            del inputs,masks,output
    return records
