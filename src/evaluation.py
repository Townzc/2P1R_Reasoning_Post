"""Development-only generation scoring; all failures stay in the denominator."""
import re
from .countdown_smoke import safe_parse, canonical, verify_expression
from .metrics import macro_pass_at_k


def score_token_caps(tokens, tokenizer, row, caps, generation_limit):
    """Score prefixes of one greedy continuation, preserving EOS/truncation flags."""
    result = {}
    for cap in caps:
        if not 0 < cap <= generation_limit:
            raise ValueError('Diagnostic cap outside generated sequence limit')
        capped = tokens[:cap]
        eos = tokenizer.eos_token_id in capped
        if eos:
            capped = capped[:capped.index(tokenizer.eos_token_id)+1]
        result[str(cap)] = {'problem_id': row['problem_id'], 'eos': eos,
                            'output_tokens': len(capped), 'truncated': not eos and len(capped) == cap,
                            **score_text(tokenizer.decode(capped, skip_special_tokens=True), row['numbers'], row['target'])}
    return result


def score_text(text, numbers, target):
    matches = list(re.finditer(r'(?m)^\s*Answer:\s*([^\n]+)', text))
    result = {'parsed': False, 'correct': False, 'expression': None, 'structure_id': None}
    if len(matches) != 1:
        return result
    candidate = matches[0].group(1).strip()
    try:
        tree = safe_parse(candidate)
    except (ValueError, SyntaxError, RecursionError):
        return result
    result.update(parsed=True, expression=candidate,
                  correct=verify_expression(candidate, numbers, target))
    if result['correct']:
        result['structure_id'] = canonical(tree, structure_only=True)
    return result


def summarize(predictions, ks=()):
    from collections import defaultdict
    import math
    if not predictions:
        raise ValueError('Empty predictions')
    groups = defaultdict(list)
    for p in predictions:
        groups[p['problem_id']].append(p)
    counts = [(len(items), sum(p['correct'] for p in items)) for items in groups.values()]
    structure_counts, entropies = [], []
    from collections import Counter
    for items in groups.values():
        structures = Counter(p['structure_id'] for p in items if p['correct'])
        structure_counts.append(len(structures))
        total = sum(structures.values())
        entropies.append(-sum((n/total)*math.log(n/total) for n in structures.values()) if total else None)
    return {'problems': len(groups), 'generations': len(predictions),
            'accuracy_macro': sum(c/n for n, c in counts)/len(counts),
            'parsing_failure_rate': sum(not p['parsed'] for p in predictions)/len(predictions),
            'eos_rate': sum(p['eos'] for p in predictions)/len(predictions),
            'truncation_rate': sum(p['truncated'] for p in predictions)/len(predictions),
            'mean_output_tokens': sum(p['output_tokens'] for p in predictions)/len(predictions),
            'pass_at_k': {str(k): macro_pass_at_k(counts, k) for k in ks},
            'mean_valid_structure_count': sum(structure_counts)/len(groups),
            'mean_valid_structure_entropy_conditional_on_success':
                sum(x for x in entropies if x is not None)/sum(x is not None for x in entropies)
                if any(x is not None for x in entropies) else None}
