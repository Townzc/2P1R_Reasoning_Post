"""Bind a clean failed-parent prefix before loading any continuation model.

This is data validation, not authorization. A future dispatcher must separately
bind these exact bytes, owner scope/time approval, external review, released
providers, a distinct claim and cumulative budget. No dispatch entry exists here.
"""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, sha, digest, verify
from experiments.sft_allocation_acquisition.contract import REVISION
from .pool_prefix import restore

FILES = {
    'parent_intent.json', 'parent_frozen_wallets.json', 'RECONCILIATION.json',
    'candidate_cache_reconstructed.json', 'wallet_events_reconstructed.json',
    'wallet_states_reconstructed.json',
}


def load_prefix(prefix, config, wallets, parent_order, prompt_lengths):
    prefix = Path(prefix)
    if sha(prefix/'manifest.json') != config['prefix_manifest_sha256']:
        raise ValueError('Prefix is not the frozen configured input')
    meta = read(prefix/'manifest.json')
    if set(meta['files']) != FILES:
        raise ValueError('Exact parent-prefix file roster required')
    verify(prefix, meta['files'])
    parent = read(prefix/'parent_intent.json'); old = parent['config']
    rec = read(prefix/'RECONCILIATION.json')
    frozen = read(prefix/'parent_frozen_wallets.json')
    if (config['draw'] != 2 or config['high_multiple'] != 8
            or config['max_physical_attempts'] != 16384
            or old['run_id'] != 'pool_d2' or old['role'] != 'pool'
            or parent['plan']['campaign_id'] != 'p008-main-20261013-r1'
            or any(config[k] != old[k] for k in
                   ('draw', 'high_multiple', 'max_physical_attempts', 'input_sha256'))):
        raise ValueError('Original scientific scope/input identity must remain fixed')
    terminal = rec['parent_terminal']; claim = rec['parent_claim']
    original_intent = dict(run_id=old['run_id'], source_sha256=digest(parent['release']['source_files']),
                           config_sha256=digest(old), data_sha256=old['input_sha256'])
    if (terminal['run_id'] != old['run_id'] or terminal['status'] != 'failed'
            or terminal['claim_sha256'] != digest(claim)
            or terminal['attempt_id'] != claim['attempt_id']
            or claim['plan_sha256'] != digest(parent['plan'])
            or claim['intent_sha256'] != digest(original_intent)
            or rec['parent_source_commit'] != parent['release']['commit']
            or terminal['evidence_sha256'] != rec['parent_manifest_digest']):
        raise ValueError('Failed parent provenance differs')
    if (frozen['parent_order'] != parent_order or frozen['prompt_lengths'] != prompt_lengths
            or frozen['wallets'] != [w.name for w in wallets]
            or frozen['teacher_revision'] != REVISION
            or frozen['draw'] != 2 or frozen['max_physical_attempts'] != 16384):
        raise ValueError('Original parent order, prompts or wallet roster differs')
    for file, field in [
            ('candidate_cache_reconstructed.json', 'reconstructed_cache_sha256'),
            ('wallet_events_reconstructed.json', 'reconstructed_events_sha256'),
            ('wallet_states_reconstructed.json', 'reconstructed_states_sha256')]:
        if sha(prefix/file) != rec[field]:
            raise ValueError('Independent reconstructed prefix differs')
    state = restore(wallets, read(prefix/'candidate_cache_reconstructed.json'),
                    read(prefix/'wallet_events_reconstructed.json'),
                    read(prefix/'wallet_states_reconstructed.json'), rec)
    lineage = dict(parent_campaign=parent['plan']['campaign_id'], parent_run=old['run_id'],
                   parent_terminal=terminal, reconciliation_sha256=sha(prefix/'RECONCILIATION.json'),
                   prefix_manifest_sha256=sha(prefix/'manifest.json'),
                   parent_physical_attempts=state['attempted'],
                   parent_returned_tokens=state['returned_tokens'],
                   parent_physical_batches=state['batch_index'],
                   original_parent_status='failed', unknown=0,
                   continuation_authorized_by_this_check=False)
    return state, lineage
