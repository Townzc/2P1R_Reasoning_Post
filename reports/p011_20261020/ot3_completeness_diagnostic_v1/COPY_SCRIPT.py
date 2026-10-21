"""Copy a genuinely completed diagnostic once; never rerun original rules."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

R = Path('.local/p011_20261020/r1')
SOURCE = R / 'ot3_completeness_diagnostic_r1'
OUT = Path('reports/p011_20261020/ot3_completeness_diagnostic_v1')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


def main():
    session = json.loads((R / 'CLI_SESSIONS.json').read_text())['ot3_completeness_diagnostic']
    if session['session_id'] != 19683 or session['state'] != 'EXIT0_CONSUMED':
        raise ValueError('Original actual CLI must be consumed exit0')
    if (SOURCE / 'FAILED.json').exists() or OUT.exists():
        raise ValueError('Failed or existing output; no completed publication retry')
    completed = json.loads((SOURCE / 'COMPLETED.json').read_text())
    summary = json.loads((SOURCE / 'SUMMARY.json').read_text())
    original = json.loads((SOURCE / 'MANIFEST.json').read_text())
    if summary['parents'] != 53107 or summary['responses'] != 849712:
        raise ValueError('Full original denominators required')
    if (completed['original_database_write'] or completed['selection_changed']
            or completed['new_tokenization'] or completed['new_model_or_symbolic_calls']):
        raise ValueError('Only admitted read-only scope is allowed')
    expected_names = {'INTENT.json', 'RESPONSE_DIAGNOSTICS.jsonl.gz',
        'PARENT_DIAGNOSTICS.jsonl', 'SUMMARY.json', 'COMPLETED.json'}
    if set(original) != expected_names:
        raise ValueError('Unexpected original diagnostic manifest')
    OUT.mkdir(exist_ok=False)
    copied = {}
    for name in sorted(expected_names):
        raw = (SOURCE / name).read_bytes()
        proof = {'bytes': len(raw), 'sha256': digest(raw)}
        if proof != original[name]:
            raise ValueError('Original result changed; retain partial publication')
        with (OUT / name).open('xb') as f:
            f.write(raw)
        if (OUT / name).read_bytes() != raw:
            raise ValueError('Copy readback mismatch; retain partial publication')
        copied[name] = proof
    raw = (SOURCE / 'MANIFEST.json').read_bytes()
    with (OUT / 'ORIGINAL_MANIFEST.json').open('xb') as f:
        f.write(raw)
    copied['ORIGINAL_MANIFEST.json'] = {'bytes': len(raw), 'sha256': digest(raw)}
    binding = json.loads(Path('reports/p011_20261020/ot3_completeness_diagnostic_preflight_v1/SOURCE_BINDING.json').read_text())
    accepted = json.loads((R / 'OT3_COMPLETENESS_DIAGNOSTIC_CR_ACCEPTED.json').read_text())
    dump(OUT / 'PUBLICATION_PROOF.json', {'written_utc': datetime.now(timezone.utc).isoformat(),
        'actual_completed_utc': completed['utc'], 'original_cli': 19683,
        'source_target': '980dd073dd597fa511341ee08294695530463d10',
        'source_and_original_input_binding': binding,
        'code_review_report_sha256': accepted['report_sha256'],
        'code_review_commit': accepted['report_commit'],
        'actual_result_review_accepted': False, 'new_selection_authorized': False,
        'copied_original_bytes': copied, 'original_rules_not_reexecuted': True,
        'summary_and_samples_copied_without_recomputation': True,
        'old_production_input_packet_unchanged': True})
    with (OUT / 'COPY_SCRIPT.py').open('xb') as f:
        f.write(Path(__file__).read_bytes())
    with (OUT / 'README.md').open('x') as f:
        f.write('''# Actual read-only OT3 completeness diagnosis — result review pending

The single admitted local diagnostic completed over all53,107 cardinality16
parents and849,712 original responses. SUMMARY, full per-response/per-parent
journals and deterministic category samples are original bytes, copied once.
Original database and disposition hashes were checked only as inputs to this
new admitted diagnostic. No production refilter, tokenization, generation,
scoring, training or reselection occurred. The fixed4032-input packet is unchanged.

N1–N5 are string categories, not correctness judgments or verified causes of
truncation. Character quantiles are not token lengths. Rprime all16 completeness
is before the remaining length/decontamination filters; known eligible count,
possible eligible upper count and unknown length are separate. Reporting flags
only require informing the owner; they never permit automatic rule changes.
The 8076 comparison uses the explicitly reviewed raw completeness denominator.

The original CLI and complete manifest must close before this copier runs.
ORIGINAL_MANIFEST is the unchanged result inventory; PUBLIC_MANIFEST binds the
new handoff. Source-code PASS is not an actual result decision. Independent
actual result review remains pending. Original failed constructors and all
existing successful inputs/encodings remain immutable. No NLL/model result or
scientific effect follows from these descriptive diagnostic counts.
''')
    manifest = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())}
        for p in sorted(OUT.iterdir()) if p.is_file()}
    dump(OUT / 'PUBLIC_MANIFEST.json', manifest)
    dump(R / 'OT3_DIAGNOSTIC_RESULT_PUBLICATION_DONE.json', {
        'utc': datetime.now(timezone.utc).isoformat(), 'packet': str(OUT),
        'public_members': len(manifest), 'actual_result_review_accepted': False,
        'no_original_diagnostic_or_science_rerun': True})
    print(json.dumps({'packet': str(OUT), 'public_members': len(manifest),
        'report_owner': summary['request_reporting_threshold']}), flush=True)


if __name__ == '__main__':
    main()
