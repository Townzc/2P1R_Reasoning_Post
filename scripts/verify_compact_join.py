"""Independent complete-domain audit of C013 compact keys and block packing.

No production matching or packing code is imported. Tuple domains are rebuilt
with itertools; every unpruned pair uses per-occurrence AC *sets* and Hall's
condition, with no shared-structure compatibility/projection cache. Pruned
Cartesian products are certified by their necessary problem-support bound.
An audit deadline is incomplete, never a passing completeness certificate.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import io
import json
import math
from pathlib import Path
import subprocess
import time

from scripts.verify_complete_join import (
    AuditDeadline, AuditFailure, FAMILIES, INVENTORY_SHA, INVENTORY_STREAM_SHA,
    TRAIN_SHA, at_least_four, canonical, digest_file, require,
)


PUBLIC_FILES = {'catalog.json', 'support_groups.json', 'join.json', 'packing.json', 'selection.json'}
EXPECTED_PAIRS = 48_429_084
VERIFIER_SOURCES = ('scripts/verify_compact_join.py', 'scripts/verify_complete_join.py',
                    'tests/test_verify_compact_join.py')


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def receipt(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def read_encoded(report_dir, name, expected, input_hashes):
    require(type(name) is str and Path(name).name == name, 'Archive part must be a basename')
    path = report_dir/name
    raw = path.read_bytes()
    require(receipt(raw) == {'sha256': expected['encoded_sha256'], 'bytes': expected['encoded_bytes']},
            'Encoded archive hash/size mismatch: '+name)
    input_hashes[str(path)] = expected['encoded_sha256']
    return base64.b64decode(b''.join(raw.split()), validate=True)


def public_artifacts(report_dir, summary, input_hashes):
    """Read exact original JSON bytes, including fresh-clone archive fallback."""
    storage_path = report_dir/'storage.json'
    storage = json.loads(storage_path.read_text()) if storage_path.is_file() else None
    if storage is not None:
        require(storage['format'] == 'gzip-base64-original-bytes-v1', 'Unknown public storage format')
        input_hashes[str(storage_path)] = digest_file(storage_path)['sha256']
    result = {}
    for name, expected in summary['output_sha256'].items():
        path = report_dir/name
        if path.is_file():
            raw = path.read_bytes()
            input_hashes[str(path)] = expected
        else:
            require(storage is not None and name in storage['files'], 'Missing original and public archive: '+name)
            spec = storage['files'][name]
            raw = gzip.decompress(read_encoded(report_dir, spec['archive_file'], spec, input_hashes))
            require(receipt(raw) == {'sha256': spec['original_sha256'], 'bytes': spec['original_bytes']},
                    'Reconstructed JSON hash/size mismatch: '+name)
        require(hashlib.sha256(raw).hexdigest() == expected, 'Changed C013 output: '+name)
        result[name] = json.loads(raw)
    return result, storage


def key_input(report_dir, path, summary, storage, input_hashes):
    """Return a path or in-memory gzip; never materialize a new search artifact."""
    if path is not None and Path(path).is_file():
        path = Path(path)
        require(digest_file(path) == summary['private_key_archive'], 'Compact archive receipt differs')
        input_hashes[str(path)] = summary['private_key_archive']['sha256']
        return path
    require(storage is not None and 'compact_key_archive' in storage, 'Missing compact key archive and public fallback')
    spec = storage['compact_key_archive']
    require({'sha256': spec['original_sha256'], 'bytes': spec['original_bytes']} == summary['private_key_archive'],
            'Public compact archive receipt disagrees with producer')
    parts = spec['parts_in_order']
    require(parts and len({part['file'] for part in parts}) == len(parts), 'Empty or duplicate archive parts')
    raw = b''.join(read_encoded(report_dir, part['file'], part, input_hashes) for part in parts)
    require(receipt(raw) == summary['private_key_archive'], 'Reconstructed compact archive hash/size mismatch')
    return io.BytesIO(raw)


def reconstruct_inventory(records, catalog, check):
    """Independent coordinate deduplication, functional relation and tuple grid."""
    pids = sorted({r['problem_id'] for r in records})
    structures = sorted({r['structure_id'] for r in records})
    require(catalog['problem_ids'] == pids and catalog['structure_ids'] == structures,
            'Problem/structure catalog does not equal the input inventory')
    require(all(type(x) is str and x for x in pids + structures), 'Invalid catalog string')
    pid_ids, structure_ids = ({v: i for i, v in enumerate(values)} for values in (pids, structures))
    occurrences = sorted({(pid_ids[r['problem_id']], r['n_supervised']) for r in records})
    occurrence_ids = {v: i for i, v in enumerate(occurrences)}
    pid_masks, occurrence_masks = defaultdict(int), defaultdict(int)
    classes, representatives, lookup, relation = defaultdict(set), {}, {}, {}
    for row in records:
        check()
        pid, length, family, structure, ac = (row[k] for k in
                                             ('problem_id', 'n_supervised', 'family', 'structure_id', 'ac_class'))
        require(integer(length, 1) and family in FAMILIES and type(ac) is str and ac,
                'Invalid inventory coordinate')
        require(row.get('encodable', True) is True, 'Ineligible row in selected inventory')
        coordinate = (pid, ac)
        require(coordinate not in relation or relation[coordinate] == structure,
                'AC class maps to multiple structures; Hall decomposition invalid')
        relation[coordinate] = structure
        pi, sid, oi = pid_ids[pid], structure_ids[structure], occurrence_ids[(pid_ids[pid], length)]
        pid_masks[(family, sid)] |= 1 << pi
        occurrence_masks[(family, sid)] |= 1 << oi
        classes[(pi, length, family, sid)].add(ac)
        encoded = canonical(row)
        ref = hashlib.sha256(encoded).hexdigest()
        require(ref not in lookup or lookup[ref] == row, 'Record reference collision')
        lookup[ref] = row
        key = (pid, length, family, structure, ac)
        if key not in representatives or encoded < representatives[key][0]:
            representatives[key] = (encoded, ref)
    classes = {k: frozenset(v) for k, v in classes.items()}
    entries, groups = {}, {}
    for family, name in zip(FAMILIES, ('identity_tuples', 'nonidentity_tuples')):
        domain = sorted(s for f, s in pid_masks if f == family and at_least_four(pid_masks[(f, s)]))
        table, grouped = [], defaultdict(list)
        for item in itertools.combinations(domain, 4):
            check()
            pm, om = pid_masks[(family, item[0])], occurrence_masks[(family, item[0])]
            for sid in item[1:]:
                pm &= pid_masks[(family, sid)]
                om &= occurrence_masks[(family, sid)]
            if at_least_four(pm):
                grouped[pm].append(len(table))
                table.append((item, om))
        supplied = catalog[name]
        require(all(type(t) is list and len(t) == 4 and all(integer(v) for v in t) for t in supplied),
                'Malformed tuple catalog')
        require(supplied == [list(t) for t, _ in table], 'Independent complete tuple domain differs: '+family)
        entries[family], groups[family] = table, sorted(grouped.items())
    return {'pids': pids, 'structures': structures, 'occurrences': occurrences,
            'classes': classes, 'entries': entries, 'groups': groups,
            'representatives': representatives, 'lookup': lookup}


def exact_support(si, sn, occurrence_mask, occurrences, classes):
    """One independent Hall set check per occurrence; return each pid's lowest L."""
    shared = set(si).intersection(sn)
    found = {}
    while occurrence_mask:
        low = occurrence_mask & -occurrence_mask
        pi, length = occurrences[low.bit_length() - 1]
        occurrence_mask ^= low
        if pi in found:
            continue
        if all(len(classes[(pi, length, FAMILIES[0], sid)] |
                   classes[(pi, length, FAMILIES[1], sid)]) >= 2 for sid in shared):
            found[pi] = length
    return tuple(found.items())


def validate_witness(key, signature, support_lengths, index, counters, check):
    si, sn = signature
    names = index['structures']
    require(key['identity_structures'] == [names[s] for s in si]
            and key['nonidentity_structures'] == [names[s] for s in sn], 'Representative structures differ')
    expected = {index['pids'][pi]: length for pi, length in support_lengths}
    require(key['problem_ids'] == sorted(expected) and set(key['witnesses']) == set(expected),
            'Representative problem support differs')
    for pid, length in expected.items():
        check()
        witness = key['witnesses'][pid]
        require(witness['problem_id'] == pid and witness['n_supervised'] == length,
                'Representative does not use the lowest common length')
        slots = witness['slots']
        require(len(slots) == 8 and len({s['ac_class'] for s in slots}) == 8,
                'Representative must use eight distinct numerical AC classes')
        expected_slots = [(family, names[sid]) for family, items in zip(FAMILIES, (si, sn)) for sid in items]
        require([(s['family'], s['structure_id']) for s in slots] == expected_slots,
                'Representative family/structure slots differ or are reordered')
        for slot in slots:
            require(set(slot) == {'family', 'structure_id', 'ac_class', 'record_ref'}, 'Malformed reference slot')
            ref = slot['record_ref']
            require(ref in index['lookup'], 'Unresolved record_ref')
            row = index['lookup'][ref]
            require(row['problem_id'] == pid and row['n_supervised'] == length
                    and all(row[k] == slot[k] for k in ('family', 'structure_id', 'ac_class')),
                    'Referenced inventory row disagrees with slot')
            coordinate = (pid, length, slot['family'], slot['structure_id'], slot['ac_class'])
            require(index['representatives'][coordinate][1] == ref, 'Noncanonical coordinate representative')
            counters['representative_slots_checked'] += 1
        counters['representative_witnesses_checked'] += 1


def verify_records(records, catalog, join, support_groups, key_archive, *, check=lambda: None):
    """Generic finite verifier for synthetic fixtures and hash-checked real inputs."""
    counters = {'stream_keys_checked': 0, 'representative_witnesses_checked': 0,
                'representative_slots_checked': 0, 'independent_pruned_pairs': 0,
                'independent_exact_pairs': 0, 'independent_valid_keys': 0}
    require(set(catalog) == {'problem_ids', 'structure_ids', 'identity_tuples',
                             'nonidentity_tuples', 'length_signatures'}, 'Unexpected catalog schema')
    require(all(join.get(k) is True for k in ('complete', 'grid_complete', 'representatives_complete',
                                             'ac_to_structure_functionality_verified')),
            'Cannot certify an incomplete compact join')
    require(join['length_mode'] == 'common', 'Wrong length rule')
    index = reconstruct_inventory(records, catalog, check)
    entries, groups = index['entries'], index['groups']
    counts = {f: len(entries[f]) for f in FAMILIES}
    total = counts[FAMILIES[0]] * counts[FAMILIES[1]]
    require(join['frequent_tuples_by_family'] == counts, 'Tuple count mismatch')
    require(join['mask_groups_by_family'] == {f: len(groups[f]) for f in FAMILIES}, 'Mask group count mismatch')
    require(join['total_candidate_pairs'] == join['represented_pairs'] == total
            and join['pruned_pairs'] + join['exact_pairs'] == total and join['unrepresented_pairs'] == 0,
            'Producer finite-grid accounting does not close')
    signatures, signature_seen = [], set()
    for raw in catalog['length_signatures']:
        check()
        require(type(raw) is list and len(raw) >= 4
                and all(type(pair) is list and len(pair) == 2 and integer(pair[0])
                        and pair[0] < len(index['pids']) and integer(pair[1], 1) for pair in raw),
                'Malformed length signature')
        signature = tuple(map(tuple, raw))
        require([p for p, _ in signature] == sorted({p for p, _ in signature}),
                'Length signature repeats or reorders problem IDs')
        require(signature not in signature_seen, 'Duplicate length signature')
        signature_seen.add(signature)
        signatures.append(signature)
    emitted, groups_seen, signature_used = {}, {}, set()
    digest, size = hashlib.sha256(), 0
    ni, nn = (counts[f] for f in FAMILIES)
    with gzip.open(key_archive, 'rb') as stream:
        for line in stream:
            check()
            digest.update(line)
            size += len(line)
            key = json.loads(line)
            require(type(key) is list and len(key) == 3 and all(integer(x) for x in key), 'Malformed compact key')
            ti, tn, li = key
            require(line == f'[{ti},{tn},{li}]\n'.encode('ascii'), 'Noncanonical compact stream encoding')
            require(ti < ni and tn < nn and li < len(signatures), 'Compact catalog index out of bounds')
            pair = ti * nn + tn
            require(pair not in emitted, 'Duplicate compact structure key')
            si, oi = entries[FAMILIES[0]][ti]
            sn, on = entries[FAMILIES[1]][tn]
            actual = exact_support(si, sn, oi & on, index['occurrences'], index['classes'])
            require(len(actual) >= 4 and actual == signatures[li],
                    'Compact key has wrong exact support or nonminimum length')
            emitted[pair] = li
            signature_used.add(li)
            support = tuple(pi for pi, _ in actual)
            seen = groups_seen.setdefault(support, {'count': 0, 'minimum': (ti, tn), 'length_id': li})
            seen['count'] += 1
            if (ti, tn) < seen['minimum']:
                seen['minimum'], seen['length_id'] = (ti, tn), li
            counters['stream_keys_checked'] += 1
    require(signature_used == set(range(len(signatures))), 'Catalog has unused length signatures')
    require(digest.hexdigest() == join['key_stream_sha256'], 'Compact key stream digest mismatch')
    require(len(emitted) == join['valid_key_count'] == join['counters']['valid_key_count'], 'Valid key count mismatch')
    require(len(support_groups) == len(groups_seen) == join['support_group_count'], 'Support group count mismatch')
    supplied_supports = []
    pid_ids = {pid: pi for pi, pid in enumerate(index['pids'])}
    for group in support_groups:
        check()
        require(group['problem_ids'] == sorted(set(group['problem_ids']))
                and all(pid in pid_ids for pid in group['problem_ids']), 'Malformed group support')
        support = tuple(pid_ids[pid] for pid in group['problem_ids'])
        supplied_supports.append(support)
        require(support in groups_seen, 'Unknown exact support group')
        observed = groups_seen[support]
        require(group['valid_key_count'] == observed['count'], 'Support group key multiplicity differs')
        require(group['representative_tuple_ids'] == list(observed['minimum'])
                and group['representative_length_signature_id'] == observed['length_id'],
                'Support group representative is not the lexicographic minimum')
        ti, tn = observed['minimum']
        validate_witness(group['representative_key'],
                         (entries[FAMILIES[0]][ti][0], entries[FAMILIES[1]][tn][0]),
                         signatures[observed['length_id']], index, counters, check)
    require(supplied_supports == sorted(groups_seen), 'Duplicate or reordered exact support groups')
    supported = sorted({index['pids'][pi] for support in groups_seen for pi in support})
    require(join['supported_problem_ids'] == supported, 'Supported-problem union mismatch')
    remaining = set(emitted)
    for mask_i, tuples_i in groups[FAMILIES[0]]:
        for mask_n, tuples_n in groups[FAMILIES[1]]:
            check()
            if not at_least_four(mask_i & mask_n):
                counters['independent_pruned_pairs'] += len(tuples_i) * len(tuples_n)
                continue
            for ti in tuples_i:
                si, oi = entries[FAMILIES[0]][ti]
                for tn in tuples_n:
                    check()
                    sn, on = entries[FAMILIES[1]][tn]
                    actual = exact_support(si, sn, oi & on, index['occurrences'], index['classes'])
                    pair = ti * nn + tn
                    if len(actual) >= 4:
                        require(pair in emitted and actual == signatures[emitted[pair]],
                                'Full finite audit found an omitted or altered valid key')
                        remaining.remove(pair)
                        counters['independent_valid_keys'] += 1
                    else:
                        require(pair not in emitted, 'Full finite audit found an invalid emitted key')
                    counters['independent_exact_pairs'] += 1
    require(not remaining, 'Emitted keys were not covered by independent finite audit')
    require(counters['independent_pruned_pairs'] == join['pruned_pairs']
            and counters['independent_exact_pairs'] == join['exact_pairs']
            and counters['independent_pruned_pairs'] + counters['independent_exact_pairs'] == total
            and counters['independent_valid_keys'] == len(emitted), 'Independent finite counts do not close')
    return {'audit_complete': True, 'total_candidate_pairs': total, 'counters': counters,
            'frequent_tuples_by_family': counts, 'eligible_records': len(records),
            'eligible_problems': len(index['pids']), 'supported_problem_ids': supported,
            'support_group_count': len(groups_seen), 'valid_key_count': len(emitted),
            'key_stream': {'sha256': digest.hexdigest(), 'bytes': size}}, index


def verify_packing(packing, groups, index):
    """Validate concrete integer blocks and an independent connected-component bound."""
    require(packing.get('input_join_complete') is True, 'Packing used incomplete support')
    supports = [set(g['problem_ids']) for g in groups]
    all_pids = set().union(*supports) if supports else set()
    used, by_group = [], defaultdict(list)
    for block in packing['blocks']:
        gi, pids = block['group_id'], block['problem_ids']
        require(integer(gi) and gi < len(groups), 'Packing group index invalid')
        require(type(pids) is list and len(pids) == 4 and pids == sorted(set(pids))
                and set(pids) <= supports[gi], 'Packing block lacks four distinct supported problems')
        used.extend(pids)
        by_group[gi].extend(pids)
        expected = dict(groups[gi]['representative_key'], problem_ids=pids, witnesses={})
        for pid in pids:
            witness = groups[gi]['representative_key']['witnesses'][pid]
            slots = [{**{k: v for k, v in slot.items() if k != 'record_ref'},
                      'record': index['lookup'][slot['record_ref']]} for slot in witness['slots']]
            expected['witnesses'][pid] = dict(witness, slots=slots)
        require(block['representative'] == expected, 'Packing expanded witness differs from verified representative')
    require(len(used) == len(set(used)) and packing['used_problem_ids'] == sorted(used),
            'Packing repeats a problem or reports wrong selected IDs')
    primal = len(packing['blocks'])
    require(integer(packing['primal_block_count']) and packing['primal_block_count'] == primal,
            'Packing primal count differs from concrete integer blocks')
    assignments = packing['group_assignments']
    require(len(assignments) == len(by_group), 'Packing group assignment count differs')
    assignment_seen = set()
    for assignment in assignments:
        gi = assignment['group_id']
        require(integer(gi) and gi in by_group and gi not in assignment_seen, 'Duplicate or unsupported group assignment')
        assignment_seen.add(gi)
        require(integer(assignment['block_count']) and 4 * assignment['block_count'] == len(by_group[gi])
                and assignment['problem_ids'] == sorted(by_group[gi])
                and assignment['representative'] == groups[gi]['representative_key'],
                'Packing assignment violates sum x = 4y or its representative')
    elementary = min(len(all_pids) // 4, sum(len(s) // 4 for s in supports))
    require(packing['input_group_count'] == len(groups) and packing['input_problem_count'] == len(all_pids)
            and packing['elementary_upper_bound'] == elementary, 'Packing input/count bound differs')
    upper, dual, status = packing['integer_upper_bound'], packing['dual_upper_bound'], packing['solver_status']
    require(integer(upper) and primal <= upper <= elementary, 'Packing solver bound inconsistent with primal')
    require(type(status) is int and status in (0, 1, 4)
            and packing['is_optimal'] is (status == 0), 'Packing solver status/optimality inconsistent')
    if dual is not None:
        require(type(dual) in (int, float) and math.isfinite(dual) and dual >= primal - 1e-6,
                'Packing dual bound inconsistent with primal')
        if status != 0:
            require(upper == min(elementary, math.floor(dual + 1e-6)), 'Packing integerized dual bound differs')
    if status == 0:
        require(upper == primal and (dual is None or math.floor(dual + 1e-6) == primal),
                'Claimed solver optimum disagrees with solver bound')
    require(packing['absolute_gap_blocks'] == upper - primal, 'Packing absolute gap differs')
    # A block lives wholly inside one hypergraph connected component. This
    # independently certifies sum floor(|component|/4), without trusting HiGHS.
    parent = {p: p for p in all_pids}
    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p
    for support in supports:
        first, *rest = sorted(support)
        for pid in rest:
            parent[find(pid)] = find(first)
    components = defaultdict(list)
    for pid in sorted(all_pids):
        components[find(pid)].append(pid)
    components = sorted(components.values())
    independent_bound = sum(len(component) // 4 for component in components)
    require(primal <= independent_bound, 'Packing violates independent component bound')
    return {'primal_blocks_verified': primal, 'selected_problem_ids': sorted(used),
            'solver_bound_consistency_checked': True, 'reported_solver_integer_upper_bound': upper,
            'solver_claims_optimal': status == 0, 'component_problem_ids': components,
            'component_upper_bound': independent_bound,
            'optimality_independently_certified': primal == independent_bound,
            'optimality_basis': ('concrete primal equals independent support-component bound'
                                 if primal == independent_bound else
                                 'primal and reported solver-bound consistency only; no independent optimality certificate'),
            'scope': 'No MILP rerun or independent verification of the solver dual certificate'}


def audit(report_dir, key_archive, inventory, *, max_seconds=600.0):
    require(type(max_seconds) in (int, float) and 0 < max_seconds <= 600, 'Use one finite audit deadline of at most 600 seconds')
    started = time.monotonic()
    progress = {'stage': 'source_verification'}
    def check():
        if time.monotonic() - started >= max_seconds:
            raise AuditDeadline('Independent compact audit deadline reached; no completeness certificate', progress)
    report_dir, inventory = map(Path, (report_dir, inventory))
    summary = json.loads((report_dir/'summary.json').read_text())
    require(summary['diagnostic_id'] == 'C013' and summary['status'] == 'complete'
            and summary['join_complete'] is True, 'Complete C013 final summary required')
    require(set(summary['output_sha256']) == PUBLIC_FILES, 'Unexpected C013 public artifact inventory')
    input_hashes = {(report_dir/'summary.json').as_posix(): digest_file(report_dir/'summary.json')['sha256']}
    artifacts, storage = public_artifacts(report_dir, summary, input_hashes)
    archive = key_input(report_dir, key_archive, summary, storage, input_hashes)
    for name, expected in summary['source_sha256'].items():
        check()
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Source path must be repository relative')
        raw = subprocess.check_output(['git', 'show', f"{summary['source_commit']}:{name}"])
        require(hashlib.sha256(raw).hexdigest() == expected, 'Committed source hash differs: '+name)
    old_source = Path('reports/family_matching_20260909_r1/per_problem.jsonl')
    old_summary = json.loads(Path('reports/family_matching_20260909_r1/summary.json').read_text())
    old_sha = digest_file(old_source)['sha256']
    require(old_sha == old_summary['output_sha256'][old_source.name]
            and old_sha == summary['source_sha256'][str(old_source)], 'C009 necessary filter source differs')
    input_hashes[str(old_source)] = old_sha
    lengths = {p['problem_id']: set(p['structure_lengths']) for p in map(json.loads, old_source.read_text().splitlines())}
    train = Path('runs/pilot_v1_20260908_r3/train_blocks.json')
    require(digest_file(train)['sha256'] == TRAIN_SHA, 'Original training problem source changed')
    input_hashes[str(train)] = TRAIN_SHA
    problems = {p['problem']['problem_id']: p['problem'] for block in json.loads(train.read_text()) for p in block['problems']}
    require(len(problems) == 256 and set(lengths) == set(problems), 'Wrong original/filtered problem population')
    require(digest_file(inventory)['sha256'] == INVENTORY_SHA == summary['inventory_compressed_sha256'], 'Tokenized archive changed')
    input_hashes[str(inventory)] = INVENTORY_SHA
    rows, selected, stream_hash, all_pids, relation = 0, [], hashlib.sha256(), set(), {}
    progress['stage'] = 'inventory'
    with gzip.open(inventory, 'rb') as source:
        for line in source:
            check()
            stream_hash.update(line)
            row = json.loads(line)
            pid, ac, structure = (row[k] for k in ('problem_id', 'ac_class', 'structure_id'))
            require(pid in problems and all(row[k] == problems[pid][k] for k in ('numbers', 'target', 'prompt')),
                    'Inventory problem identity differs from original')
            require(row['family'] in FAMILIES, 'Unknown inventory family')
            require((pid, ac) not in relation or relation[(pid, ac)] == structure, 'Full inventory AC-to-structure relation is not functional')
            relation[(pid, ac)] = structure
            all_pids.add(pid)
            rows += 1
            if row['encodable'] and row['n_supervised'] in lengths[pid]:
                selected.append(row)
    require(rows == 25846 and all_pids == set(problems)
            and stream_hash.hexdigest() == INVENTORY_STREAM_SHA == summary['inventory_stream_sha256'],
            'Original tokenized stream count/hash/population differs')
    require(len(selected) == 5774 and len({r['problem_id'] for r in selected}) == 66, 'C009 necessary filter not reproduced')
    join, catalog, groups, packing = (artifacts[name] for name in
                                     ('join.json', 'catalog.json', 'support_groups.json', 'packing.json'))
    progress['stage'] = 'complete_stream_and_independent_finite_grid'
    result, index = verify_records(selected, catalog, join, groups, archive, check=check)
    require(result['total_candidate_pairs'] == EXPECTED_PAIRS == summary['total_candidate_pairs']
            == summary['represented_pairs'], 'C013 fixed complete grid differs')
    require(result['key_stream'] == summary['private_key_stream'], 'Compact stream receipt differs')
    require(result['valid_key_count'] == summary['valid_key_count']
            and result['support_group_count'] == summary['support_group_count']
            and len(result['supported_problem_ids']) == summary['supported_problem_count'], 'C013 final summary counts differ')
    progress['stage'] = 'packing_and_final_hashes'
    packing_result = verify_packing(packing, groups, index)
    require(packing_result['primal_blocks_verified'] == summary['packing_block_count']
            and packing['is_optimal'] is summary['packing_proved_optimal']
            and packing['integer_upper_bound'] == summary['packing_upper_bound'], 'Packing summary disagrees')
    for name, expected in input_hashes.items():
        check()
        require(digest_file(name)['sha256'] == expected, 'Audit input changed during verification: '+name)
    return {**result, 'status': 'passed', 'diagnostic_id': 'C013', 'inventory_rows': rows,
            'producer_source_commit': summary['source_commit'], 'input_sha256': input_hashes,
            'packing_verification': packing_result, 'elapsed_seconds': time.monotonic()-started,
            'verification_method': 'Independent itertools complete tuple domains and per-occurrence AC-set Hall checks; all positive and negative keys, exact lowest lengths, representative refs and integer packing checked',
            'scope_limits': ['No tokenization, expression search, new model output, GPU or holdout evaluation',
                             'Inventory legality/tokenization inherit the exact pinned C009 bytes',
                             'Solver-bound consistency is not an independent dual certificate; component equality separately certifies optimality when available']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--keys', type=Path, help='Optional original gzip; missing input uses verified public archive parts')
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--max-seconds', type=float, default=600)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Fresh immutable verification output required')
    try:
        result = audit(args.report, args.keys, args.inventory, max_seconds=args.max_seconds)
    except (AuditFailure, AuditDeadline, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        result = {'status': 'incomplete' if isinstance(exc, AuditDeadline) else 'failed',
                  'audit_complete': False, 'error': str(exc)}
        if isinstance(exc, AuditDeadline):
            result['progress'] = exc.counters
    result.update(completed_at_utc=datetime.now(timezone.utc).isoformat(), gpu_seconds_added=0,
                  verifier_source_sha256={name: digest_file(name)['sha256'] for name in VERIFIER_SOURCES})
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_sha256', 'supported_problem_ids', 'packing_verification')}, sort_keys=True), flush=True)
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
