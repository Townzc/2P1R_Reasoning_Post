"""Independent checks of C020 saved prefixes and dose; does not call its stopper."""
import argparse
from collections import Counter
import json
from pathlib import Path

from analyses.gsm8k_answer_audit import BOUNDARY, extract, canonical
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import read_jsonl, sha256_file


def verify(tokenizer, folder, output):
    report = json.loads((folder / 'summary.json').read_text())
    records = read_jsonl(folder / 'records.jsonl')
    paths = {'e013_base16': 'runs/gsm8k_overfit_e013_r1/base_dev.jsonl',
             'e013_tuned16': 'runs/gsm8k_overfit_e013_r1/final_dev.jsonl',
             'e016_base64': 'runs/gsm8k_capability_e016_r1/base.jsonl',
             'e016_e01564': 'runs/gsm8k_capability_e016_r1/e015.jsonl'}
    assert len(records) == 160
    assert len({(r['endpoint'], r['problem_id']) for r in records}) == 160
    boundaries = 0
    for name, path in paths.items():
        assert sha256_file(path) == report['input_hashes'][path]
        raw = read_jsonl(path)
        group = [r for r in records if r['endpoint'] == name]
        assert [r['problem_id'] for r in group] == [r['problem_id'] for r in raw]
        correct, retained, reasons = 0, [], Counter()
        for saved, result in zip(raw, group):
            assert saved['score'] == result['original_strict_score']
            event = result['proposed_stop']; count = event['retained_tokens']
            ids = saved['generated_ids']; assert 0 < count <= len(ids)
            prefix_ids = ids[:count]; reason = event['stop_reason']; reasons[reason] += 1
            if reason == 'new_problem_boundary':
                boundaries += 1
                text = tokenizer.decode(prefix_ids, skip_special_tokens=True)
                before = tokenizer.decode(prefix_ids[:-1], skip_special_tokens=True)
                boundary = BOUNDARY.search(text)
                assert boundary and not BOUNDARY.search(before)
                assert boundary.start() == event['boundary_offset']
                assert event['answer_segment'] == text[:boundary.start()]
                assert tokenizer.eos_token_id not in prefix_ids
                assert not event['actual_eos_at_stop']
            elif reason == 'native_eos':
                assert prefix_ids[-1] == tokenizer.eos_token_id
                assert tokenizer.eos_token_id not in prefix_ids[:-1]
                assert event['actual_eos_at_stop']
                assert event['answer_segment'] == tokenizer.decode(prefix_ids[:-1], skip_special_tokens=True)
                assert not BOUNDARY.search(event['answer_segment'])
            else:
                assert reason == 'length_cap' and count == len(ids) == 768
                assert tokenizer.eos_token_id not in prefix_ids
                assert not BOUNDARY.search(saved['text'])
                assert not event['actual_eos_at_stop']
                assert event['answer_segment'] == saved['text']
            parsed = extract(event['answer_segment'])
            expected = (reason in ('native_eos', 'new_problem_boundary')
                        and parsed['status'] == 'parsed' and parsed['value'] == canonical(saved['answer']))
            assert result['saved_prefix_candidate']['task_answer_correct'] == expected
            correct += expected; retained.append(count)
        summary = report['endpoints'][name]
        assert summary['saved_prefix_task_answer_correct'] == correct
        assert summary['candidate_stop_reasons'] == dict(reasons)
        assert summary['retained_prefix_tokens_including_stop_trigger'] == sum(retained)
        assert summary['original_generated_tokens'] == sum(r['generated_tokens'] for r in raw)
        assert summary['prefix_batch_maximum_lengths_sum'] == sum(max(retained[i:i+8]) for i in range(0, len(retained), 8))

    dose = json.loads((folder / 'proposed_training_dose.json').read_text())
    selected_path = Path('reports/real_math_c017_scale_proposal_r1/repeat_rows.jsonl')
    selected = read_jsonl(selected_path)
    assert sha256_file(selected_path) == dose['selected_rows_sha256']
    batches = dose['updates']; assert len(batches) == 64
    exposure = Counter(i for b in batches for i in b['row_indices'])
    assert exposure == Counter({i: 2 for i in range(253)})
    for batch in batches:
        assert batch['supervised_tokens'] == sum(selected[i]['n_supervised'] for i in batch['row_indices'])
    assert sum(b['supervised_tokens'] for b in batches) == dose['supervised_tokens'] == 77192
    assert 2 * sum(r['n_processed'] for r in selected) == dose['nonpadding_processed_tokens'] == 109434
    adapter = dose['proposed_lora_shape_estimate']
    assert adapter['trainable_adapter_parameters'] == 28 * 16 * (2 * 3072 + 2 * 1792 + 3 * 10496) == 18464768
    assert adapter['float32_tensor_bytes'] == 4 * 18464768
    evidence = {'status': 'passed_independent_prefix_and_dose_checks',
                'raw_streams': 160, 'minimal_boundary_trigger_prefixes_checked': boundaries,
                'dose_presentations_checked': sum(exposure.values()), 'new_model_calls': 0,
                'first_stop_implementation_called': False, 'runtime_stopping_verified': False,
                'original_scores_modified': False, 'reasoning_proofs_verified': False,
                'verifier_sha256': sha256_file(__file__),
                'artifact_sha256': {name: sha256_file(folder / name) for name in
                                   ('summary.json', 'records.jsonl', 'proposed_training_dose.json')}}
    with output.open('x') as f:
        f.write(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    return evidence


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer-dir', required=True, type=Path)
    p.add_argument('--folder', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    tokenizer, _ = verified_tokenizer(args.tokenizer_dir)
    print(json.dumps(verify(tokenizer, args.folder, args.out), indent=2))
