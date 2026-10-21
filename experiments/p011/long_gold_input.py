"""Proposed lossless JSON numeric-gold adapter; no answer correction or scoring."""
import math
from collections import Counter
from experiments.p011.long_evaluation import BENCHMARK_COUNTS
from experiments.sft_allocation_midpoint.common import digest


def benchmark_projection(rows):
    if Counter(r['benchmark'] for r in rows)!=Counter(BENCHMARK_COUNTS):
        raise ValueError('All original600 benchmark rows required')
    seen=set();projected=[];proof=[]
    # Validate all scalar types and identities before any native tokenization.
    for r in rows:
        b,i=r['benchmark'],r['source_row'];value=r['answer']
        if type(i) is not int or not 0<=i<BENCHMARK_COUNTS[b] or (b,i) in seen:
            raise ValueError('Original unique benchmark identity required')
        seen.add((b,i))
        if isinstance(value,str):
            if not value.strip():raise ValueError('Empty original gold')
            text=value
        elif type(value) is int:text=str(value)
        elif type(value) is float and math.isfinite(value) and value.is_integer():text=str(int(value))
        else:raise ValueError('No coercion for bool, nonfinite, nonintegral or structured gold')
        projected.append({**r,'answer':text})
        proof.append({'benchmark':b,'source_row':i,'original_row_sha256':digest(r),
            'original_answer_type':type(value).__name__,'original_answer':value,
            'canonical_gold':text,'projected_row_sha256':digest(projected[-1]),
            'semantic_answer_change':False})
    return projected,proof
