"""Report only the four independently closed seed17 models; no dispatch."""
import datetime
import json
import shutil
from pathlib import Path

import numpy as np
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from scripts.summarize_token_students import exposure_summary
from src.sft_data import read_jsonl

r = Path(__file__).resolve().parent
out = Path('reports/p007_audit/token_seed17_two_prices_v1')
assert not out.exists()
spec = read('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
cells = ('breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4')
models, predictions, receipts, sources = {}, {}, {}, {}
for cell in cells:
    run = cell + '_s17'
    ep = r/'students'/f'{run}_run_r1/result.json'
    ap = r/'student_exports'/run/'LOCAL_ORACLE_AUDIT.json'
    pp = r/'student_closeouts'/run/'provider.json'
    e, a, p = read(ep), read(ap), read(pp)
    z = e['result']
    v = read(r/'student_exports'/run/'LOCAL_VERIFICATION.json')
    assert a['run_id'] == run and a['campaign'] == spec['campaign_id']
    assert a['updates_verified'] == 256 and a['supervised_tokens_verified'] == 524287
    assert a['outputs_independently_rescored'] == 1319
    assert a['correct'] == z['endpoint']['correct']
    assert a['artifact_digest'] == e['receipt']['evidence_sha256'] == digest(e['artifact_manifest'])
    assert a['input_sha256'] == spec['input_sha256']
    assert p['app']['state'] == 'stopped' and not p['containers']
    assert e['receipt']['status'] == 'completed'
    assert v['files_verified'] == 861 and v['full_checkpoint_steps'] == [256]
    q = z['endpoint']['question_correct']
    assert len(q) == 1319 and all(type(x) is bool for x in q.values())
    assert sum(q.values()) == a['correct']
    inputs = r/'student_preparation_r2/inputs'
    exposure = exposure_summary(read_jsonl(inputs/f'{cell}_train.jsonl'), read(inputs/f'{cell}_seed17.json'))
    predictions[cell], receipts[cell] = q, e['receipt']
    sources[cell] = dict(source_commit=read(ep.parent/'intent.json')['release']['commit'],
                        oracle_sha256=sha(ap), envelope_sha256=sha(ep), provider_sha256=sha(pp))
    models[cell] = dict(run_id=run, seed=17, correct=a['correct'], n=1319,
        accuracy=a['correct']/1319, updates=256, supervised_targets=524287,
        state_sha256=a['state_sha256'], artifact_digest=a['artifact_digest'],
        stop_diagnostics=a['endpoint_stop_diagnostics'], training_exposure=exposure,
        train_seconds=z['train_seconds'], wall_seconds=z['wall_seconds'],
        runtime_rate_estimate_usd=z['runtime_rate_estimate_usd'],
        provider_stopped=True, containers=0, procurement=spec['selection'][cell])
ids = sorted(predictions[cells[0]])
assert all(sorted(x) == ids for x in predictions.values())
paired = [dict(problem_id=i, **{c:predictions[c][i] for c in cells}) for i in ids]
arr = np.asarray([[predictions[c][i] for c in cells] for i in ids], dtype=np.int8)
d0, d4 = arr[:,1]-arr[:,0], arr[:,3]-arr[:,2]
vectors = {'p0_depth_minus_breadth':d0, 'p4_depth_minus_breadth':d4,
           'price_interaction_p4_minus_p0':d4-d0}
idx = np.random.default_rng(20261013).integers(0,1319,(10000,1319))
contrasts = {}
for name, x in vectors.items():
    interval = np.quantile(x[idx].mean(axis=1)*100, [.025,.975]).tolist()
    contrasts[name] = dict(difference_pp=float(x.mean()*100),
                          conditional_question_bootstrap_95_pp=interval)
discordances = {p:dict(breadth_only=int((x==-1).sum()),depth_only=int((x==1).sum()))
                for p,x in [('p0',d0),('p4',d4)]}
assert np.isclose(contrasts['price_interaction_p4_minus_p0']['difference_pp'],
                  contrasts['p4_depth_minus_breadth']['difference_pp']-
                  contrasts['p0_depth_minus_breadth']['difference_pp'])
billing = read(sorted((r/'billing').glob('*.json'))[-1]); billing.pop('report',None)
limits = [
    'Only seed17 is complete at both prices; four seed23 runs and the final cloud audit remain pending.',
    'Each cell has one saved random teacher trace. A price contrast is not a clean causal price effect or procurement replication.',
    'The hypothetical token cap is common, not equal realized spending or real API dollars; unused fractions are6.14%,6.88%,12.26%,10.90%.',
    'Fixed supervised targets and updates include unequal repetition; no isolated reasoning-diversity or repetition-damage mechanism.',
    'Shared-question bootstrap is conditional on these four models and traces, not training-seed or procurement uncertainty.',
    'All512-token length caps remain incorrect in the full1319 denominator; frozen E2 parser cases are not selectively repaired.',
    'Official test was researcher-observed in September; not a fresh uncontaminated test.',
    'Old time-priced operational pilots stay separate and are not pooled.',
    'Interaction alone does not establish a winner; non-significance is not equivalence.'
]
summary = dict(schema='p007b_token_seed17_two_prices_v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    campaign=spec['campaign_id'],seed=17,models=models,sources=sources,contrasts=contrasts,
    paired_disagreements=discordances,updates_verified=1024,supervised_targets_verified=2097148,
    raw_outputs_independently_rescored=5276,unknown_endpoint_outputs=0,full_states_verified=4,
    billing=billing,bootstrap=dict(replicates=10000,seed=20261013,unit='shared paired question across four fixed seed17 models'),
    external_claude_review='This new two-price packet is pending; earlier p0-only verdict is retained at its reviewed version.',
    remaining_frozen_student_runs=4,final_cloud_audit='pending',limits=limits)
out.mkdir()
dump(out/'summary.json',summary); dump(out/'paired_question_scores.json',paired); dump(out/'receipts.json',receipts)
for cell in cells:
    run = cell+'_s17'
    shutil.copyfile(r/'student_exports'/run/'LOCAL_ORACLE_AUDIT.json',out/f'{cell}_local_audit.json')
    shutil.copyfile(r/'student_exports'/run/'artifact_manifest.json',out/f'{cell}_artifact_manifest.json')
shutil.copyfile(__file__,out/'report_builder.py')
(out/'REVIEW_REQUEST.md').write_text('''# Token tariff: two prices, seed17, provisional results

Pin the packet to its publication commit. Recompute the four accuracies,
within-price depth-minus-breadth differences, and their price interaction from
paired_question_scores.json. The10,000 shared-question bootstrap uses seed20261013
and conditions on four fixed models and teacher traces; seed23 is still pending.
The report builder is preserved for reproducibility, with large local artifacts
required for its full input gates. Every published local audit verifies1319 raw
outputs,256 updates,524287 targets, and the complete terminal state.

Full raw token arrays and weights remain under local token_policy_r1/student_exports;
public manifests list their hashes. The compact packet alone does not independently
decode all arrays or reconstruct weights. Previous p0-only Claude PASS-WITH-NOTES
does not cover these new high-price outcomes or the new interaction.

Report every truncation count and retain all1319 questions. Keep frozen primary
scores, including disclosed E2 formatting errors. No selective rescoring is used.
Common cap differs from equal realized spending; prices are hypothetical token
units, not API dollars. Distinct procurement traces, unequal exposure and benchmark
history constrain inference. This is a provisional seed17 result, not the final
eight-run result or a general dollar-optimal recommendation.
''')
dump(out/'manifest.json',dict(schema='audit_packet_manifest_v1',files=manifest(out),
    scope='Four seed17 cells,5276 complete endpoint outputs, four full-state/dose local audits; no seed23 or final cloud audit.',
    external_review='pending for this new packet'))
dump('reports/sft_allocation_midpoint_20261011/P007B_TOKEN_SEED17_RESULTS.json',summary)
dump(r/'HIGH_PRICE_PAIR_CLOSED.json',dict(utc=summary['utc'],both_passed=True,both_provider_stopped=True,
    summary_sha256=sha(out/'summary.json'),oracles={c:sources[c]['oracle_sha256'] for c in ('breadth_p4','depth_p4')},
    packet_manifest_sha256=sha(out/'manifest.json')))
print(json.dumps(dict(models={c:dict(correct=m['correct'],n=m['n'],cap=m['stop_diagnostics']['length_cap_outputs']) for c,m in models.items()},
    contrasts=contrasts,paired_disagreements=discordances,billing=billing)))
