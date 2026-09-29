"""Complete the frozen Base dev and masks before any formal optimizer update."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import gc
import hashlib
import json
from pathlib import Path
import time
import unicodedata

import torch
from transformers import AutoTokenizer

from .data import load_inputs
from .losses import select_qdw_tokens, validate_response_alignment
from .preflight import (PHASE, MODEL_REVISION, drop_model, gold_forward, json_hash,
                        load_base, sha, write_json)
from .runtime_common import PhysicalLedger, ensure_record, generate_rows, read, require_time
from .source_guard import verify_inventory
from .tokenization import encode_prompt, validate_tokenizer

RELEASE_SHA = 'f7c67a1c523c3ec5dfbd1ae63506a9ce91dd03683643dcf3b7a72c70b16fa370'
INPUT_SHA = '06660ef5f0a12dde2118b3f7d436a7c0f3f34f492632ec13e438523b33d50c8c'
PREFLIGHT_COMMIT = '0f66e8ceb9138be52d3d51169944486d75c1ea94'
PREFLIGHT_INVENTORY = 'f65e3115fc241e8cb773780d42f32ce8b3f3bd5903ca440426f03a0fe967dc33'


def prepare_identity(base, release, inputs):
    if sha(inputs) != INPUT_SHA or sha(Path(release)/'manifest.json') != RELEASE_SHA:
        raise ValueError('Frozen release/preflight input SHA differs')
    frozen = read(inputs)
    for name, expected in frozen['model_files_sha256'].items():
        if sha(Path(base)/name) != expected:
            raise ValueError('Public base/tokenizer differs: ' + name)
    if frozen['model_revision'] != MODEL_REVISION:
        raise ValueError('Public base revision differs')
    tokenizer = AutoTokenizer.from_pretrained(base, local_files_only=True)
    identity = dict(model_revision=MODEL_REVISION,
        model_sha256=frozen['model_files_sha256']['model.safetensors'],
        inputs_sha256=INPUT_SHA, release_manifest_sha256=RELEASE_SHA,
        precision='FP32_master_BF16_autocast', attention='sdpa',
        tokenizer=validate_tokenizer(tokenizer))
    return tokenizer, identity, frozen


def validate_preflight(preflight, old_source, inputs, identity):
    old_source, preflight = Path(old_source), Path(preflight)
    verify_inventory(old_source/'SOURCE_INVENTORY.json',
        old_source/'experiments/public_math_pilot_v1/preflight_inputs.json',
        expected_source_commit=PREFLIGHT_COMMIT, expected_inventory_sha256=PREFLIGHT_INVENTORY,
        repo_root=old_source)
    # Reuse only if all code that produced annotations/generation is byte-identical.
    for name in ('preflight.py', 'losses.py', 'tokenization.py'):
        if sha(old_source/'experiments/public_math_pilot_v1'/name) != sha(Path(__file__).with_name(name)):
            raise ValueError('Preflight scientific implementation changed: ' + name)
    receipt = read(preflight/'PREFLIGHT_RECEIPT.json')
    old_identity = dict(identity, source_commit=PREFLIGHT_COMMIT)
    if (receipt['status'] != 'engineering_preflight_completed_not_main_admission'
            or receipt['identity'] != old_identity or receipt['formal_optimizer_updates'] != 0
            or receipt['nonformal_optimizer_updates'] != 5
            or not receipt['all_training_state_discarded_before_scientific_annotations']
            or not receipt['checkpoint_roundtrip']['roundtrip_verified']):
        raise ValueError('Engineering preflight is incomplete or incompatible')
    annotations = {}
    for i, row in enumerate(inputs['train_profile']):
        rec = read(preflight/f'annotation_{i:04d}.json')
        if rec['id'] != row['id'] or rec['identity'] != old_identity or rec['encoded_sha256'] != json_hash(row):
            raise ValueError('Preflight annotation reuse differs')
        for key in ('full', 'blank'):
            forward = read(preflight/f'annotation_{i:04d}.{key}.json')
            if (forward['id'] != row['id'] or forward['identity'] != old_identity
                    or forward['logp'] != rec['annotation'][key+'_logp']):
                raise ValueError('Preflight forward reuse differs')
        annotations[row['id']] = rec
    dev = {}
    for path in sorted((preflight/'base_dev32').glob('*.outputs.json')):
        for rec in read(path)['records']:
            if rec['id'] in dev or rec['identity'] != old_identity:
                raise ValueError('Preflight dev identity/duplicate differs')
            dev[rec['id']] = rec
    if set(dev) != {r['id'] for r in inputs['dev_profile']}:
        raise ValueError('Missing preflight dev reuse')
    return annotations, dev, receipt


def selection(row, full, blank, tokenizer):
    validate_response_alignment(row['input_ids'], row['blank_input_ids'],
        row['response_start'], row['blank_response_start'], row['response_ids'])
    return select_qdw_tokens(row['response'], row['response_ids'], row['response_offsets'], full, blank,
        blank_response_ids=row['blank_input_ids'][row['blank_response_start']:],
        special_ids=tokenizer.all_special_ids, full_prefix_length=row['response_start'],
        blank_prefix_length=row['blank_response_start'])


def technical_audit(rows, masks, audit_ids, raw):
    """Recompute all64 selectors from saved FP32 scores; expose every chosen span."""
    if len(audit_ids) != 64 or len(set(audit_ids)) != 64:
        raise ValueError('The audit subset must contain64 frozen unique IDs')
    by_id = {r['id']:r for r in rows}
    audit = []; classes = Counter(); positions = []; copies = 0; total_selected = 0
    for problem_id in audit_ids:
        row = by_id[problem_id]; ann = masks[problem_id]['annotation']
        spans = []
        for index in ann['selected_indices']:
            start, end = row['response_offsets'][index]
            text = row['response'][start:end]
            if (index not in ann['eligible_indices'] or not ann['scores'][index] > 1e-6
                    or not text.strip() or end > ann['boundary']['line_start']):
                raise ValueError('Selected token violates frozen boundary')
            stripped = text.strip()
            category = ('number' if any(c.isdigit() for c in stripped) else
                'operator' if any(c in '+-=*/<>×÷^∑∫√' for c in stripped) else
                'word' if any(c.isalpha() for c in stripped) else 'punctuation')
            copied = bool(stripped and stripped in raw[problem_id]['question'])
            classes[category] += 1; copies += copied; total_selected += 1
            positions.append(index/ann['L'])
            spans.append(dict(token_index=index, start=start, end=end, text=text,
                category=category, copied_substring_in_question=copied, score=ann['scores'][index]))
        audit.append(dict(id=problem_id, L=ann['L'], K=ann['K'],
            K_over_L=ann['K']/ann['L'], base_nll=-sum(ann['full_logp'])/ann['L'],
            boundary=ann['boundary'], selected_spans=spans,
            response=row['response'], question=raw[problem_id]['question'],
            technical_alignment_passed=True))
    return dict(schema=1, fixed_ids=audit_ids, records=audit,
        zero_K=sum(a['K']==0 for a in audit), selected_token_categories=dict(classes),
        question_substring_copy_fraction=copies/total_selected if total_selected else None,
        selected_relative_positions=positions,
        category_rule='digit then math-operator then alphabetic then punctuation; substring copy, not semantic copy',
        semantic_keyness_ground_truth=False, masks_modified_after_audit=False)


def run(args):
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    with (out/'GPU.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_time(args.deadline_unix, 300)
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
        tokenizer, identity, frozen = prepare_identity(args.base, args.release, args.inputs)
        old_ann, old_dev, preflight_receipt = validate_preflight(args.preflight, args.preflight_source, frozen, identity)
        released = load_inputs(args.release)
        raw = {r['problem_id']:r for r in released['pilot']}
        rows = [dict(r, id=r['problem_id'], response=raw[r['problem_id']]['response'])
            for r in released['tokenized_pilot']]
        if len(rows) != 4096 or len(raw) != 4096: raise ValueError('Frozen training coverage differs')
        ensure_record(out/'scientific_identity.json', identity)
        ensure_record(out/'preflight_reuse.json', dict(preflight_receipt_sha256=sha(Path(args.preflight)/'PREFLIGHT_RECEIPT.json'),
            source_commit=PREFLIGHT_COMMIT, reused_annotation_ids=sorted(old_ann), reused_dev_ids=sorted(old_dev),
            generation_batch_size=16, scientific_source_hashes_identical=True))
        ledger = PhysicalLedger(args.ledger)
        model = load_base(args.base, training=False)
        annotations = {}; manifest = []
        for i, row in enumerate(rows):
            path = out/'annotations'/f'{i:04d}.json'
            expected = dict(id=row['id'], identity=identity, encoded_sha256=json_hash(row))
            if path.exists():
                record = read(path)
                if any(record[k] != v for k, v in expected.items()):
                    raise ValueError('Stored annotation identity differs')
            elif row['id'] in old_ann:
                record = dict(**expected, annotation=old_ann[row['id']]['annotation'],
                    provenance=dict(reused_preflight=True, source_commit=PREFLIGHT_COMMIT))
                write_json(path, record)
            else:
                values = {}
                for name in ('full', 'blank'):
                    fpath = out/'annotations'/f'{i:04d}.{name}.json'
                    if fpath.exists():
                        forward = read(fpath)
                        if any(forward[k] != v for k, v in expected.items()):
                            raise ValueError('Stored forward identity differs')
                    else:
                        require_time(args.deadline_unix)
                        ledger.reserve('annotation_forward', [row['id']+'/'+name])
                        logp, stats = gold_forward(model, row, blank=name=='blank')
                        forward = dict(**expected, logp=logp, stats=stats, source_commit=args.source_commit)
                        write_json(fpath, forward)
                    values[name] = forward['logp']
                record = dict(**expected, annotation=selection(row, values['full'], values['blank'], tokenizer),
                    provenance=dict(reused_preflight=False, source_commit=args.source_commit))
                write_json(path, record)
            ann = record['annotation']
            recomputed = selection(row, ann['full_logp'], ann['blank_logp'], tokenizer)
            if recomputed != ann: raise ValueError('Frozen selector recomputation differs')
            annotations[row['id']] = record
            manifest.append(dict(id=row['id'], path=path.name, sha256=sha(path), mask_sha256=ann['mask_sha256']))
            if (i+1) % 128 == 0:
                print(json.dumps(dict(event='annotation_progress', complete=i+1, total=4096)), flush=True)
        ensure_record(out/'MASK_MANIFEST.json', dict(identity=identity, count=4096, records=manifest,
            annotation_sequence_forwards=8192, reused_preflight_sequence_forwards=64,
            formal_updates_before_mask_freeze=0))
        audit = technical_audit(rows, annotations, released['audit64'], raw)
        ensure_record(out/'MASK_AUDIT.json', audit)
        lines = ['# Fixed64 QDW technical audit', '', 'Character spans are descriptive; no semantic keyness labels or mask changes.', '']
        for r in audit['records']:
            spans = r['selected_spans']; text = r['response']; marked=[]; cursor=0
            for span in spans:
                marked.extend([text[cursor:span['start']], '⟦', text[span['start']:span['end']], '⟧'])
                cursor=span['end']
            marked.append(text[cursor:])
            lines.extend(['## '+r['id'], '', f"L={r['L']}, K={r['K']}; base NLL={r['base_nll']:.6f}", '', r['question'], '', '```text', ''.join(marked), '```', ''])
        md='\n'.join(lines)
        if (out/'MASK_AUDIT.md').exists():
            if (out/'MASK_AUDIT.md').read_text()!=md: raise ValueError('Audit text changed')
        else: (out/'MASK_AUDIT.md').write_text(md)
        dev_rows=[dict(id=r['problem_id'], prompt_ids=encode_prompt(tokenizer,r['question'])) for r in released['dev']]
        generate_rows(model, tokenizer, dev_rows, out/'generation'/'Base-dev', model_identity=identity,
            logical_name='Base-dev', ledger=ledger, deadline=args.deadline_unix, batch_size=16, reused=old_dev)
        drop_model(model); del model; gc.collect(); torch.cuda.empty_cache()
        ensure_record(out/'PREPARATION_COMPLETE.json', dict(identity=identity, mask_count=4096, dev_count=512,
            mask_manifest_sha256=sha(out/'MASK_MANIFEST.json'), audit_sha256=sha(out/'MASK_AUDIT.json'),
            dev_complete_sha256=sha(out/'generation'/'Base-dev'/'COMPLETE.json'), technical_audit_passed=True))
        return dict(status='preparation_complete', mask_count=4096, dev_count=512)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','release','inputs','preflight','preflight-source','output','ledger','source-commit'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--deadline-unix',required=True,type=float)
    print(json.dumps(run(p.parse_args()),sort_keys=True),flush=True)
