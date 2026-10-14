"""Reporting arithmetic on frozen, previously audited P008 records.

No tokenizer, scorer, procurement replay, state loader, network or model call.
Prices are hypothetical token units, distinct from platform metering dollars.
"""
from fractions import Fraction


def fraction(value):
    return Fraction(value['numerator'], value['denominator'])


def encoded(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


def wallet_row(summary, events, candidates):
    name = summary['wallet']
    draw, budget, price, policy = name.split('_')
    ids = summary['consumed_candidate_ids']
    assert len(ids) == len(set(ids)) == summary['attempted_candidates']
    rows = [candidates[k] for k in ids]
    assert all(r['candidate_id'] == k for r, k in zip(rows, ids))
    assert [r['candidate_id'] for r in rows if r['usable']] == summary['accepted_candidate_ids']
    event_ids = [k for e in events for k in e['done']['candidate_ids']]
    assert event_ids == ids
    purchased_list = [k for e in events for k in e['intent']['action']['new_problem_ids']]
    purchased = set(purchased_list)
    assert len(purchased_list) == len(purchased) == summary['acquired_problems']
    assert {r['problem_id'] for r in rows} == purchased
    covered = {r['problem_id'] for r in rows if r['usable']}
    assert len(covered) == summary['covered_parents']
    assert len(purchased - covered) == summary['zero_usable_parents']
    prompt = sum(r['prompt_tokens'] for r in rows)
    output = sum(r['completion_tokens'] for r in rows)
    fee = int(price[1:]) * Fraction(191151, 512) * len(purchased)
    charge = fraction(summary['charge'])
    assert charge == prompt + output + fee
    assert charge == sum((fraction(e['done']['charged_units']) for e in events), Fraction())
    cap = fraction(summary['cap'])
    assert 0 <= charge <= cap and (cap - charge) / cap == fraction(summary['unused_fraction'])
    usable = sum(r['usable'] for r in rows)
    assert usable == summary['usable_answers'] == len(summary['accepted_candidate_ids'])
    rejected_valid_duplicates = sum(r['clean_correct'] and r['usable_duplicate_of'] is not None for r in rows)
    other_unusable = sum(not r['clean_correct'] for r in rows)
    assert usable + rejected_valid_duplicates + other_unusable == len(rows)
    assert summary['unknown'] == 0 and not summary['unresolved_batch']
    return {
        'wallet': name, 'draw': int(draw[1:]), 'budget_multiple': int(budget[1:]),
        'problem_price_multiple_m': int(price[1:]), 'policy': policy,
        'cap_units': encoded(cap), 'charged_units': encoded(charge),
        'unused_units': encoded(cap - charge), 'unused_percent': 100 * float((cap - charge) / cap),
        'problem_fee_units': encoded(fee), 'charged_prompt_tokens': prompt,
        'charged_returned_tokens_including_eos': output,
        'charged_attempts': len(rows), 'accepted_usable_answers': usable,
        'unusable_attempts': len(rows) - usable,
        'of_which_rejected_valid_duplicates': rejected_valid_duplicates,
        'other_frozen_primary_unusable': other_unusable,
        'exact_text_duplicate_attempts_including_possible_invalid': sum(r['duplicate_of'] is not None for r in rows),
        'length_capped_attempts': sum(r['truncated'] for r in rows),
        'technical_unknown': summary['unknown'], 'purchased_problems': len(purchased),
        'usable_covered_problems': len(covered), 'zero_usable_problems': len(purchased - covered),
        'pool_exhausted': summary['pool_exhausted'], 'stop_reason': summary['stop_reason'],
        'purchased_problem_ids': sorted(purchased), 'usable_problem_ids': sorted(covered),
        'charge_scope': 'Every virtual-policy consumed attempt, including shared-cache, failed-primary and duplicate outputs; hypothetical units, not dollars',
    }


def overlap_row(left, right, field):
    assert left['draw'] == 1 and right['draw'] == 2
    assert left['budget_multiple'] == right['budget_multiple'] == 8
    assert left['policy'] == right['policy']
    assert left['problem_price_multiple_m'] == right['problem_price_multiple_m']
    a, b = set(left[field]), set(right[field])
    union, shared = a | b, a & b
    return {'policy': left['policy'], 'problem_price_multiple_m': left['problem_price_multiple_m'],
            'budget_multiple': 8, 'set_definition': field, 'draw1_count': len(a),
            'draw2_count': len(b), 'intersection_count': len(shared), 'union_count': len(union),
            'jaccard': len(shared) / len(union) if union else None,
            'shared_problem_ids': sorted(shared),
            'interpretation': 'Problem-ID overlap only; independently seeded teacher answers are not shared between draws'}


def render_appendix(data, billing):
    units = lambda x: f"{float(fraction(x)):.5f}".rstrip('0').rstrip('.')
    lines = ['## Acquisition, overlap and costs', '',
             'These are aggregates of frozen, independently audited scored records and payment events; no raw answers were rescored. '
             'All 16 wallets used the same 6,973 eligible training problems. All token charges below follow the hypothetical tariff; they are not API or platform dollars.', '',
             '| Wallet | Cap | Charged | Unused | Unused % | Problem fee | Prompt tokens | Returned tokens |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in data['wallets']:
        lines.append(f"| {r['wallet']} | {units(r['cap_units'])} | {units(r['charged_units'])} | {units(r['unused_units'])} | {r['unused_percent']:.3f} | {units(r['problem_fee_units'])} | {r['charged_prompt_tokens']} | {r['charged_returned_tokens_including_eos']} |")
    lines += ['', '| Wallet | Paid attempts | Usable answers | Unusable | Valid duplicates within unusable | Other primary unusable | Text duplicates, overlapping | Length caps | Purchased / usable / zero-usable problems | Pool exhausted | Stop reason |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|']
    for r in data['wallets']:
        lines.append(f"| {r['wallet']} | {r['charged_attempts']} | {r['accepted_usable_answers']} | {r['unusable_attempts']} | {r['of_which_rejected_valid_duplicates']} | {r['other_frozen_primary_unusable']} | {r['exact_text_duplicate_attempts_including_possible_invalid']} | {r['length_capped_attempts']} | {r['purchased_problems']} / {r['usable_covered_problems']} / {r['zero_usable_problems']} | {r['pool_exhausted']} | {r['stop_reason']} |")
    lines += ['', 'Unusable = rejected valid duplicates + other failures under the frozen primary rule. Length-cap/text-duplicate columns can overlap those categories. '
              'All virtual attempts are charged in full even when a candidate came from the shared cache. All wallets have zero technical unknowns. '
              'A budget stop that cannot reserve the next complete16-action batch is distinct from exhaustion of the eligible problem pool.', '',
              '| High-B policy | Problem price | Set | D1 | D2 | Intersection | Union | Jaccard |',
              '|---|---:|---|---:|---:|---:|---:|---:|']
    for r in data['high_budget_overlap']:
        lines.append(f"| {r['policy']} | {r['problem_price_multiple_m']}m | {r['set_definition']} | {r['draw1_count']} | {r['draw2_count']} | {r['intersection_count']} | {r['union_count']} | {r['jaccard']:.4f} |")
    lines += ['', 'Both purchased-problem and usable-problem overlap are shown. Repeated problem IDs across draws do not mean the teacher answers or training paths are identical.', '',
              '| Physical teacher draw | Unique generated outputs | Prompt tokens | Returned tokens, including EOS | Parent / child outputs |',
              '|---|---:|---:|---:|---|']
    for r in data['physical_draws']:
        lines.append(f"| D{r['draw']} | {r['physical_outputs']} | {r['prompt_tokens']} | {r['returned_tokens']} | {r.get('parent_outputs', 'n/a')} / {r.get('child_outputs', 'n/a')} |")
    lines += ['', 'Physical teacher work is shared by virtual policies; summing virtual-wallet token charges would double-count some physical generation. '
              'The failed D2 parent remains failed and its3,992 outputs are retained once, followed by3,424 new child outputs. '
              'Two original T1 calls failed before any update or endpoint output; two independently authorized replacements completed. All failure/setup/storage costs remain included in platform records.', '',
              f"Platform snapshot read {billing['actual_read_receipt']['read_utc']}: workspace delayed usage **${billing['workspace_delayed_meter_usd']}**; "
              f"P008-labelled rows **${billing['P008_description_prefix_sum_usd']}**; billed charges field **${billing['billed_usd']}**. "
              'A zero billed-charge field does not mean no usage cost. These are delayed metering fields, not a final invoice, final P008 total or balance. '
              'Currently running or recently completed work may not yet be included.', '',
              f"The authorized P008 reservation is **${billing['stage_authorized_reservation_usd']}**, distinct from actual usage. "
              f"The residual (which may include lagging/unlabelled P008) plus the full reservation is ${billing['residual_plus_entire_stage_usd']}; "
              f"the project spending ceiling is ${billing['project_ceiling_usd']} with ${billing['protected_usd']} protected. "
              'The freeze-time page must use a separately dated latest available billing snapshot; invoices or final charges may remain pending.', '',
              'The D1/price0 B8/T1 depth-minus-breadth gap shown in earlier T1 context is a **conditional, unregistered comparison**, not one of the18 registered main contrasts. '
              'The four retained within-policy bridge conditional effects are reported separately. Unified parser-v2 sensitivity remains pending; no selective example corrections are made.', '']
    return '\n'.join(lines)
