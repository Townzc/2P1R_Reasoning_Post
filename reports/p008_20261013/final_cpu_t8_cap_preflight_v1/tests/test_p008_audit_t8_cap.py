"""Synthetic cap-provenance fixtures; no cloud, tensor or raw-oracle execution."""
import ast
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.sft_allocation_midpoint.common import digest, read, sha
from experiments.sft_allocation_p008.audit_t8_cap_records import (
    CAP_SPEC, OLD_PROPOSAL, KEY, CAMPAIGN, amendment_record, validate_cap_inputs,
    validate_cap_numeric, validate_cap_label, require_remote_cap_records,
    verify_packed_run)


def fixture():
    spec = read('reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json')
    sources = read('reports/p008_20261013/student_t8_cap_9600_v1/SOURCE_BUNDLE.json')
    binding = dict(t8_cap_spec=spec, t8_runtime_source_files=sources, labels={},
                   t8_cap_ledger_records={KEY:amendment_record(spec)})
    labels = {}
    for name in spec['runs']:
        cfg = spec['configs'][name]
        ledger_intent = dict(run_id=name, config_sha256=digest(cfg),
            source_sha256=digest(sources), data_sha256=cfg['input_sha256'])
        claim = dict(intent_sha256=digest(ledger_intent), plan_sha256=spec['plan_sha256'],
                     claimed_epoch=1000., deadline_epoch=10630.)
        binding['labels'][name] = dict(claim=claim)
        supplement = dict(run_id=name, original_claim_sha256=digest(claim),
            amendment_sha256=digest(binding['t8_cap_ledger_records'][KEY]),
            supplement_reserved_cents=5, reservation_not_provider_expense=True)
        binding['t8_cap_ledger_records'][KEY+'/reserved/'+name] = supplement
        # These placeholders exist only in memory, never as trusted review files.
        review = dict(verdict='PASS', review_commit='a'*40, review_report_sha256='b'*64,
                      source_files=sources, spec_sha256=CAP_SPEC)
        gates = dict(runtime_review=dict(review, scope='t8-cap-9600-runtime'),
            t8_numeric_review=dict(review, scope='t8-cap-9600-numeric', passed=True,
                N2_closed=True, original_N2_passed=False, post_hoc_engineering_deviation=True,
                accepted_runs=spec['runs'], worker_caps={n:9600 for n in spec['runs']},
                proposal_digest=OLD_PROPOSAL), t8_timing_proposal=spec['original_failed_timing_proposal'])
        sent = dict(config=cfg, plan=spec['original_spec']['plan'],
            release=dict(spec_sha256=CAP_SPEC, source_files=sources, gates=gates),
            supplement=supplement, reserved_cents=1253, total_reserved_cents=1258,
            effective_worker_seconds=9600, started_epoch=999.)
        raw = json.dumps(sent, ensure_ascii=False, indent=2)+'\n'
        labels[name] = dict(config=cfg, campaign=CAMPAIGN, run_id=name, claim=claim,
            t8_operational_evidence=dict(intent_json=raw, original_ledger_intent=ledger_intent,
                amendment_record=binding['t8_cap_ledger_records'][KEY], supplement_record=supplement),
            envelope=dict(artifact_manifest={'intent.json':dict(bytes=len(raw.encode()),
                sha256=hashlib.sha256(raw.encode()).hexdigest())},
                receipt=dict(claim_sha256=digest(claim), status='completed', actual_cost_cents=1253),
                result=dict(registered_slot_reserved_usd=12.53, supplement_reserved_usd=.05,
                            reserved_cost_usd=12.58, provider_invoice_usd=None)),
            local_oracle=dict(original_N2_passed=False, post_hoc_engineering_deviation=True,
                effective_worker_seconds=9600, total_reserved_cents=1258, supplement_reserved_cents=5))
    binding['numeric_review'] = dict(t8_cap_spec_sha256=CAP_SPEC,
        t8_cap_ledger_sha256=digest(binding['t8_cap_ledger_records']),
        original_N2_passed=False, post_hoc_engineering_deviation=True)
    return binding, labels


def rewrite_intent(label, mutate):
    value=json.loads(label['t8_operational_evidence']['intent_json']);mutate(value)
    raw=json.dumps(value,ensure_ascii=False)+'\n'
    label['t8_operational_evidence']['intent_json']=raw
    label['envelope']['artifact_manifest']['intent.json']=dict(bytes=len(raw.encode()),
        sha256=hashlib.sha256(raw.encode()).hexdigest())


class CapIntegrity(unittest.TestCase):
    def test_all_eight_original_claims_and_amended_records(self):
        binding,labels=fixture();validate_cap_numeric(binding)
        for n,label in labels.items():self.assertEqual(validate_cap_label(binding,n,label),label)

    def test_partial_or_changed_supplement_roster_rejected(self):
        for mode in ('missing','extra','changed'):
            b,_=fixture();k=KEY+'/reserved/'+b['t8_cap_spec']['runs'][0]
            if mode=='missing':del b['t8_cap_ledger_records'][k]
            elif mode=='extra':b['t8_cap_ledger_records']['extra']={}
            else:b['t8_cap_ledger_records'][k]['supplement_reserved_cents']=0
            with self.assertRaises(ValueError):validate_cap_inputs(b)

    def test_rehashed_amendment_cannot_change_original_failure(self):
        b,_=fixture();b['t8_cap_spec']['original_failed_timing_proposal']['engineering_criterion_passed']=True
        with self.assertRaises(ValueError):validate_cap_inputs(b)

    def test_supplement_cannot_be_mapped_to_other_claim(self):
        b,_=fixture();n=b['t8_cap_spec']['runs'][0];b['labels'][n]['claim']['claimed_epoch']+=1
        with self.assertRaises(ValueError):validate_cap_inputs(b)

    def test_cpu_numeric_review_must_cover_actual_cap_records(self):
        for k,v in [('t8_cap_spec_sha256','c'*64),('t8_cap_ledger_sha256','d'*64),
                    ('original_N2_passed',True),('post_hoc_engineering_deviation',False)]:
            b,_=fixture();b['numeric_review'][k]=v
            with self.assertRaises(ValueError):validate_cap_numeric(b)

    def test_original_scientific_config_not_rewritten_to_9600(self):
        b,labels=fixture();n=next(iter(labels));x=copy.deepcopy(labels[n]);x['config']['max_seconds']=9600
        with self.assertRaises(ValueError):validate_cap_label(b,n,x)

    def test_intent_exact_byte_hash_not_canonical_digest(self):
        b,labels=fixture();n=next(iter(labels));x=labels[n]
        x['t8_operational_evidence']['intent_json']+=' '
        with self.assertRaises(ValueError):validate_cap_label(b,n,x)

    def test_old_numeric_or_code_only_review_rejected_after_rehash(self):
        for key in ('runtime_review','t8_numeric_review'):
            b,labels=fixture();n=next(iter(labels));x=labels[n]
            rewrite_intent(x,lambda value:value['release']['gates'][key].update(scope='old-scope'))
            with self.assertRaises(ValueError):validate_cap_label(b,n,x)

    def test_rehashed_intent_cannot_erase_failure_or_extend_cap(self):
        mutations=[lambda v:v['release']['gates']['t8_numeric_review'].update(original_N2_passed=True),
                   lambda v:v.update(effective_worker_seconds=9601),
                   lambda v:v.update(total_reserved_cents=1253)]
        for mutate in mutations:
            b,labels=fixture();n=next(iter(labels));rewrite_intent(labels[n],mutate)
            with self.assertRaises(ValueError):validate_cap_label(b,n,labels[n])

    def test_original_intent_and_claim_hash_are_required(self):
        b,labels=fixture();n=next(iter(labels));x=labels[n]
        x['t8_operational_evidence']['original_ledger_intent']['source_sha256']='f'*64
        with self.assertRaises(ValueError):validate_cap_label(b,n,x)

    def test_expense_cannot_replace_reservation(self):
        for k,v in [('provider_invoice_usd',12.58),('reserved_cost_usd',12.53)]:
            b,labels=fixture();n=next(iter(labels));labels[n]['envelope']['result'][k]=v
            with self.assertRaises(ValueError):validate_cap_label(b,n,labels[n])

    def test_local_oracle_cap_fields_required(self):
        b,labels=fixture();n=next(iter(labels));del labels[n]['local_oracle']['effective_worker_seconds']
        with self.assertRaises(ValueError):validate_cap_label(b,n,labels[n])

    def test_nont8_cannot_silently_carry_amendment(self):
        b,labels=fixture();n=next(iter(labels));x=labels[n];x['config']=dict(x['config'],training_multiple=1)
        with self.assertRaises(ValueError):validate_cap_label(b,n,x)

    def test_actual_remote_check_is_readonly_and_exact(self):
        b,_=fixture();store=copy.deepcopy(b['t8_cap_ledger_records']);original=copy.deepcopy(store)
        require_remote_cap_records(store,b);self.assertEqual(store,original)
        store[KEY]={'wrong':True}
        with self.assertRaises(ValueError):require_remote_cap_records(store,b)

    def test_actual_compact_read_cannot_substitute_different_intent(self):
        b,labels=fixture();x=next(iter(labels.values()))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'evidence').mkdir();(root/'evidence/intent.json').write_text('{}')
            with patch('experiments.sft_allocation_p008.audit_t8_cap_records.verify_original_packed_run',return_value={'passed':True}):
                with self.assertRaises(ValueError):verify_packed_run(root,root,x)

    def test_new_worker_keeps_original_cpu_limits_and_scientific_sources(self):
        p=Path('experiments/sft_allocation_p008/modal_audit_t8_cap.py');tree=ast.parse(p.read_text())
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='work')
        values={x.arg:ast.literal_eval(x.value) for x in fn.decorator_list[0].keywords if x.arg in ('cpu','memory','timeout','startup_timeout','retries','max_containers')}
        self.assertEqual(values,dict(cpu=(4,4),memory=(16384,16384),timeout=3500,startup_timeout=600,retries=0,max_containers=1))
        for file,h in read('reports/p008_20261013/student_t8_cap_9600_v1/SOURCE_BUNDLE.json').items():self.assertEqual(sha(file),h)
        self.assertEqual(p.read_text().count('call = work.spawn('),1)
        self.assertIn('require_remote_cap_records(claims, binding, check)',p.read_text())


if __name__=='__main__':unittest.main()
