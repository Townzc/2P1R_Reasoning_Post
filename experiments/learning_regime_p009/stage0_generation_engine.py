"""One model lifetime for a finite Stage0 slot; no retries, scoring or dispatch."""
import os
import traceback

from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine
from experiments.learning_regime_p009.p0_engine import software
from experiments.learning_regime_p009.stage0_generation_contract import MODELS, SLOTS, sampling


def returned_records(rows, params, outputs):
    """Retain all returned candidates even when the backend shape is invalid."""
    raw = []
    for i, generated in enumerate(outputs):
        row = rows[i] if i < len(rows) else {}
        answers = [dict(token_ids=list(a.token_ids), backend_text=a.text,
            finish_reason=a.finish_reason, stop_reason=a.stop_reason) for a in generated.outputs]
        value = dict(candidate_id=row.get('candidate_id'), problem_id=row.get('problem_id'),
            source_row_sha256=row.get('source_row_sha256'),
            sampling=params[i] if i < len(params) else None,
            prompt_token_ids=list(generated.prompt_token_ids), output_count=len(answers))
        if len(answers) == 1:
            value.update(answers[0])
        else:
            value['invalid_shape_original_answers'] = answers
        raw.append(value)
    return raw


def child(connection, run_id, paths):
    try:
        if os.environ.get('VLLM_USE_V1') != '1':
            raise ValueError('The common reviewed V1 engine is mandatory')
        slot = SLOTS[run_id]; expected = MODELS[slot['model']]
        info = software()
        from vllm import LLM, SamplingParams
        model = LLM(model=paths['model'], tokenizer=paths['tokenizer'], **engine_kwargs())
        config = model.llm_engine.vllm_config
        if (config.model_config.hf_config.vocab_size != expected['vocab_size']
                or config.model_config.hf_config.architectures != [expected['architecture']]):
            raise ValueError('Pinned model architecture/vocabulary differs')
        native = config.model_config.hf_config.eos_token_id
        native = native if isinstance(native, list) else [native]
        if not native or not set(native) <= set(expected['eos_token_ids']):
            raise ValueError('Model has an unregistered automatic EOS token')
        info['requested_engine'] = engine_kwargs()
        info['actual_engine'] = actual_engine(config)
        info['model'] = expected
        connection.send(('ready', info))
        while True:
            command, payload = connection.recv()
            if command == 'close':
                return
            if command != 'generate':
                raise ValueError('Unknown child command')
            name, rows = payload['dataset'], payload['rows']
            if name not in slot['datasets'] or not 1 <= len(rows) <= 256:
                raise ValueError('Only this slot\'s fixed dataset batches are permitted')
            params = [sampling(name, row) for row in rows]
            outputs = model.generate([dict(prompt_token_ids=r['input_ids']) for r in rows],
                [SamplingParams(**p) for p in params], use_tqdm=False)
            connection.send(('outputs', returned_records(rows, params, outputs)))
    except BaseException:
        connection.send(('error', traceback.format_exc()))
        raise
    finally:
        connection.close()
