"""New CPU-only provenance/admission tests; no old oracle or remote model calls."""
import ast
import copy
import json
from pathlib import Path
import unittest
from experiments.sft_allocation_p008.completion_queue import make_plan, transfer_record, CAMPAIGN as STUDENT_CAMPAIGN
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.contract import DEADLINE_EPOCH, run_roster
from experiments.sft_allocation_p008.audit_lineage_binding import (
    CONFIG, PARENT_LABEL, PARENT_ARCHIVE, CHILD_RUN, PARENT_CAMPAIGN, CHILD_CAMPAIGN,
    CONTAINERS, physical_roster, source_key, validate, validate_label, validate_all_labels, evidence_file_hash)


def fixture():
    source = {'new_cpu.py': 'a' * 64}
    packet=Path('reports/p008_20261013/student_completion_queue_v1')
    original=json.loads((packet/'ORIGINAL_PLAN.json').read_text())
    owner=json.loads((packet/'OWNER_COMPLETION.json').read_text())
    plan=make_plan(original, owner, original['created_epoch']+100)
    files = {n: dict(bytes=10, sha256='b' * 64) for n in CONTAINERS}
    labels = {}
    for name in physical_roster():
        campaign = CHILD_CAMPAIGN if name == CHILD_RUN else PARENT_CAMPAIGN if name in ('pool_d1',PARENT_LABEL) else STUDENT_CAMPAIGN
        run = 'pool_d2' if name == PARENT_LABEL else name
        claim = dict(intent_sha256='c' * 64, plan_sha256=digest(original if campaign==PARENT_CAMPAIGN else plan), run_id=run)
        terminal = dict(status='failed' if name == PARENT_LABEL else 'completed',
                        claim_sha256=digest(claim), evidence_sha256=digest(files))
        role = 'pool_continuation' if name == CHILD_RUN else 'pool' if name.startswith('pool_') else 'base' if name == 'base' else 'main'
        cfg = dict(run_id=run, role=role)
        label = dict(campaign=campaign, run_id=run, config=cfg, claim=claim)
        if name == PARENT_LABEL:
            rec = dict(parent_terminal=terminal, parent_claim=claim, passed=True,
                       physical_raw_unknown=0)
            label.update(terminal=terminal, reconciliation=rec, archive_files=copy.deepcopy(files))
            label['reconciliation_json'] = json.dumps(rec, indent=2) + '\n'
        else:
            oracle = dict(passed=True, manifest_digest=digest(files))
            label.update(envelope=dict(receipt=terminal, artifact_manifest=copy.deepcopy(files)), local_oracle=oracle)
            label['local_oracle_json'] = json.dumps(oracle, indent=2) + '\n'
        labels[name] = label
    parent, child, d1 = labels[PARENT_LABEL], labels[CHILD_RUN], labels['pool_d1']
    merged = dict(passed=True, parent_plus_child_redecoded=True, all_wallets_replayed=True,
        parent_status='failed', child_status='completed', parent_physical_outputs=3992,
        child_physical_outputs=28, physical_outputs=4020,
        parent_terminal=parent['terminal'], child_terminal=child['envelope']['receipt'],
        parent_reconciliation_sha256=evidence_file_hash(parent['reconciliation_json'], parent['reconciliation']),
        manifest_digest=digest(files))
    child['local_oracle'] = merged
    child['local_oracle_json'] = json.dumps(merged, indent=2) + '\n'
    def origin(label):
        return dict(campaign=label['campaign'], run_id=label['run_id'], claim=label['claim'],
                    terminal=label.get('terminal', label.get('envelope', {}).get('receipt')))
    hashes = {'1': evidence_file_hash(d1['local_oracle_json'], d1['local_oracle']),
              '2': evidence_file_hash(child['local_oracle_json'], merged)}
    lineages = {'1': dict(kind='completed_original', original=origin(d1), local_oracle_sha256=hashes['1']),
        '2': dict(kind='failed_parent_completed_child', parent=origin(parent), child=origin(child),
                  merged_oracle_sha256=hashes['2'], merged_proof=merged,
                  parent_reconciliation_sha256=evidence_file_hash(parent['reconciliation_json'], parent['reconciliation']))}
    meta = {}
    for n, l in labels.items():
        meta[n] = dict(**origin(l), provider_stopped=True, owned_containers=0,
                       app_id='app-' + n, label_sha256=digest(l))
    im = {n + '.json': dict(bytes=10, sha256='d' * 64) for n in labels}
    im.update({PARENT_ARCHIVE + '/' + n: x for n, x in files.items()})
    binding = dict(plan=plan, original_plan=original,student_completion_owner=owner,student_slot_transfer=transfer_record(plan,original,owner), config=copy.deepcopy(CONFIG), labels=meta,
        config_sha256={n: digest(l['config']) for n, l in labels.items()},
        input_manifest=dict(files=im), pool_lineages=lineages, draw_oracle_sha256=hashes,
        code_review=dict(scope='p008_cpu_lineage_integrity_code', decision='PASS',
            source_files=source, target_commit='1' * 40, report_sha256='2' * 64),
        io_gate=dict(passed=True, source_files=source, labels_sha256=digest(meta),
                     forecast_seconds=1000, complete_dispatch_window_seconds=4000,
                     actual_transfer_bytes=660, actual_state_bytes=0, actual_compact_bytes=220))
    binding['numeric_review'] = dict(scope='p008_cpu_lineage_integrity_numeric', decision='PASS',
        io_gate_sha256=digest(binding['io_gate']), target_commit='3' * 40, report_sha256='4' * 64)
    return binding, labels, source


def release_for(binding, source):
    spec = dict(original_plan_sha256=digest(binding['original_plan']),student_plan_sha256=digest(binding['plan']),
        status='admitted_after_all_local_oracles_and_resource_release',
        binding_sha256=digest(binding), source_files=source)
    return spec, dict(source_files=source, spec_sha256=digest(spec))


class LineageAdmission(unittest.TestCase):
    def setUp(self):
        self.binding, self.labels, self.source = fixture()

    def admit(self):
        s, r = release_for(self.binding, self.source)
        return validate(self.binding, s, r)

    def reject(self):
        with self.assertRaises(ValueError):
            self.admit()

    def test_complete_22_sources_for_21_logical_runs(self):
        self.assertEqual(len(self.admit()), 22)
        self.assertEqual(validate_all_labels(self.binding, self.labels), self.labels)

    def test_dropped_failed_parent_rejected_even_after_spec_rehash(self):
        del self.binding['labels'][PARENT_LABEL]
        self.reject()

    def test_parent_relabel_completed_rejected(self):
        self.binding['labels'][PARENT_LABEL]['terminal']['status'] = 'completed'
        self.reject()

    def test_child_foreign_campaign_rejected(self):
        self.binding['labels'][CHILD_RUN]['campaign'] = PARENT_CAMPAIGN
        self.reject()

    def test_claim_changed_rejected(self):
        self.binding['labels'][CHILD_RUN]['claim']['intent_sha256'] = 'e' * 64
        self.reject()

    def test_resources_still_active_rejected(self):
        self.binding['labels']['base']['owned_containers'] = 1
        self.reject()

    def test_missing_parent_archive_rejected(self):
        del self.binding['input_manifest']['files'][PARENT_ARCHIVE + '/compact_evidence.tar.gz']
        self.reject()

    def test_old_code_review_does_not_cover_new_entry(self):
        self.binding['code_review']['scope'] = 'p008_cpu_integrity_code'
        self.reject()

    def test_exact_authorized_completion_envelope_required(self):
        self.binding['plan']['deadline_epoch'] += 3600
        self.reject()

    def test_no_extra_cpu_budget(self):
        self.binding['plan']['slots']['audit']['reserved_cents'] += 1
        self.reject()

    def test_infinite_or_overlong_io_estimate_rejected(self):
        for value in (float('inf'), 3181):
            with self.subTest(value=value):
                b = copy.deepcopy(self.binding)
                b['io_gate']['forecast_seconds'] = value
                if value == 3181:
                    b['numeric_review']['io_gate_sha256'] = digest(b['io_gate'])
                with self.assertRaises(ValueError):
                    s, r = release_for(b, self.source)
                    validate(b, s, r)

    def test_code_pass_cannot_replace_numeric_review(self):
        self.binding['numeric_review']['scope'] = 'p008_cpu_lineage_integrity_code'
        self.reject()

    def test_merged_oracle_replacement_rejected_after_label_rehash(self):
        l = self.labels[CHILD_RUN]
        l['local_oracle'] = copy.deepcopy(l['local_oracle'])
        l['local_oracle']['parent_physical_outputs'] = 0
        self.binding['labels'][CHILD_RUN]['label_sha256'] = digest(l)
        with self.assertRaises(ValueError):
            validate_label(self.binding, CHILD_RUN, l)

    def test_omitted_transfer_bytes_rejected(self):
        self.binding['io_gate']['actual_transfer_bytes'] -= 30
        with self.assertRaises(ValueError):
            validate_all_labels(self.binding, self.labels)

    def test_failed_parent_archive_swap_rejected(self):
        l = self.labels[PARENT_LABEL]
        l['archive_files']['compact_evidence.tar.gz']['sha256'] = 'e' * 64
        self.binding['labels'][PARENT_LABEL]['label_sha256'] = digest(l)
        with self.assertRaises(ValueError):
            validate_label(self.binding, PARENT_LABEL, l)

    def test_original_file_sha_is_not_canonical_object_digest(self):
        label = self.labels[CHILD_RUN]
        self.assertNotEqual(evidence_file_hash(label['local_oracle_json'], label['local_oracle']),
                            digest(label['local_oracle']))
        self.assertEqual(validate_label(self.binding, CHILD_RUN, label), label)

    def test_original_json_bytes_and_object_disagreement_rejected(self):
        label = self.labels[CHILD_RUN]
        label['local_oracle_json'] = '{}\n'
        self.binding['labels'][CHILD_RUN]['label_sha256'] = digest(label)
        with self.assertRaises(ValueError):
            validate_label(self.binding, CHILD_RUN, label)

    def test_other_slot_budget_cannot_change_frozen_plan(self):
        self.binding['plan']['slots']['base']['reserved_cents'] += 1
        self.reject()

    def test_source_keys_keep_failed_parent_campaign(self):
        self.assertEqual(source_key(self.binding['labels'][PARENT_LABEL], 'terminal'),
                         'midpoint/' + PARENT_CAMPAIGN + '/terminal/pool_d2')
        self.assertEqual(source_key(self.binding['labels'][CHILD_RUN], 'terminal'),
                         'midpoint/' + CHILD_CAMPAIGN + '/terminal/' + CHILD_RUN)

    def test_student_labels_must_use_successor_campaign(self):
        self.binding['labels']['base']['campaign']=PARENT_CAMPAIGN
        self.reject()

    def test_student_claim_bound_to_actual_successor_plan(self):
        x=self.binding['labels']['base'];x['claim']['plan_sha256']=digest(self.binding['original_plan'])
        x['terminal']['claim_sha256']=digest(x['claim'])
        self.reject()

    def test_owner_budget_or_transfer_cannot_change(self):
        self.binding['student_slot_transfer']['additional_budget_cents']=1
        self.reject()

    def test_entrypoint_static_finite_contract(self):
        tree = ast.parse(Path('experiments/sft_allocation_p008/modal_audit_lineage.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'work')
        decorator = fn.decorator_list[0]
        kw = {x.arg: ast.literal_eval(x.value) for x in decorator.keywords
              if x.arg not in ('image', 'volumes')}
        self.assertNotIn('gpu', kw)
        self.assertEqual((kw['timeout'], kw['startup_timeout'], kw['retries'], kw['max_containers']),
                         (3500, 600, 0, 1))
        self.assertEqual((kw['cpu'], kw['memory'], kw['min_containers'], kw['single_use_containers']),
                         ((4, 4), (16384, 16384), 0, True))
        body = ast.unparse(fn)
        self.assertLess(body.index('timer.start()'), body.index('import torch'))
        self.assertLess(body.index('timer.start()'), body.index('roster = validate'))
        self.assertIn('max_workers=2', body)
        local = ast.unparse(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main'))
        self.assertEqual(local.count('window()'), 3)  # definition + entry + post-provider check
        self.assertEqual(local.count('work.spawn('), 1)


if __name__ == '__main__':
    unittest.main()
