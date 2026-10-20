"""Copy completed original C6 paired tables once; no statistical computation."""
import json
import shutil
from pathlib import Path
from experiments.p010.common import read, dump, sha, manifest, utc


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open('rb') as a, dst.open('xb') as b:
        shutil.copyfileobj(a, b)
    assert sha(src) == sha(dst)


def main():
    r = Path('.local/p010_20261019/r1')
    p = Path('reports/p010_20261019')
    analysis = r/'cue_benchmark_analysis_r1'
    packet = p/'c6_complete_results_v1'
    done, intent = read(analysis/'COMPLETED.json'), read(analysis/'INTENT.json')
    assert done['passed'] is True and done['original_cells'] == 4
    assert done['primary_contrasts'] == done['secondary_contrasts'] == 4
    assert done['draws'] == 10000 and done['seed'] == 20261019 and done['numpy_version'] == '2.2.6'
    assert done['new_scores'] == 0 and done['old_analyses_repeated'] is False
    assert not (analysis/'FAILED.json').exists()
    for name, expected in {**intent['input_files'], **intent['source_files']}.items():
        assert sha(name) == expected, name
    original = read(packet/'SUMMARY.json')
    assert original['total_complete_outputs'] == 21371
    sources = {}
    for name, expected in intent['source_files'].items():
        public_name = 'private_adapter/'+Path(name).name if name.startswith('.local/') else name
        assert public_name not in sources
        sources[public_name] = dict(original_path=name, sha256=expected)
    for file in analysis.iterdir():
        if file.is_file() and file.suffix in ('.json', '.csv'):
            assert '/Users/' not in file.read_text() and '/var/folders/' not in file.read_text()
    out = p/'c6_analysis_v1'
    out.mkdir(exist_ok=False)
    for file in analysis.iterdir():
        if file.is_file():
            copy(file, out/file.name)
    for name, value in sources.items():
        copy(Path(value['original_path']), out/'source'/name)
    dump(out/'SOURCE_BINDING.json', sources)
    copy(Path(__file__), out/'publisher.py')
    dump(out/'RESULT_PACKET_REFERENCE.json', dict(packet=str(packet),
        manifest_sha256=sha(packet/'MANIFEST.json'),
        failed_parent_reference=read(packet/'FAILED_PARENT_REFERENCE.json'),
        actual_results_A3_pending=True))
    (out/'README.md').write_text(
        '# Original C6 paired cue comparisons; actual A3 pending\n\n'
        'Four fixed cells compare the original development-selected cue against no cue: '
        'base MATH, base GSM8K, S1-n400 MATH, and T72-n400 MATH. '
        'Greedy is primary; the per-question mean of all four samples is secondary. '
        'All eight contrasts are retained. No winner selection or new stopping rule is introduced.\n\n'
        'These are the original once-computed paired-question results: 10,000 shared draws '
        'within each task and metric, seed20261019, numpy2.2.6, linear percentiles. '
        'The original estimator is unchanged; its sampled-vector validation was extended '
        'to the planned 1,319 GSM8K questions. The intervals condition on these observed '
        'models and questions. They are not familywise intervals, seed-population estimates, '
        'equivalence tests or mechanistic conclusions.\n\n'
        'The linked complete evidence preserves 18,871 outputs from the failed original parent '
        'and 2,500 outputs from the independent remaining call. Existing no-cue Boolean tables '
        'are reused unchanged. Independent actual A3 and fixed-sample adjudication are pending. '
        'This publication only copies saved tables and source bytes; it does not generate, '
        'decode, symbolically score, deserialize weights or rerun any bootstrap. '
        'This is technical evidence metadata, not course-report prose.\n')
    dump(out/'MANIFEST.json', manifest(out))
    dump(r/'C6_ANALYSIS_PUBLICATION_DONE.json', dict(utc=utc(), packet=str(out),
        manifest_sha256=sha(out/'MANIFEST.json'), new_scores=0,
        new_statistical_computations=0, actual_A3_pending=True))
    print(json.dumps(dict(packet=str(out), actual_A3_pending=True)))


if __name__ == '__main__':
    main()
