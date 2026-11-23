"""Add settled billing and recovery provenance to the completed CPU packet."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
ROOT = Path('reports/p012_20261111')
PACKET = ROOT/'amendment10_combined_training_review_v1'
read = lambda p:json.loads(Path(p).read_text())
sha = lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2,ensure_ascii=False); f.write('\n')


def main():
    assert read(HERE/'STATUS.json')['status'] == 'combined_review_ready'
    state = read('.local/p012_20261111/amendment10_v1/RECOVERY_QUEUE.json')
    assert state['status'] == 'generation_complete_data_and_training_review_required'
    assert state['active_batch'] is None and state['qualified_rows'] >= 4300
    manifest = read(PACKET/'INPUT_MANIFEST.json')
    assert manifest['qualified_pool'] == state['qualified_rows']
    for path,h in read(ROOT/'amendment10_completion_preparation_v1/SOURCES.json').items():
        assert sha(path) == h
    settlement = read(HERE/'BILLING_SETTLEMENT.json')
    settled = {x['run_id']:x['settled_API_cost_usd'] for x in settlement['sessions']}
    batch_costs=[]
    for batch in state['completed_batches']:
        name=batch['run_id']
        batch_costs.append({'run_id':name,
            'cost_usd':settled.get(name,batch['token_cost_usd']),
            'basis':'API completed invoice-priced bucket' if name in settled else 'completed raw-token uncached upper bound pending API settlement'})
    S1 = sum(x['cost_usd'] for x in batch_costs)+settlement['failed_attempt_settled_cost_usd']
    initial=read(PACKET/'BUDGET.json')
    total=S1+initial['baselines_forecast_usd']+initial['training_and_evaluation_forecast_usd']
    budget={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'authority_commit':state['authority_commit'],'length_review_commit':state['length_review_commit'],
        'cap_authority_commit':state['cap_authority_commit'],'S1_completed_batches':batch_costs,
        'failed_attempt_settled_cost_usd':settlement['failed_attempt_settled_cost_usd'],
        'failed_attempt_remaining_reserve_usd':0,
        'failed_attempt_released_reserve_usd':settlement['failed_reserve_released_usd'],
        'S1_accounted_usd':S1,'S1_subcap_usd':100,
        'baselines_forecast_usd':initial['baselines_forecast_usd'],'baselines_subcap_usd':6,
        'training_and_evaluation_forecast_usd':initial['training_and_evaluation_forecast_usd'],
        'training_and_evaluation_subcap_usd':125,'whole_phase_forecast_usd':total,'overall_hard_cap_usd':200,
        'all_financial_gates_pass':S1<=100 and initial['baselines_forecast_usd']<=6 and initial['training_and_evaluation_forecast_usd']<=125 and total<=200,
        'admitted':False,'next_gate':'combined data/source review, then live financial admission; update forecasts after baseline/L measurements',
        'settlement_receipt':{'path':str(HERE/'BILLING_SETTLEMENT.json'),'sha256':sha(HERE/'BILLING_SETTLEMENT.json')},
        'original_conservative_forecast':{'path':str(PACKET/'BUDGET.json'),'sha256':sha(PACKET/'BUDGET.json')},
        'settings_changed':False,'training_started':False}
    write(PACKET/'BUDGET_SETTLED.json',budget)
    bindings=[]
    for path in sorted(HERE.iterdir()):
        if path.is_file() and path.suffix in ['.py','.json','.md']:
            bindings.append({'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size})
    write(PACKET/'RECOVERY_INPUT_MANIFEST.json',{'utc':budget['utc'],'bindings':bindings,
        'recovery_authority':'Owner 2026-11-22 instruction','model_or_scoring_source_changed':False,
        'batch09_previous_paid_calls':0,'normal_git_push_verified':True,'force_push':False,
        'frozen_previous_outputs_changed':False,'current_budget':'BUDGET_SETTLED.json',
        'diagnostic_table':str(ROOT/'diagnostics_20261122_v1/TABLE.md'),
        'diagnostic_table_sha256':sha(ROOT/'diagnostics_20261122_v1/TABLE.md')})
    report=PACKET/'README.md'
    text=report.read_text()
    text=text.replace('Failed-attempt evidence and reserve remain preserved.',
        'Failed-attempt evidence remains preserved; its invoice-priced API settlement is recorded in BUDGET_SETTLED.json.')
    original_start=text.index('Budget: S1 accounted plus retained failed reserve')
    original_end=text.index('\n\nINPUT_MANIFEST',original_start)
    text=text[:original_start]+f'''Current budget after API settlement: S1 ${S1:.4f}/100 (including failed attempt ${settlement['failed_attempt_settled_cost_usd']:.4f}); baselines forecast ${initial['baselines_forecast_usd']:.4f}/6; twelve training/evaluations forecast ${initial['training_and_evaluation_forecast_usd']:.4f}/125; whole phase ${total:.4f}/200. BUDGET_SETTLED.json is the current financial receipt; BUDGET.json preserves the earlier conservative forecast with the old failed reserve. All financial gates pass: {budget['all_financial_gates_pass']}. These forecasts do not authorize training; combined review and live admission remain required.

Recovery: batch09 admission publication failed due to a GitHub connection reset. Fetch and normal push confirmed no divergence; API/session and local evidence showed batch09 had not started. Its original request was executed once under the owner's2026-11-22 instruction. The existing paid-generation, qualification and preparation functions remain unchanged. RECOVERY_INPUT_MANIFEST.json binds the full recovery and billing receipts. No account settings changed.''' +text[original_end:]
    report.write_text(text)
    write(HERE/'DELIVERY.json',{'utc':budget['utc'],'generation_complete':True,'qualified_pool':state['qualified_rows'],
        'outputs':manifest['outputs'],'batch_count':len(state['completed_batches']),
        'combined_review_packet':str(report),'current_budget':str(PACKET/'BUDGET_SETTLED.json'),
        'diagnostic_endpoints':113,'diagnostic_outputs':299968,'training_started':False,
        'all_financial_gates_pass':budget['all_financial_gates_pass']})
    sys.path.insert(0,'.local/p012_20261111/amendment7_v1')
    from a7_ops import publish
    commit=publish([PACKET,HERE/'DELIVERY.json',HERE/'finalize_delivery.py'],
        'P012 A10: finalize full pretraining review with recovered S1 evidence and settled budget')
    print(json.dumps({'commit':commit,'qualified_pool':state['qualified_rows'],'S1_usd':S1,
        'whole_phase_forecast_usd':total,'training_and_evaluation_forecast_usd':initial['training_and_evaluation_forecast_usd'],
        'all_financial_gates_pass':budget['all_financial_gates_pass']}))


if __name__=='__main__':
    main()
