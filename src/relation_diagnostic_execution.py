"""E012 CPU input binding, statistics and strict finite-dose gates."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

from scripts.audit_family_matching import verified_tokenizer
from scripts.verify_relation_cpu_audit import load_archive
from scripts.verify_relation_diagnostics import verify as verify_c016
from src.relation_engineering import SOURCES as OLD_SOURCES, provenance as old_provenance
from src.relation_diagnostics import NEW_SOURCES as C016_SOURCES
from src.relation_diagnostic_verifier import FIELDS, summarize, teacher_forced_metrics, score as score_text
from src.relation_experiment import profile
from src.sft_data import encode_row, budget_report, sha256_file

CONFIG = Path('configs/relation_diagnostics_e012/execution.json')
RELEASE = Path('configs/relation_diagnostics_e012/release.json')
C016_RELEASE = Path('configs/diagnostics/relation_c016_release.json')
SOURCES = sorted(set(OLD_SOURCES + C016_SOURCES + [str(CONFIG),str(C016_RELEASE),
    'src/relation_diagnostic_execution.py','src/relation_diagnostic_training.py',
    'scripts/run_relation_diagnostics.py','scripts/audit_relation_diagnostic_outputs.py',
    'scripts/prepare_relation_diagnostic_execution.py','tests/test_relation_diagnostic_execution.py',
    'scripts/build_registry.py','scripts/update_compute_accounting.py',
    'docs/experiments/E012_relation_diagnostic_ladder.md'] +
    [f'runs/relation_diagnostics_c016_r1/{name}.json' for name in
     ('initial','rows','assignment','schedules','budgets','audit','manifest')]))


def digest_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def provenance(include_release=False):
    return old_provenance(SOURCES + ([str(RELEASE)] if include_release else []))


def verify_source_hashes(commit, records):
    for name, expected in records.items():
        historical = subprocess.check_output(['git','show',f'{commit}:{name}'])
        if sha256_file(name) != expected or hashlib.sha256(historical).hexdigest() != expected:
            raise ValueError('Frozen execution source or historical bytes differ')


def verify_release():
    release = json.loads(RELEASE.read_text())
    if release['status'] != 'prepared_execution_not_run' or set(release['source_files_sha256']) != set(SOURCES):
        raise ValueError('Missing or changed execution release')
    if release['execution_config_sha256'] != sha256_file(CONFIG):
        raise ValueError('Execution configuration changed')
    verify_source_hashes(release['source_commit'],release['source_files_sha256'])
    return release


def load_inputs(snapshot, *, require_release=True):
    cfg = json.loads(CONFIG.read_text())
    if sha256_file(C016_RELEASE) != cfg['c016_release_sha256']:
        raise ValueError('C016 release identity changed')
    folder = Path(cfg['data_dir'])
    if sha256_file(folder/'manifest.json') != cfg['data_manifest_sha256']:
        raise ValueError('C016 input identity changed')
    release = verify_release() if require_release else None
    check = verify_c016(folder,snapshot)
    tokenizer, token_record = verified_tokenizer(Path(snapshot)); tokenizer.pad_token = tokenizer.eos_token
    model_vocab_size = json.loads((Path(snapshot)/'config.json').read_text())['vocab_size']
    known_token_ids = frozenset(tokenizer.get_vocab().values())
    if max(known_token_ids)>=model_vocab_size: raise ValueError('Tokenizer exceeds pinned model vocabulary')
    rows = load_archive(folder/'rows.json')
    schedules = json.loads((folder/'schedules.json').read_text())
    budgets = json.loads((folder/'budgets.json').read_text())
    proposal = json.loads(Path('configs/diagnostics/relation_c016_gpu_proposal.json').read_text())
    keys = ('seed','learning_rate','weight_decay','grad_clip','batch_size','microbatch_size','eval_batch_size')
    if any(cfg[k] != proposal[k] for k in keys) or cfg['arm_order'] != proposal['order']:
        raise ValueError('Execution differs from the reviewed diagnostic proposal')
    if cfg['steps'] != proposal['steps_per_arm'] or cfg['max_new_tokens_by_arm'] != proposal['max_new_tokens']:
        raise ValueError('Dose or generation cap changed')
    if (cfg['max_seconds'],cfg['guard_seconds'],cfg['maximum_phase_reservation_seconds']) != (360,15,1125):
        raise ValueError('Complete-phase caps changed')
    data = {}
    for arm in cfg['arm_order']:
        local = {**cfg,'arm':arm,'run_id':cfg['run_ids'][arm],
                 'max_new_tokens':cfg['max_new_tokens_by_arm'][arm]}
        train = [r for r in rows if r['arm']==arm and r['split']=='train']
        dev = [r for r in rows if r['arm']==arm and r['split']=='engineering_dev']
        factor = 4 if arm=='single_step' else 1
        if len(train) != factor*cfg['train_parents'] or len(dev) != factor*cfg['dev_parents']:
            raise ValueError('Wrong diagnostic population')
        encoded = [encode_row(r,tokenizer,cfg['max_length']) for r in train]
        if any(r['tokens']['n_prompt']+local['max_new_tokens']>cfg['max_length'] for r in train+dev):
            raise ValueError('Generation context cap exceeded')
        if any(r['n_supervised']>local['max_new_tokens'] for r in encoded):
            raise ValueError('Target plus EOS cannot fit decode cap')
        actual = account(train,encoded,schedules[arm],cfg['microbatch_size'])
        if actual != budgets[arm]: raise ValueError('Execution dose differs from C016')
        data[arm] = {'cfg':local,'train':train,'dev':dev,'encoded':encoded,
                     'schedule':schedules[arm],'budget':actual}
    return {'cfg':cfg,'arms':data,'tokenizer':tokenizer,'tokenizer_record':token_record,
            'model_vocab_size':model_vocab_size,'known_token_ids':known_token_ids,
            'release':release,'c016_verified':check['all_stored_audit_fields_reproduced']}


def score_tokens(row, text, ids, eos, truncated, known_token_ids):
    result = score_text(row,text,eos,truncated)
    unknown = [i for i,token in enumerate(ids) if token not in known_token_ids]
    result['unmapped_output_token_positions'] = unknown
    if unknown:
        # Padded model-vocabulary IDs can be emitted but have no tokenizer text.
        # Retain these model failures instead of silently dropping them in decode.
        result['complete_correct'] = False
        result['certificate'] = {'valid':False,'reason':'unmapped_output_token'}
    return result


def account(rows, encoded, schedule, microbatch):
    budget = budget_report(encoded,schedule,microbatch)
    parents = Counter(rows[i]['parent_world_id'] for update in schedule for i in update)
    budget.update(parent_exposures=dict(parents),independent_train_parent_count=len(parents),
                  unique_train_rows=len({i for u in schedule for i in u}),
                  supervised_field_tokens={name:sum(len(rows[i]['token_fields'][name]) for u in schedule for i in u) for name in FIELDS})
    return json.loads(json.dumps(budget))


def reference_record(row, encoded, predicted_ids, nll):
    positions = [i for i,x in enumerate(encoded['labels']) if i and x!=-100]
    return {'problem_id':row['problem_id'],'parent_world_id':row['parent_world_id'],
            'arm':row['arm'],'split':row['split'],'input_ids_sha256':digest_json(encoded['input_ids']),
            'response_sha256':encoded['response_hash'],'target_positions':positions,
            'target_ids':[encoded['labels'][i] for i in positions],
            'predicted_ids':list(predicted_ids),'token_nll':list(nll)}


def reference_statistics(record, row, encoded, vocab_size):
    expected = reference_record(row,encoded,record['predicted_ids'],record['token_nll'])
    if record != expected or len(record['target_positions']) != len(record['token_nll']) or len(record['predicted_ids']) != len(record['token_nll']):
        raise ValueError('Teacher-forced identity, token alignment or size changed')
    losses = [None]*len(encoded['input_ids']); correct = [None]*len(losses)
    for pos, target, pred, loss in zip(record['target_positions'],record['target_ids'],record['predicted_ids'],record['token_nll']):
        if type(pred) is not int or not 0<=pred<vocab_size or type(loss) not in (int,float) or not math.isfinite(loss) or loss<0:
            raise ValueError('Invalid saved teacher-forced statistics')
        # Necessary consistency of top-one correctness and full-vocabulary CE.
        if (pred!=target and loss<math.log(2)-1e-5) or (pred==target and loss>math.log(vocab_size)+1e-5):
            raise ValueError('Top-one prediction and token NLL are inconsistent')
        losses[pos] = loss; correct[pos] = pred==target
    return teacher_forced_metrics(encoded,row['token_fields'],losses,correct)


def aggregate_references(records, rows, encoded, vocab_size):
    if len(records)!=len(rows) or len(encoded)!=len(rows) or not rows:
        raise ValueError('Require all assigned training references exactly once')
    stats = [reference_statistics(rec,row,enc,vocab_size) for rec,row,enc in zip(records,rows,encoded)]
    def merge(items):
        count = sum(x['tokens'] for x in items); loss = math.fsum(x['loss_sum'] for x in items)
        correct = sum(x['correct'] for x in items)
        return {'tokens':count,'loss_sum':loss,'nll':loss/count if count else None,
                'correct':correct,'accuracy':correct/count if count else None}
    after = [[s['after_state_by_step'][j] for s in stats] for j in range(len(stats[0]['after_state_by_step']))]
    out = {'reference_count':len(rows),'parent_count':len({r['parent_world_id'] for r in rows}),
           'all_response':merge([s['all_response'] for s in stats]),
           'by_field':{k:merge([s['by_field'][k] for s in stats]) for k in FIELDS},
           'after_state_by_certificate_position':[merge(items) for items in after],
           'conditioning':'teacher_forced_gold_prefix_not_free_generation',
           'reference_distribution':'assigned_training_references_once_not_E011_four_reference_average'}
    if rows[0]['arm']=='single_step':
        out['after_state_by_original_route_position'] = [
            merge([s['by_field']['after_state'] for r,s in zip(rows,stats) if r['step_position']==j]) for j in range(4)]
    return out


def training_gate(cfg, history, throughput, train_stats, reference_stats):
    expected_rows = cfg['train_parents']*(4 if cfg['arm']=='single_step' else 1)
    nll = reference_stats['all_response']['nll']
    checks = {'complete_updates':len(history)==cfg['steps'],
        'complete_profile':throughput['profile_complete'],
        'complete_train_population':train_stats['rows']==expected_rows and train_stats['parents']==cfg['train_parents'],
        'all_train_proofs_correct':train_stats['complete_correct']==expected_rows,
        'all_train_parents_correct':train_stats['all_correct_parents']==cfg['train_parents'],
        'all_train_eos':train_stats['ended_with_eos']==expected_rows,
        'zero_train_truncation':train_stats['truncated']==0,
        'assigned_reference_nll':type(nll) in (int,float) and math.isfinite(nll) and nll<cfg['overfit_max_nll']}
    return {'passed':all(checks.values()),'checks':checks,
            'scope':'finite_engineering_gate_not_causal_localization_or_holdout_generalization'}


def result_metrics(data, history, baseline, training, dev, references, vocab_size):
    cfg = data['cfg']; throughput = profile(history,cfg)
    ref = aggregate_references(references,data['train'],data['encoded'],vocab_size)
    train_stats = summarize(data['train'],[r['score'] for r in training])
    return {'phase':'E012','arm':cfg['arm'],'steps':len(history),
        'baseline_dev':summarize(data['dev'],[r['score'] for r in baseline]),
        'train':train_stats,'dev':summarize(data['dev'],[r['score'] for r in dev]),
        'teacher_forced_train':ref,'throughput':throughput,
        'engineering_gate':training_gate(cfg,history,throughput,train_stats,ref),
        'interpretation':'observed_engineering_parents_only_no_scientific_pair'}
