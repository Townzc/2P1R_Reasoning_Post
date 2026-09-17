"""Durable, bounded reference forwards and passive greedy/logit alignment.

Alignment observes existing generation; it never calls a model a second time.
Raw/effective vectors use IEEE754 float32 bit patterns for lossless JSON storage.
"""
from contextlib import contextmanager, nullcontext
import json
import math
from pathlib import Path
import time

from experiments.thursday_probe.common import digest
from experiments.post_e037_goal_training.generation import _atomic, _read, _file_hash, _caller_state
from src.sft_data import encode_row
from .decision_spans import validate_mask


class DiagnosticConsistencyError(RuntimeError):
    pass


def _device(model, device):
    if device is not None:return device
    return str(next(model.parameters()).device)


def _forward(model, ids, device, *, use_cache=False):
    import torch
    if not ids or len(ids)>1024 or any(type(x) is not int or x<0 for x in ids):
        raise ValueError('Diagnostic input must contain 1..1024 valid token IDs')
    inputs=torch.tensor([ids],device=device)
    context=torch.autocast('cuda',dtype=torch.bfloat16) if str(device).startswith('cuda') else nullcontext()
    if str(device).startswith('cuda'):torch.cuda.synchronize()
    tick=time.monotonic()
    with torch.inference_mode(),context:
        logits=model(input_ids=inputs,attention_mask=torch.ones_like(inputs),use_cache=use_cache).logits
    if str(device).startswith('cuda'):torch.cuda.synchronize()
    return logits,dict(forward_calls=1,input_tokens=len(ids),seconds=time.monotonic()-tick,
                       logits_dtype=str(logits.dtype),use_cache=use_cache)


def _stats(logits, target):
    import torch
    vector=logits.float();logp=vector.log_softmax(-1);top=vector.max()
    return dict(token_id=int(target),logit=vector[target].item(),log_probability=logp[target].item(),
        probability=logp[target].exp().item(),strictly_higher_tokens=int((vector>vector[target]).sum()),
        equal_logit_tokens=int((vector==vector[target]).sum()),argmax_tokens=(vector==top).nonzero().flatten().tolist(),
        tie_rule='exact equality of observed float32 logits; torch first-index argmax')


def decomposition_record(model,tokenizer,row,span,device):
    encoded=encode_row(row,tokenizer,1024);validate_mask(encoded,span)
    if span['source_row_sha256']!=digest(row):raise ValueError('Reference row/span identity differs')
    logits,timing=_forward(model,encoded['input_ids'],device)
    positions=[i for i,x in enumerate(encoded['labels']) if i>0 and x!=-100]
    if not positions:raise ValueError('No supervised reference tokens')
    shifted=logits[0].float().log_softmax(-1)
    values=[shifted[i-1,encoded['input_ids'][i]].item() for i in positions]
    if any(not math.isfinite(x) for x in values):raise FloatingPointError('Nonfinite reference token log probability')
    masks={k:[span[k][i] for i in positions] for k in
           ('decision_mask','program_operator_mask','input_copy_mask','computed_numeric_mask') if k in span}
    def partition(mask):
        numbers=[-v for v,m in zip(values,mask) if m]
        return dict(tokens=len(numbers),nll_sum=sum(numbers),mean_nll=sum(numbers)/len(numbers) if numbers else None)
    parts={name:partition(mask) for name,mask in masks.items()}
    parts['full']=partition([True]*len(values));parts['rest']=partition([not x for x in masks['decision_mask']])
    selected=[i for i in positions if span['decision_mask'][i]]
    record=dict(problem_id=row['problem_id'],source_row_sha256=digest(row),dataset_row_id=row.get('dataset_row_id'),
        group_id=row.get('group_id'),target_index=row.get('target_index'),interface=row.get('interface'),
        prompt_ids=encoded['input_ids'][:encoded['n_prompt']],response_ids=[encoded['input_ids'][i] for i in positions],
        input_ids=encoded['input_ids'],response_token_positions=positions,causal_logit_positions=[i-1 for i in positions],
        response_log_probabilities=values,response_masks=masks,full_token_masks={k:span[k] for k in masks},
        decision_token_indices=selected,decision_token_statistics=[_stats(logits[0,i-1],encoded['input_ids'][i]) for i in selected],
        partitions=parts,encoded_row_sha256=digest(encoded),span_sha256=digest(span),
        first_literal_deviation=None,first_semantic_error='unknown',dead_end_prefix='unknown',
        semantic_note='Reference likelihood alone does not classify an alternative free program as wrong or dead.',
        **timing)
    return record


def candidate_context(span):
    candidates=span['candidates']
    return dict(context_ids=span.get('context_ids',span.get('prefix_input_ids')),
        candidates={op:(value['token_ids'] if isinstance(value,dict) else value) for op,value in candidates.items()},
        correct_operator=span.get('correct_operator',span.get('expected_operator')))


def candidate_record(model,row,device):
    context=candidate_context(row);ids=context['context_ids'];candidates=context['candidates']
    if not ids or set(candidates)!=set('+-*/') or any(not c for c in candidates.values()):
        raise ValueError('Four nonempty candidates and one shared token prefix required')
    if any(a!=b and candidates[a]==candidates[b][:len(candidates[a])] for a in candidates for b in candidates):
        raise ValueError('Candidate continuations must be prefix-free')
    records=[];calls=tokens=0;seconds=0.;single=all(len(v)==1 for v in candidates.values())
    shared,timing=_forward(model,ids,device) if single else (None,None)
    for operator in '+-*/':
        candidate=candidates[operator]
        if single:logits=shared;current=timing if operator=='+' else dict(forward_calls=0,input_tokens=0,seconds=0.)
        else:logits,current=_forward(model,ids+candidate[:-1],device)
        logps=[logits[0,len(ids)-1+i].float().log_softmax(-1)[token].item() for i,token in enumerate(candidate)]
        if any(not math.isfinite(x) for x in logps):raise FloatingPointError('Nonfinite candidate probability')
        records.append(dict(operator=operator,token_ids=candidate,token_log_probabilities=logps,
                            log_probability=sum(logps),probability=math.exp(sum(logps))))
        calls+=current['forward_calls'];tokens+=current['input_tokens'];seconds+=current['seconds']
    maximum=max(r['log_probability'] for r in records);normalizer=sum(math.exp(r['log_probability']-maximum) for r in records)
    for r in records:r['normalized_probability']=math.exp(r['log_probability']-maximum)/normalizer
    return dict(context_ids=ids,candidates=records,correct_operator=context['correct_operator'],
        candidate_probability_mass=sum(r['probability'] for r in records),source_row_sha256=digest(row),
        problem_id=row.get('problem_id'),group_id=row.get('group_id'),target_index=row.get('target_index'),
        forward_calls=calls,sequence_equivalents=calls,input_tokens=tokens,seconds=seconds,
        scoring='Raw continuation log probabilities; normalized values conditional on four candidates; no EOS scored')


def _run_rows(model,rows,path,identity,forward_budget,deadline,compute,units):
    path=Path(path);folder=path.with_suffix('.resume');folder.mkdir(parents=True,exist_ok=True)
    descriptor=dict(identity=identity,rows_sha256=digest(rows),diagnostic=identity['diagnostic'],
                    source_sha256=_file_hash(__file__))
    manifest=folder/'manifest.json'
    if manifest.exists():
        if _read(manifest)!=descriptor:raise ValueError('Diagnostic manifest identity changed')
    else:_atomic(manifest,descriptor,immutable=True)
    records=[];status='completed'
    with _caller_state(model):
        model.eval()
        for index,row in enumerate(rows):
            file=folder/f'{index:06d}.json';intent=file.with_suffix('.intent.json')
            binding=dict(descriptor_sha256=digest(descriptor),index=index,row_sha256=digest(row))
            key='diagnostic_'+digest(binding);n=units(row)
            events=[e for e in forward_budget.record()['events'] if e['name']==key]
            if file.exists():
                record=_read(file)
                if (record['identity']!=binding or record.get('request_key')!=key or
                        record.get('forward_calls')!=n or len(events)!=1 or events[0]['reserved']!=n):
                    raise ValueError('Saved forward/ledger identity differs')
                if not intent.exists() or _read(intent)!=dict(identity=binding,request_key=key,sequence_equivalents=n):
                    raise ValueError('Saved forward intent differs')
            else:
                if intent.exists() or events:raise DiagnosticConsistencyError('Ambiguous forward intent: preserve cost and do not replay')
                if time.time()+90>deadline:status='partial';break
                _atomic(intent,dict(identity=binding,request_key=key,sequence_equivalents=n),immutable=True)
                forward_budget.reserve(key,n)
                record=dict(identity=binding,request_key=key,**compute(row))
                if record['forward_calls']!=n:raise ValueError('Actual diagnostic calls differ from reserved sequence equivalents')
                _atomic(file,record,immutable=True)
            records.append(record)
    result=dict(status=status,identity=identity,completed_records=len(records),expected_records=len(rows),records=records,
        forward_calls=sum(r['forward_calls'] for r in records),sequence_equivalents=sum(r['forward_calls'] for r in records),
        input_tokens=sum(r['input_tokens'] for r in records),seconds=sum(r['seconds'] for r in records),
        manifest_sha256=_file_hash(manifest))
    _atomic(path,result);return result


def run_decomposition(model,tokenizer,rows,spans,path,*,identity,forward_budget,deadline,device='cuda'):
    if len(rows)!=len(spans):raise ValueError('Every reference requires a span audit')
    paired=[dict(row=row,span=span) for row,span in zip(rows,spans)]
    identity=dict(identity,diagnostic='unweighted_reference_decomposition')
    return _run_rows(model,paired,path,identity,forward_budget,deadline,
        lambda pair:decomposition_record(model,tokenizer,pair['row'],pair['span'],device),lambda _:1)


def run_candidates(model,contexts,path,*,identity,forward_budget,deadline,device='cuda'):
    identity=dict(identity,diagnostic='first_decision_candidates')
    return _run_rows(model,contexts,path,identity,forward_budget,deadline,
        lambda row:candidate_record(model,row,device),
        lambda row:1 if all(len(x)==1 for x in candidate_context(row)['candidates'].values()) else 4)


def make_alignment_cases(rows,spans,tokenizer):
    result=[]
    if len(rows)!=len(spans):raise ValueError('Alignment case/spans differ')
    for row,span in zip(rows,spans):
        encoded=encode_row(row,tokenizer,1024);validate_mask(encoded,span)
        start=encoded['n_prompt']
        result.append(dict(problem_id=row['problem_id'],source_row_sha256=digest(row),
            prompt_ids=encoded['input_ids'][:start],reference_response_ids=encoded['input_ids'][start:],
            decision_response_positions=[i-start for i in span['decision_token_indices']],span_sha256=digest(span)))
    if len({tuple(r['prompt_ids']) for r in result})!=len(result):
        raise ValueError('Alignment uses one frozen reference per distinct prompt')
    return result


class GreedyAlignmentObserver:
    def __init__(self,model,tokenizer,cases,path,identity):
        self.model=model;self.tokenizer=tokenizer;self.cases=cases;self.path=Path(path);self.identity=identity
        self.folder=self.path.with_suffix('.observations');self.folder.mkdir(parents=True,exist_ok=True)
        self.by_prompt={tuple(c['prompt_ids']):c for c in cases};self.last=None;self.failures=[]
        if not cases or len(self.by_prompt)!=len(cases):raise ValueError('Nonempty distinct alignment prompts required')
        if self.path.exists():
            previous=_read(self.path)
            if previous['identity']!=identity or previous['cases']!=cases:
                raise DiagnosticConsistencyError('Alignment summary identity changed')

    def hook(self,module,args,kwargs,output):
        # This is the actual generate forward, with its actual padding, positions
        # and cache. No alternative precision or uncached replay is substituted.
        self.last=dict(logits=output.logits[:,-1,:].detach(),
            input_shape=list(kwargs['input_ids'].shape),use_cache=kwargs.get('use_cache'),
            cache_present=kwargs.get('past_key_values') is not None,
            position_ids=kwargs['position_ids'].detach().cpu().tolist() if kwargs.get('position_ids') is not None else None,
            cache_position=kwargs['cache_position'].detach().cpu().tolist() if kwargs.get('cache_position') is not None else None)

    def generate(self,*args,**kwargs):
        import torch
        from transformers import LogitsProcessorList
        config=kwargs['generation_config']
        if self.model.training:raise DiagnosticConsistencyError('Greedy alignment requires eval mode')
        if config.do_sample or config.num_beams!=1:raise ValueError('Alignment observer only accepts fixed greedy generation')
        if getattr(config,'renormalize_logits',False):raise ValueError('Observer must be the final effective-logit stage')
        inputs=kwargs['input_ids'];masks=kwargs['attention_mask'];width=inputs.shape[1]
        active={i:self.by_prompt.get(tuple(ids[mask.bool()].tolist())) for i,(ids,mask) in enumerate(zip(inputs,masks))}
        active={i:c for i,c in active.items() if c is not None}
        observations=[];selection_checks=[];deviated=set();self.last=None
        stopper=next((s for s in kwargs.get('stopping_criteria',[]) if hasattr(s,'events')),None)
        if active and stopper is None:raise ValueError('Per-row stopping events required to exclude post-stop padding')
        def observe(input_ids,scores):
            step=input_ids.shape[1]-width
            if active and (self.last is None or self.last['logits'].shape!=scores.shape):
                raise DiagnosticConsistencyError('Actual raw/effective logits were not paired')
            for index,case in active.items():
                if stopper.events[index] is not None:continue
                chosen=int(scores[index].argmax());raw=self.last['logits'][index].float();effective=scores[index].float()
                if not torch.isfinite(raw).all() or torch.isnan(effective).any() or not torch.isfinite(effective).any():
                    raise DiagnosticConsistencyError('Nonfinite effective argmax')
                reference=case['reference_response_ids'];prefix=input_ids[index,width:].tolist()
                different=step>=len(reference) or chosen!=reference[step]
                first= index not in deviated and different
                if first:deviated.add(index)
                selection_checks.append(dict(batch_row=index,step=step,effective_argmax=chosen,
                                             source_row_sha256=case['source_row_sha256']))
                matched_reference_end=step==len(reference)-1 and index not in deviated
                if first or step in case['decision_response_positions'] or matched_reference_end:
                    reference_token=reference[step] if step<len(reference) else None
                    observations.append(dict(problem_id=case['problem_id'],source_row_sha256=case['source_row_sha256'],
                        batch_row=index,step=step,first_literal_deviation=first,semantic_error='unknown',dead_end_prefix='unknown',
                        is_reference_decision_position=step in case['decision_response_positions'],
                        fully_matched_reference_end=matched_reference_end,
                        reference_prefix_matches=prefix==reference[:step],prefix_ids=input_ids[index].tolist(),
                        original_attention_mask=masks[index].tolist(),generated_prefix_ids=prefix,
                        raw_argmax=int(raw.argmax()),effective_argmax=chosen,
                        raw_argmax_tokens=(raw==raw.max()).nonzero().flatten().tolist(),
                        effective_argmax_tokens=(effective==effective.max()).nonzero().flatten().tolist(),
                        raw_logits_fp32_bits=raw.cpu().contiguous().view(torch.int32).tolist(),
                        effective_logits_fp32_bits=effective.cpu().contiguous().view(torch.int32).tolist(),
                        reference_token=reference_token,raw_dtype=str(self.last['logits'].dtype),effective_dtype=str(scores.dtype),
                        raw_effective_exact_equal=bool(torch.equal(raw,effective)),
                        forward={k:v for k,v in self.last.items() if k!='logits'},
                        tie_rule='Exact observed value equality; first token index wins, no tolerance threshold'))
            return scores
        old=kwargs.get('logits_processor') or []
        kwargs['logits_processor']=LogitsProcessorList([*old,observe])
        output=self.original_generate(*args,**kwargs)
        sequences=output.sequences if hasattr(output,'sequences') else output
        errors=[]
        for check in selection_checks:
            actual=int(sequences[check['batch_row'],width+check['step']])
            check['generated_token']=actual
            if actual!=check['effective_argmax']:errors.append(check)
        for record in observations:
            record['generated_token']=int(sequences[record['batch_row'],width+record['step']])
            record['status']='aligned' if record['generated_token']==record['effective_argmax'] else 'genuine_effective_argmax_mismatch'
        binding=dict(identity=self.identity,cases_sha256=digest(self.cases),prompt_batch_ids=inputs.tolist(),
            attention_mask=masks.tolist(),generation_config=config.to_dict(),custom_processors=[type(p).__name__ for p in old])
        path=self.folder/(digest(binding)+'.json')
        result=dict(identity=binding,observations=observations,selection_checks=selection_checks,
            output_ids=sequences.tolist(),genuine_mismatches=errors,status='hard_failure' if errors else 'aligned',
            numeric_encoding='IEEE754 float32 bit pattern int32 list; no rounding',
            extra_forward_calls=0,extra_generations=0,model_training=self.model.training)
        if path.exists():
            if _read(path)!=result:raise DiagnosticConsistencyError('Alignment observation changed on replay')
        else:_atomic(path,result,immutable=True)
        self.failures.extend(errors)
        if errors:raise DiagnosticConsistencyError('Actual generated token differs from same-prefix effective argmax; training must stop')
        return output

    def publish(self):
        files=sorted(self.folder.glob('*.json'));records=[_read(p) for p in files]
        if any(r['identity']['identity']!=self.identity or r['identity']['cases_sha256']!=digest(self.cases) for r in records):
            raise DiagnosticConsistencyError('Saved alignment batch identity changed')
        observed=sorted({o['source_row_sha256'] for r in records for o in r['selection_checks']})
        missing=sorted({c['source_row_sha256'] for c in self.cases}-set(observed))
        result=dict(identity=self.identity,cases=self.cases,cases_sha256=digest(self.cases),
            batches=len(files),batch_files_sha256={p.name:_file_hash(p) for p in files},
            status='hard_failure' if any(r['genuine_mismatches'] for r in records) else 'incomplete' if missing else 'passed',
            genuine_mismatches=sum(len(r['genuine_mismatches']) for r in records),
            observed_cases=observed,missing_cases=missing,
            extra_forward_calls=0,extra_generations=0)
        _atomic(self.path,result);return result


@contextmanager
def observe_greedy_alignment(model,tokenizer,cases,path,*,identity):
    observer=GreedyAlignmentObserver(model,tokenizer,cases,path,identity)
    observer.original_generate=model.generate
    # PEFT delegates generate to its underlying causal LM, bypassing the outer
    # PeftModel.__call__; observe the module that actually emits these logits.
    emitter=model.get_base_model() if hasattr(model,'get_base_model') else model
    hook=emitter.register_forward_hook(observer.hook,with_kwargs=True)
    model.generate=observer.generate
    try:yield observer
    finally:
        model.generate=observer.original_generate;hook.remove();observer.last=None;observer.publish()
