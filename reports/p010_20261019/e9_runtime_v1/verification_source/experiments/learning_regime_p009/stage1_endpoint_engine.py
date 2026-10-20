"""Prepared one-pass NC/S1 vLLM endpoint process, never a dispatch route.

The future parent owns single-use unit intents/raw persistence/deadlines and
exact full input/source checks. This process verifies the whole endpoint before
initialization and accepts only each next original batch once. It never scores.
"""
import os
import traceback

from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
from experiments.learning_regime_p009.p0_engine import software
from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
from experiments.learning_regime_p009.stage0_generation_contract_v2 import ids_checked, MODELS
from experiments.sft_allocation_midpoint.common import digest, verify


def checked_endpoint(setting, rows):
    if setting not in ('NC', 'S1'):
        raise ValueError('Only NC/S1; S2 failed its original cap gate')
    count, cap = (1319, 512) if setting == 'NC' else (500, 1024)
    if not isinstance(rows, list) or len(rows) != count:
        raise ValueError('Complete endpoint required')
    seen = set()
    for row in rows:
        if (not isinstance(row['problem_id'], str) or not row['problem_id']
                or row['problem_id'] in seen
                or row['candidate_id'] != setting+'::'+row['problem_id']
                or row['source_row_sha256'] != digest(dict(problem_id=row['problem_id'],
                                                          input_ids=row['input_ids']))):
            raise ValueError('Frozen endpoint identity/source differs')
        ids_checked(row['input_ids'], 151936, 2048-cap)
        seen.add(row['problem_id'])
    return dict(n=1, temperature=0, top_p=1, top_k=-1, repetition_penalty=1,
        max_tokens=cap, seed=17, stop=None, stop_token_ids=[151643], ignore_eos=False,
        detokenize=True, skip_special_tokens=False, include_stop_str_in_output=True)


class EndpointCursor:
    """Reserve only the next original batch; ambiguous sends are never retried."""
    def __init__(self, rows):
        self.rows = rows; self.cursor = 0

    def reserve(self, offset):
        if type(offset) is not int or offset != self.cursor or self.cursor >= len(self.rows):
            raise ValueError('Repeated/foreign endpoint batch; no retry')
        part = self.rows[offset:offset+256]
        self.cursor += len(part)
        return part


def child(connection, setting, paths, rows, merged_manifest):
    try:
        if os.environ.get('VLLM_USE_V1') != '1':
            raise ValueError('Original common V1 engine required')
        params = checked_endpoint(setting, rows); cursor = EndpointCursor(rows)
        info = software(); verify(paths['model'], merged_manifest)
        from vllm import LLM, SamplingParams
        sampling = SamplingParams(**params)
        model = LLM(model=paths['model'], tokenizer=paths['tokenizer'], **engine_kwargs())
        config = model.llm_engine.vllm_config
        if (config.model_config.hf_config.vocab_size != 151936
                or config.model_config.hf_config.architectures != ['Qwen2ForCausalLM']
                or config.model_config.hf_config.eos_token_id != 151643):
            raise ValueError('Exact merged Qwen architecture/EOS differs')
        info.update(model=MODELS['qwen'], requested_engine=engine_kwargs(),
            actual_engine=actual_engine(config), endpoint_rows_sha256=digest(rows),
            sampling=params, scoring_on_gpu=False)
        connection.send(('ready', info))
        while True:
            command, payload = connection.recv()
            if command == 'close':
                if cursor.cursor != len(rows):
                    raise ValueError('Endpoint closed early; incomplete work must stay failed')
                return
            if command != 'generate':
                raise ValueError('Unknown child command')
            part = cursor.reserve(payload)
            outputs = model.generate([dict(prompt_token_ids=r['input_ids']) for r in part],
                sampling, use_tqdm=False)
            # Retain malformed returned shapes verbatim for the parent to save
            # before transport validation. No answer decode or scoring here.
            connection.send(('outputs', returned_records(part, [params for _ in part], outputs)))
    except BaseException:
        connection.send(('error', traceback.format_exc()))
        raise
    finally:
        connection.close()
