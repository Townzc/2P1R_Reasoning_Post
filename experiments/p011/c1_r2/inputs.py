"""Reuse the original eighteen files; only journal geometry changes for r2."""
from scripts.prepare_p011_c1_inputs import load_pack as original_load_pack


def load_pack(root, manifest, expected_inventory):
    count = expected_inventory['unique_sequences']
    if expected_inventory['journal_chunks'] != (count + 319) // 320:
        raise ValueError('Exact r2 chunk320 inventory required')
    original = {**expected_inventory, 'journal_chunks': (count + 31) // 32}
    return original_load_pack(root, manifest, original)
