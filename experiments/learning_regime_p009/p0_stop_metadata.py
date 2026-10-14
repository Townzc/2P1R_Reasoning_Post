"""Validate native token streams without treating vLLM's cap/EOS tie as corruption.

Code candidate only. No old runtime imports this module. In vLLM 0.11 V1,
check_stop checks the output-length cap before native EOS. At exactly token512,
an authentic terminal EOS can therefore have finish_reason='length'. Preserve
both original fields; the frozen CPU first_stop remains the logical-stop oracle.
"""
from experiments.learning_regime_p009.p0_contract import raw_checked as original_raw_checked


def raw_checked(rows, output):
    """Accept only the one documented metadata tie in addition to old valid rows.

    No token append, deletion, decoding, score, field normalization or mutation.
    A short stream, post-EOS token, duplicate EOS, different identity/prompt,
    noninteger/out-of-vocabulary ID or any other inconsistent stop still fails.
    """
    if len(rows) != len(output):
        raise ValueError('Missing generation')
    for row, raw in zip(rows, output):
        ids = raw['token_ids']
        tie = (len(ids) == 512 and ids[-1] == 151643 and ids.count(151643) == 1
               and raw['finish_reason'] == 'length' and raw['stop_reason'] is None)
        if not tie:
            original_raw_checked([row], [raw])
            continue
        if (raw['problem_id'] != row['problem_id']
                or raw['prompt_token_ids'] != row['input_ids']
                or any(type(x) is not int or not 0 <= x < 151936 for x in ids)):
            raise ValueError('Raw identity/token contract differs')
    return output
