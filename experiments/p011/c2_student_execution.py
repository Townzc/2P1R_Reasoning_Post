"""C2 full training-child/exit/native-five-endpoint body; shared outer CR pending."""
from pathlib import Path
import math
import multiprocessing
import time

from experiments.p010.common import dump, read, digest
from experiments.p010.student_contract import evaluation_jobs, sampling
from experiments.p011.c2_numeric import forecast
from experiments.p011.c2_student_process import child
from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records


def endpoint_rows(rows):
    fields = {'candidate_id', 'problem_id', 'input_ids', 'source_row_sha256'}
    if (not isinstance(rows, list) or len(rows) != 500
            or len({r['candidate_id'] for r in rows}) != 500
            or len({r['problem_id'] for r in rows}) != 500):
        raise ValueError('Original full500 endpoint list required')
    for row in rows:
        ids = row['input_ids']
        if (set(row) != fields or not ids or len(ids)+1024 > 2048
                or any(type(x) is not int or not 0 <= x < 151936 for x in ids)
                or not isinstance(row['source_row_sha256'], str)
                or len(row['source_row_sha256']) != 64):
            raise ValueError('Exact original gold-free endpoint fields/tokens required')
    return rows


def require_exited(proc, message):
    kind, value, times = message
    if (kind != 'complete' or proc.is_alive() or proc.exitcode != 0
            or len(times) != 64 or any(type(x) not in (int, float)
                or not math.isfinite(x) or x <= 0 for x in times)):
        raise RuntimeError('Complete original training child must exit0 and join before vLLM')
    return value, times


def load_engine(model):
    from vllm import LLM, SamplingParams
    from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
    llm = LLM(model=str(model), tokenizer=str(model), **engine_kwargs())
    return llm, SamplingParams, actual_engine(llm.llm_engine.vllm_config)


def evaluate(rows, out, key, claim, policy, training_times, store, commit,
             check, llm, constructor, clock=time.time):
    rows = endpoint_rows(rows)
    out = Path(out)
    completed, cycles = 0, []
    for job in evaluation_jobs():
        for first in (0, 256):
            tick = clock()
            check()
            if store.get(key+'/claim') != claim:
                raise ValueError('Original C2 claim differs')
            value = forecast(policy, 0, 10-completed, training_times, cycles, tick)
            unit = job[0]+f'/{first:04d}'
            part = rows[first:first+256]
            params = [sampling(job) for _ in part]
            intent = dict(rows=part, sampling=params, evaluation=job[0])
            if not store.put(key+'/eval/'+unit, intent, skip_if_exists=True):
                raise ValueError('Original C2 endpoint already attempted; no replay')
            dump(out/'eval_forecasts'/(unit+'.json'), value)
            dump(out/'eval_intents'/(unit+'.json'), intent)
            commit()
            output = llm.generate([{'prompt_token_ids':r['input_ids']} for r in part],
                [constructor(**p) for p in params], use_tqdm=False)
            raw = returned_records(part, params, output)
            dump(out/'raw'/(unit+'.json'), raw)
            commit()
            if (len(raw) != len(part) or any(x['output_count'] != 1
                    or x['candidate_id'] != r['candidate_id']
                    or x['prompt_token_ids'] != r['input_ids'] for r, x in zip(part, raw))):
                raise ValueError('Incomplete endpoint retained, no zero-filling or retry')
            check()
            ack = dict(count=len(part), raw_sha256=digest(raw), evaluation=job[0])
            dump(out/'eval_acks'/(unit+'.json'), ack)
            commit()
            if not store.put(key+'/eval_done/'+unit, ack, skip_if_exists=True):
                raise ValueError('Duplicate original endpoint acknowledgment')
            elapsed = clock()-tick
            if elapsed <= 0:
                raise ValueError('Positive three-commit/remote-ack endpoint cycle required')
            cycles.append(elapsed)
            completed += 1
    return cycles


def worker_body(job, inputs, out, identity, key, claim, policy, stop, store, volume,
                context_factory=multiprocessing.get_context, loader=load_engine):
    """Outer entry is responsible for exact source/input/review/budget/claim.

    Child exit and all local cleanup use the original worker deadline. No model
    reload, merge repair, continuation or intermediate endpoint is provided.
    """
    out, inputs = Path(out), Path(inputs)
    rows = endpoint_rows(read(inputs/'MATH_ENDPOINT.json'))
    if (job['run_id'] not in ('C2a','C2b') or identity['run_id'] != job['run_id']
            or key != 'c2/student/'+job['run_id'] or policy['kind'] != 'student'
            or store.get(key+'/claim') != claim):
        raise ValueError('Exact outer C2 student identity/claim required')

    def check():
        if time.time() >= stop-30 or store.get(key+'/claim') != claim:
            raise TimeoutError('Original worker deadline/claim no longer available')

    check()
    ctx = context_factory('spawn')
    parent, remote = ctx.Pipe()
    proc = ctx.Process(target=child, args=(remote, str(inputs), str(out), job['model'],
        identity, claim, policy, stop))
    try:
        proc.start()
        remote.close()
        if not parent.poll(max(0, stop-time.time()-30)):
            raise TimeoutError('Original training child window expired')
        message = parent.recv()
        proc.join(timeout=max(0, min(30, stop-time.time()-30)))
        trained, times = require_exited(proc, message)
        volume.reload()
        dump(out/'TRAINING_EXIT.json', dict(pid=proc.pid, exitcode=proc.exitcode,
             joined_before_vllm=True))
        volume.commit()
        check()
        forecast(policy, 0, 10, times, [], time.time())
        llm, constructor, engine = loader(out/'merged')
        dump(out/'ENGINE.json', engine)
        volume.commit()
        cycles = evaluate(rows, out, key, claim, policy, times, store, volume.commit,
                          check, llm, constructor)
        check()
        result = dict(run=job['run_id'], training=trained, raw_endpoint_count=2500,
            unique_questions=500, evaluations=[x[0] for x in evaluation_jobs()],
            eval_batch_seconds=cycles, endpoint_complete_cycles_include_three_commits_and_ack=True,
            symbolic_scoring_performed=False, final_summary_pack_outside_cycle=True)
        dump(out/'RESULT.json', result)
        volume.commit()
        check()
        return result
    finally:
        parent.close()
        remote.close()
        if proc.pid is not None and proc.is_alive():
            proc.kill()
            proc.join(timeout=5)
