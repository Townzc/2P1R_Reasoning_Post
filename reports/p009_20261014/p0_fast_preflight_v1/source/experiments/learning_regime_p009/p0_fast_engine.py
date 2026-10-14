"""Fresh high-throughput engine; reuses only the frozen software/merge routines."""
import os
import traceback
from experiments.learning_regime_p009.p0_engine import software, merge_reference
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine


def child(connection, mode, paths):
    try:
        info = software()
        if mode == 'merge':
            merge_reference(**paths); connection.send(('merged', info)); return
        if mode != 'evaluate' or os.environ.get('VLLM_USE_V1') != '1':
            raise ValueError('Exactly the reviewed V1 engine required')
        from vllm import LLM, SamplingParams
        model = LLM(model=paths['model'], tokenizer=paths['tokenizer'], **engine_kwargs())
        info['requested_engine'] = engine_kwargs()
        info['actual_engine'] = actual_engine(model.llm_engine.vllm_config)
        sampling = SamplingParams(n=1, temperature=0, top_p=1, top_k=-1,
            repetition_penalty=1, max_tokens=512, seed=17, stop=None,
            stop_token_ids=[151643], ignore_eos=False, detokenize=True,
            skip_special_tokens=False, include_stop_str_in_output=True)
        connection.send(('ready', info))
        while True:
            command, rows = connection.recv()
            if command == 'close':
                return
            if command != 'generate' or not 1 <= len(rows) <= 256:
                raise ValueError('Unknown command or unfrozen batch size')
            outputs = model.generate([dict(prompt_token_ids=r['input_ids']) for r in rows],
                                     sampling, use_tqdm=False)
            if len(outputs) != len(rows):
                raise ValueError('Missing vLLM output')
            raw = []
            for row, generated in zip(rows, outputs):
                if len(generated.outputs) != 1:
                    raise ValueError('Only one greedy completion allowed')
                answer = generated.outputs[0]
                raw.append(dict(problem_id=row['problem_id'],
                    prompt_token_ids=list(generated.prompt_token_ids), token_ids=list(answer.token_ids),
                    backend_text=answer.text, finish_reason=answer.finish_reason,
                    stop_reason=answer.stop_reason))
            connection.send(('outputs', raw))
    except BaseException:
        connection.send(('error', traceback.format_exc()))
        raise
    finally:
        connection.close()
