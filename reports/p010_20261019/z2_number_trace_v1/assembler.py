"""Create-only technical tables from completed metadata; never score or analyze."""
import csv
import hashlib
import json
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

from experiments.p010.common import dump, manifest, sha, utc

R = Path('.local/p010_20261019/r1')
P = Path('reports/p010_20261019')
OUT = P/'z2_number_trace_v1'
SOURCES, TRACES = {}, []


def source(path):
    path = Path(path)
    assert 'z1' not in str(path).lower(), 'Claude-owned Z1 content excluded'
    if str(path) not in SOURCES:
        commit = subprocess.check_output(
            ['git', 'log', '-1', '--format=%H', '--', str(path)], text=True).strip()
        SOURCES[str(path)] = dict(sha256=sha(path), bytes=path.stat().st_size,
                                 file_commit=commit or None)
    return path


def read(path):
    return json.loads(source(path).read_text())


def rows(path):
    with source(path).open() as f:
        return list(csv.DictReader(f))


def trace(output, row, path, locator, rule='copy_saved_value'):
    path = source(path)
    TRACES.append(dict(output=output, row=row, source=str(path),
                       source_sha256=sha(path), locator=locator, rule=rule))


def table(name, data):
    assert data
    with (OUT/name).open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(data)


def copy(path, name):
    path = source(path)
    dest = OUT/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with path.open('rb') as a, dest.open('xb') as b:
        shutil.copyfileobj(a, b)
    assert sha(path) == sha(dest)
    trace(name, 'entire_original_file', path, '/', 'byte_exact_copy_no_recompute')


def main():
    assert not OUT.exists()
    assert read(P/'c6_analysis_v1/COMPLETED.json')['passed'] is True
    assert read(P/'e3_complete_results_v1/SUMMARY.json')['technical_unknown'] == 0
    OUT.mkdir()
    composition = []
    for model in ('t15', 't7', 't72'):
        sp = P/f'{model}_data_candidate_v1/SELECTION.json'
        mp = P/f'{model}_data_candidate_v1/SUMMARY.json'
        selected, summaries = read(sp), read(mp)
        for cell, data in selected['cells'].items():
            old = summaries['cells'][cell]
            k = int(cell.rsplit('_k', 1)[1])
            opened = len(data.get('examined_prefix', data['question_ids']))
            cancelled = model in ('t7', 't72') and k in (4, 8)
            status = ('owner_cancelled_unattempted' if cancelled else
                      'reused_original_S1' if data.get('reuse_original_S1') else
                      'completed_original_cell')
            composition.append(dict(teacher=model, cell=cell, P_open=opened,
                P_cov=data['P_cov'], K_requested=k, N_selected=data['N'],
                K_observed_mean=data['N']/data['P_cov'],
                underfilled_questions=data.get('underfilled_questions', ''),
                retried_questions=data.get('retried_questions', ''),
                unverified_K1_questions=data.get('unverified_questions', ''),
                nesting_conflict_questions=len(data.get('nesting_conflicts', [])),
                once_each_training_targets=old.get('once_each_targets', ''),
                status=status,
                pool_attempts_cost_scope='shared_teacher_pool_not_additive_across_cells'))
            trace('T1_COMPOSITION.csv', model+'/'+cell, sp, '/cells/'+cell,
                  'copy; P_open=len(examined_prefix_or_question_ids); K_observed_mean=N/P_cov')
            trace('T1_COMPOSITION.csv', model+'/'+cell, mp, '/cells/'+cell)
    assert len(composition) == 13
    table('T1_COMPOSITION.csv', composition)
    copy(P/'owner_selection_and_e4_endpoint_20261020_v1/README.md',
         'references/OWNER_CANCELLED_CELLS.md')

    billing = R/'billing_e3_c6_completed_r1'
    bill = read(billing/'report.json')
    summary = read(billing/'summary.json')
    receipt = read(billing/'READ_RECEIPT.json')
    costs = {}
    for row in bill:
        costs[row['object_id']] = costs.get(row['object_id'], Decimal('0'))+Decimal(row['cost'])
    pool = []
    for model in ('t15', 't7', 't72'):
        root = P/f'teacher_{model}_complete_v1'
        ep = root/'ORIGINAL_RESULT_ENVELOPE.json'
        env = read(ep)
        submitted = read(root/'ORIGINAL_SUBMITTED.json')
        inherited = env['result'].get('inherited_raw_outputs', 0)
        old_reuse = 460 if model == 't15' else 0
        app = submitted['app_id']
        pool.append(dict(teacher=model,
            new_outputs_in_completed_call=env['result']['completed_unique_new_outputs'],
            inherited_failed_call_outputs=inherited, reused_preP010_outputs=old_reuse,
            complete_saved_pool_outputs=env['result']['completed_unique_new_outputs']+inherited+old_reuse,
            completed_call_elapsed_seconds=env['seconds_including_pack'],
            completed_app_id=app,
            completed_app_delayed_gross_usd=str(costs[app]) if app in costs else '',
            cost_is_complete_pool_cost=False,
            scope='shared_pool; failed/setup/cache/other_apps_are_not_allocated_to_cells'))
        trace('T1_POOL_ATTEMPTS_AND_USAGE.csv', model, ep, '/result and /seconds_including_pack',
              'copy_and_add_disjoint_saved_counts; elapsed_not_GPU_billed_seconds')
        trace('T1_POOL_ATTEMPTS_AND_USAGE.csv', model, billing/'report.json',
              'all original rows with object_id='+app, 'decimal_sum_observed_app_rows')
    assert [x['complete_saved_pool_outputs'] for x in pool] == [6400, 9666, 14098]
    table('T1_POOL_ATTEMPTS_AND_USAGE.csv', pool)
    public_rows = [
        {k:x[k] for k in ('object_id', 'description', 'interval_start', 'cost')}
        for x in bill if str(x['description']).lower().startswith('p010')]
    dump(OUT/'OBSERVED_P010_PREFIX_METER.json', dict(
        original_private_report_sha256=sha(billing/'report.json'),
        original_private_summary_sha256=sha(billing/'summary.json'),
        read_receipt=receipt, projection='P010-description rows; account/environment/tags omitted.',
        rows=public_rows,
        prefix_gross_sum_usd=str(sum((Decimal(x['cost']) for x in public_rows), Decimal('0'))),
        workspace_metered_cost=summary['metered_cost'], workspace_cash_billed=summary['billed_cost'],
        final_invoice=False, remaining_credits_not_inferred=True,
        may_omit_unlabelled_setup_build_storage_or_lag=True,
        failed_rows_not_excluded=True, no_new_provider_request=True))

    t2 = 'reports/p008_20261013/registered_primary_results_v1/ALL_CONTRASTS.csv'
    original = rows(t2)
    gaps = [x for x in original if x['kind'] == 'policy_gap']
    assert len(gaps) == 12
    table('T2_P008_DEPTH_MINUS_BREADTH.csv', gaps)
    for row in gaps:
        trace('T2_P008_DEPTH_MINUS_BREADTH.csv', row['name'], t2, 'name='+row['name'])
    copy(t2, 'references/P008_ALL31_ORIGINAL_CONTRASTS.csv')
    copy('reports/p008_20261013/registered_primary_results_v1/ALL_CELLS.csv',
         'references/P008_ORIGINAL_CELLS.csv')
    copy('reports/p008_20261013/registered_primary_results_v1/allocation_joint_scaling.png',
         'figures/F1_P008_ORIGINAL.png')
    copy('reports/p008_20261013/registered_primary_results_v1/FIGURE_BINDING.json',
         'figures/F1_ORIGINAL_BINDING.json')
    copy(P/'c9_complete_students_v1/figures/F2_MATH_AXES.png', 'figures/F2_ORIGINAL.png')
    copy(P/'c9_complete_students_v1/figures/F2_MATH_AXES.pdf', 'figures/F2_ORIGINAL.pdf')
    copy(P/'c9_complete_students_v1/VISUAL_CHECK.json', 'figures/F2_PRIOR_VISUAL_CHECK.json')
    copy(P/'c9_complete_students_v1/figures/RENDER_PROVENANCE.json',
         'figures/F2_PRIOR_RENDER_PROVENANCE.json')
    (OUT/'FIGURES.md').write_text(
        '# Original figures with required captions\n\n'
        '## F1 — P008: 不是受控的数据规模曲线\n\n'
        '![P008 — 不是受控的数据规模曲线](figures/F1_P008_ORIGINAL.png)\n\n'
        'Original PNG bytes are reused. Procurement and training vary jointly; the existing '
        'conditional bridge does not establish the full interaction. Original source and '
        'table hashes are bound in the trace. No new plot or bootstrap was produced.\n\n'
        '## F2 — Original three-teacher axes\n\n'
        '![Original saved F2](figures/F2_ORIGINAL.png)\n\n'
        'Original PNG/PDF bytes and prior visual-check record are copied unchanged. '
        'Cancelled T7/T72 K4/K8 cells remain unavailable. Seed29 is in separate saved tables.\n')

    p1 = Path('reports/p009_20261014/p1_complete_scoring_v1/SUMMARY.json')
    old_gsm = Path('reports/p009_20261014/stage0_complete_a2_v1/ORIGINAL_SUMMARIES.json')
    baselines = []
    for key, name in [('qwen_math_zero', 'Qwen2.5-1.5B base 0-shot'),
                      ('qwen_math_four', 'Qwen2.5-1.5B base 4-shot'),
                      ('teacher_math_zero', 'Qwen2.5-Math-1.5B-Instruct 0-shot')]:
        d = read(p1)['counts'][key]
        baselines.append(dict(task='MATH500', endpoint=name, engine='vLLM0.11',
            correct=d['correct'], total=d['scorable'], logical_caps=d['logical_caps'],
            source=str(p1), source_locator='/counts/'+key))
    for key, name in [('olmo_gsm_zero', 'OLMo-2-0425-1B 0-shot'),
                      ('olmo_gsm_four', 'OLMo-2-0425-1B 4-shot')]:
        d = read(old_gsm)['olmo_p3']['summaries'][key]
        baselines.append(dict(task='GSM8K', endpoint=name, engine='vLLM0.11',
            correct=d['correct'], total=d['total'], logical_caps=d['logical_stops']['length_cap'],
            source=str(old_gsm), source_locator='/olmo_p3/summaries/'+key))
    for row in baselines:
        trace('T3_BASELINE_LADDER.csv', row['task']+'/'+row['endpoint'],
              row['source'], row['source_locator'])
    table('T3_BASELINE_LADDER.csv', baselines)
    # The complete C6 table includes the already audited Qwen GSM0-shot650 baseline.
    copy(P/'c6_analysis_v1/CELLS.csv', 'T3_CUE_COMPLETE_CELLS.csv')
    copy(P/'c6_analysis_v1/PAIRED.csv', 'T3_CUE_ALL8_PAIRED.csv')
    historical = Path('reports/exploratory_20261014/completed_endpoints_v1/RESULTS.json')
    hist = read(historical)['rows']
    historical_rows = [
        dict(role=x['role'], engine='historical_HF_not_current_vLLM',
             correct=x['correct'], total=x['n'], caps=x['length_caps'],
             used_in_P010_effect=False) for x in hist]
    base_source = Path('reports/p008_20261013/registered_primary_results_v1/ALL_CELLS.csv')
    base = [x for x in rows(base_source) if x['logical_run_id'] == 'base']
    assert len(base) == 1
    historical_rows.insert(0, dict(role='base_0shot', engine='historical_HF_not_current_vLLM',
        correct=int(base[0]['correct']), total=int(base[0]['n']),
        caps=int(base[0]['length_caps']), used_in_P010_effect=False))
    table('T3_HF_HISTORICAL_ONLY.csv', historical_rows)
    trace('T3_HF_HISTORICAL_ONLY.csv', 'base_0shot', base_source, 'logical_run_id=base')
    for row in hist:
        trace('T3_HF_HISTORICAL_ONLY.csv', row['role'], historical, '/rows role='+row['role'])
    dump(OUT/'T3_CLAUDE_OWNED_COMPONENT.json', dict(
        component='Z1', owner='Claude', numeric_values_in_this_packet=None,
        actual_labels_or_report_read_by_Codex=False, relabelled_by_Codex=False,
        author_blind12_check_not_asserted_complete=True,
        integration='Claude supplies its separately reviewed component; missing is not zero.'))
    copies = {
        P/'c9_complete_students_v1/T4_COMPLETE_MATH_CELLS.csv':'T4_E1_E1D_SEED17.csv',
        P/'c9_complete_students_v1/MATH_GREEDY_PAIRED.csv':'T4_SEED17_PRIMARY_PAIRED.csv',
        P/'c9_complete_students_v1/MATH_SAMPLED_PAIRED.csv':'T4_SEED17_SECONDARY_PAIRED.csv',
        P/'c9_complete_students_v1/GSM_E4_PAIRED.csv':'T4_E4_PAIRED.csv',
        P/'seed29_analysis_v1/CELLS.csv':'T4_SEED29_CELLS.csv',
        P/'seed29_analysis_v1/GREEDY_PAIRED.csv':'T4_SEED29_PRIMARY_PAIRED.csv',
        P/'seed29_analysis_v1/SAMPLED_PAIRED.csv':'T4_SEED29_SECONDARY_PAIRED.csv',
        P/'e9_analysis_v1/CELLS.csv':'T4_E9_CELLS.csv',
        P/'e9_analysis_v1/PAIRED.csv':'T4_E9_PAIRED.csv',
    }
    for path, name in copies.items():
        copy(path, name)
    e4path = P/'e4_complete_results_v1/SUMMARY.json'
    e4 = read(e4path)['cells']
    assert len(e4) == 2
    assert all(abs(d['correct']/1319-d['accuracy']) < 1e-12 for d in e4.values())
    table('T4_E4_CELLS.csv', [
        dict(run=key, task='GSM8K', correct=d['correct'], total=1319,
             accuracy=d['accuracy'], logical_caps=d['logical_stops']['length_cap'],
             training_updates=d['original_training_updates'], targets=d['original_training_targets'],
             failed_training_parent_retained=d['original_failed_parent_remains_failed'])
        for key, d in sorted(e4.items())])
    for key in e4:
        trace('T4_E4_CELLS.csv', key, e4path, '/cells/'+key,
              'copy; total1319 bound by original endpoint protocol and correct/accuracy')
    copy(P/'e3_complete_results_v1/METRICS.json', 'E3_ORIGINAL_DESCRIPTIVE_METRICS.json')
    dump(OUT/'SCOPE_AND_STATUS.json', dict(utc=utc(), exploratory=True, preregistered=False,
        snapshot_before_scheduled_cutoff=True, scheduled_cutoff_utc='2026-10-21T19:00:00Z',
        source_packets_immutable=True, new_model_calls=0, new_decodes=0, new_scores=0,
        new_bootstraps=0, old_figure_renders=0, Z1_access=False,
        E5='retired_unattempted_by_delegated_D2; E9_original_OLMo_transfer_shown',
        cancelled_K4_K8='four T7/T72 cells retained as unavailable; no zero fill',
        E3_actual_A3='pending', C6_actual_A3='pending', number_trace_A5='pending',
        limits='Pointwise conditional intervals; no familywise, equivalence or training-seed-population claim.'))
    copy(Path(__file__), 'assembler.py')
    dump(OUT/'NUMBER_TRACE.json', TRACES)
    dump(OUT/'SOURCE_BINDING.json', SOURCES)
    (OUT/'README.md').write_text(
        '# Z2 deterministic technical tables and number trace — A5 pending\n\n'
        'This is an early dated technical assembly for author and auditor verification, '
        'not the Oct21 12:00PDT freeze and not interpretive course-report/slides prose. '
        'Every input is an existing immutable table, summary, figure or necessary saved billing snapshot. '
        'No inference, token decoding, scoring, checkpoint loading, bootstrap or figure rendering ran.\n\n'
        '- T1: composition, coverage, requested K, actual N, underfill, K1 retries and shared-pool attempts/usage. '
        'P_open counts the examined prefix for E1d and supplied question roster otherwise; P_cov is saved coverage. '
        'K_observed_mean is N/P_cov, not the requested quota. Shared-pool counts and charges must not be summed across cells. '
        'Cancelled candidates are explicitly marked and were not trained.\n'
        '- T2: all12 saved P008 depth-minus-breadth differences, including observed-draw averages; '
        'the original31-row table is supplied too. No old interval was recomputed.\n'
        '- T3: frozen vLLM baseline ladder and all cue results. Historical HF endpoints are isolated and '
        'never used for P010 effects. Claude owns Z1; its labels/results are not read or filled in here.\n'
        '- T4: original seed17/seed29, E1d, E4 and delegated E9 tables; E5 remained unattempted. '
        'All original comparisons, including unfavorable ones, remain available.\n'
        '- [F1/F2](FIGURES.md): byte-identical prior figures with caption and provenance. '
        'F1 is explicitly labelled “不是受控的数据规模曲线”. No old render was repeated.\n\n'
        'NUMBER_TRACE.json maps table rows or complete copied files to exact source SHA and selectors. '
        'Original packet pending/null fields are historical and never rewritten; current acceptances live '
        'in dated review packets. E3/C6 actual A3 and this assembly A5 remain pending at creation. '
        'The current billing projection is delayed observed usage, not a final invoice or balance; '
        'failed/setup/build/storage/lag are not assumed free. No per-cell cost allocation is invented.\n')
    dump(OUT/'MANIFEST.json', manifest(OUT))
    dump(R/'Z2_NUMBER_TRACE_ASSEMBLY_DONE.json', dict(utc=utc(), packet=str(OUT),
        manifest_sha256=sha(OUT/'MANIFEST.json'), number_trace_rows=len(TRACES),
        new_science=0, A5_pending=True))
    print(json.dumps(dict(packet=str(OUT), trace_rows=len(TRACES), sources=len(SOURCES))))


if __name__ == '__main__':
    main()
