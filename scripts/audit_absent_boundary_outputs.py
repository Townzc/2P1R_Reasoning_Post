"""Audit the frozen seed31 identity-absent pair's 800 stored predictions on CPU.

This entry point reuses the pilot's full output/trace audit while requiring the
C012 selection and its own frozen token accounting. It performs no inference,
new sampling, selection, or holdout evaluation. Incomplete runs create no report.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from scripts import audit_replication_outputs as common
from src.family_boundary_runtime import (
    ORIGINAL_HASHES, STATUS, load_family_boundary_inputs,
)
from src.sft_data import read_jsonl, sha256_file


DEFAULT_QUEUE = Path('configs/absent_boundary_seed31/queue.json')
CODE = common.CODE + (
    'scripts/audit_absent_boundary_outputs.py', 'src/family_boundary_runtime.py',
    'scripts/audit_matching_selection.py', 'scripts/audit_pilot_structure_bias.py',
    'tests/test_absent_boundary_outputs.py',
) + tuple((common.PARENT_DATA/name).as_posix() for name in
          sorted(set(ORIGINAL_HASHES) | {'dev_blocks.json'}))
LIMITATIONS = [
    common.LIMITATIONS[0], common.LIMITATIONS[1],
    'Block, input-one and selected-reference-identity development strata remain the original seed17 labels. They were fixed before seed31 outputs, were post-hoc for seed17, and remain descriptive rather than causal or significance tests.',
    common.LIMITATIONS[3], common.LIMITATIONS[4], common.LIMITATIONS[5],
    'This is a Paths/GCM comparison within the selected identity-absent training support. Identity absence excludes the frozen neutral-operation rule, not all cancellation, computed constants, or equivalent strategies.',
    'The selected training subset and dose differ from the earlier pilot. Comparing its score difference to seed17/23 does not identify an identity-family interaction or a causal mechanism.',
]


def validate_data(cfg):
    """Reconstruct selection/schedule and verify unchanged development ancestry."""
    root = Path(cfg['data_dir'])
    if sha256_file(root/'manifest.json') != cfg['data_manifest_sha256']:
        raise ValueError('Config data manifest hash mismatch')
    manifest = common.read_json(root/'manifest.json')
    if (manifest.get('status') != STATUS or cfg.get('seed') != 31
            or manifest.get('paired_seed') != 31 or manifest.get('selection_seed') != 31
            or cfg.get('eval_seed') != 17 or manifest.get('family') != 'identity_absent'):
        raise ValueError('Expected frozen seed31 identity-absent boundary data')
    # Includes every data-file hash, source witnesses, seeded selection, all four
    # compatibility arms, the schedule, model lock, and raw split disjointness.
    load_family_boundary_inputs(cfg)
    if sha256_file(common.PARENT_DATA/'manifest.json') != common.PARENT_MANIFEST_SHA256:
        raise ValueError('Frozen parent manifest changed')
    for name, digest in common.DEV_SHA256.items():
        if sha256_file(common.PARENT_DATA/name) != digest:
            raise ValueError('Frozen parent development bytes differ: '+name)
        if name != 'dev_blocks.json' and (
                manifest['files_sha256'].get(name) != digest
                or manifest['original_files_sha256'].get(name) != digest
                or sha256_file(root/name) != digest):
            raise ValueError('Frozen development bytes differ: '+name)
    audit = common.read_json(root/'matching_audit.json')
    if (audit['arms'] != manifest['budget_per_arm']
            or audit.get('planned_arms') != ['paths', 'gcm']
            or not audit.get('all_per_update_structures_paths_gcm_equal')
            or not audit.get('all_per_example_tokens_equal')):
        raise ValueError('Frozen boundary accounting or matching claims differ')
    for key in ('optimizer_updates', 'presentations', 'supervised_response_tokens',
                'processed_nonpadding_tokens', 'padding_tokens', 'per_update'):
        if audit['arms']['paths'][key] != audit['arms']['gcm'][key]:
            raise ValueError('Frozen Paths/GCM dose differs: '+key)
    return manifest


def check_boundary_dose(verified, spec, root):
    """Check complete actual accounting against the pre-training frozen budget."""
    expected = spec['data_manifest']['budget_per_arm'][spec['config']['arm']]
    if (verified['steps'] != 1024 or expected['optimizer_updates'] != 1024
            or expected['presentations'] != 4096
            or verified['supervised_response_tokens'] != expected['supervised_response_tokens']):
        raise ValueError('Completed dose differs from the frozen boundary budget')
    planned = common.read_json(root/'budget_report.json')
    actual = common.read_json(root/'actual_budget.json')
    if actual != expected or any(planned.get(k) != v for k, v in expected.items()):
        raise ValueError('Completed full accounting differs from frozen boundary budget')
    history = read_jsonl(root/'train_history.jsonl')
    if ([h['step'] for h in history] != list(range(1, 1025))
            or len(expected['per_update']) != 1024
            or any(h['supervised_tokens'] != dose['supervised_tokens']
                   or h['processed_tokens'] != dose['processed_tokens']
                   for h, dose in zip(history, expected['per_update']))):
        raise ValueError('Completed per-update token sequence differs from frozen schedule')


def run(queue_path, out):
    return common._run_pair(
        queue_path, out, data_validator=validate_data,
        completed_dose_validator=check_boundary_dose, source_code=CODE,
        limitations=LIMITATIONS, profile='ABSENT_BOUNDARY_SEED31_V1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, default=DEFAULT_QUEUE)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.queue, args.out)
    except (FileNotFoundError, FileExistsError, ValueError, KeyError) as error:
        parser.exit(2, 'Audit refused: '+str(error)+'\n')
    print(json.dumps({'status': result['status'], 'audit_profile': result['audit_profile'],
                      'run_ids': result['run_ids'], 'matched_overall': result['matched_overall']}, indent=2))


if __name__ == '__main__':
    main()
