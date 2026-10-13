"""New finite CPU fixtures for 24 sources; no old model/oracle replay."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import digest, dump, manifest, sha
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_p008.audit_replacement_binding import (
    CONFIG, ARCHIVES, FAILED_STUDENTS, REPLACEMENTS, REPLACEMENT_CAMPAIGN,
    STUDENT_CAMPAIGN, PARENT_LABEL, CHILD_RUN, CONTAINERS, physical_roster,
    validate, validate_all_labels, validate_label)
from experiments.sft_allocation_p008.audit_frozen_bundle import verify_packed_run
from experiments.sft_allocation_p008.evidence_bundle import pack
from experiments.sft_allocation_p008.completion_queue import transfer_record
from test_p008_audit_lineage import fixture as old_fixture, release_for
from test_p008_audit_frozen_plan import fixture as plan_fixture


def fixture():
    b, labels, sources = old_fixture()
    spec=json.loads(Path('reports/p008_20261013/student_lr_replacement_admission_v1/ADMISSION.json').read_text())
    plan=spec['original_execution_plan']
    b.update(plan=plan,config=CONFIG,replacement_spec=spec,
        student_slot_transfer=transfer_record(plan,b['original_plan'],b['student_completion_owner']))
    failed=Path('reports/p008_20261013/student_lr_failures_closed_v1')
    for n in list(labels):
        if n in ('pool_d1',PARENT_LABEL,CHILD_RUN):continue
        cfg=spec['original_spec']['configs'][n]
        label=labels[n];label['config']=cfg
        if n in FAILED_STUDENTS:
            p=spec['parents'][n]
            label.pop('envelope');label.pop('local_oracle');label.pop('local_oracle_json')
            raw=(failed/n/'LOCAL_MANIFEST.json').read_text()
            label.update(claim=p['claim'],terminal=p['terminal'],replacement_spec=spec,
                reconciliation=spec['zero_update_reconciliation'],
                reconciliation_json=(failed/'RECONCILED.json').read_text(),
                preserved_manifest=json.loads(raw),preserved_manifest_json=raw,
                archive_files={x:dict(bytes=10,sha256='b'*64) for x in CONTAINERS})
        else:
            label['claim']['plan_sha256']=digest(plan)
            label['envelope']['receipt']['claim_sha256']=digest(label['claim'])
            label['original_student_spec']=spec['original_spec']
            if n!='base':label['frozen_input_bytes']=plan_fixture(n)[0]['frozen_input_bytes']
    for physical,logical in REPLACEMENTS.items():
        cfg=spec['configs'][physical]
        files={n:dict(bytes=10,sha256='b'*64) for n in CONTAINERS}
        claim=dict(run_id=physical,plan_sha256=spec['plan_sha256'],intent_sha256='c'*64)
        receipt=dict(status='completed',claim_sha256=digest(claim),evidence_sha256=digest(files))
        oracle=dict(passed=True,artifact_digest=digest(files),logical_run_id=logical)
        labels[physical]=dict(campaign=REPLACEMENT_CAMPAIGN,run_id=physical,config=cfg,claim=claim,
            envelope=dict(receipt=receipt,artifact_manifest=files),local_oracle=oracle,
            local_oracle_json=json.dumps(oracle),original_student_spec=spec['original_spec'],
            replacement_spec=spec,frozen_input_bytes=plan_fixture(physical)[0]['frozen_input_bytes'])
    meta={}
    for n,label in labels.items():
        terminal=label['terminal'] if n in ARCHIVES else label['envelope']['receipt']
        meta[n]=dict(campaign=label['campaign'],run_id=label['run_id'],claim=label['claim'],
            terminal=terminal,provider_stopped=True,owned_containers=0,
            app_id=spec['parents'][n]['provider_app_id'] if n in FAILED_STUDENTS else 'app-'+n,
            label_sha256=digest(label))
    files={n+'.json':dict(bytes=10,sha256='d'*64) for n in labels}
    for n,folder in ARCHIVES.items():
        files.update({folder+'/'+k:v for k,v in labels[n]['archive_files'].items()})
    b.update(labels=meta,config_sha256={n:digest(l['config']) for n,l in labels.items()},input_manifest=dict(files=files))
    b['code_review']['scope']='p008_cpu_replacement_integrity_code'
    b['io_gate'].update(labels_sha256=digest(meta),actual_transfer_bytes=720,actual_compact_bytes=240)
    b['numeric_review'].update(scope='p008_cpu_replacement_integrity_numeric',io_gate_sha256=digest(b['io_gate']))
    return b,labels,sources


class Admission(unittest.TestCase):
    def setUp(self):self.b,self.labels,self.sources=fixture()
    def check(self):
        spec,release=release_for(self.b,self.sources)
        return validate(self.b,spec,release)
    def test_complete24_retains_three_failed_sources(self):
        self.assertEqual(len(self.check()),24)
        self.assertEqual(validate_all_labels(self.b,self.labels),self.labels)
        self.assertEqual(sum(x['terminal']['status']=='failed' for x in self.b['labels'].values()),3)
    def test_cannot_drop_failed_student_even_after_rehash(self):
        del self.b['labels'][sorted(FAILED_STUDENTS)[0]]
        with self.assertRaises(ValueError):self.check()
    def test_cannot_drop_replacement(self):
        del self.b['labels'][sorted(REPLACEMENTS)[0]]
        with self.assertRaises(ValueError):self.check()
    def test_cannot_relabel_old_failure(self):
        self.b['labels'][sorted(FAILED_STUDENTS)[0]]['terminal']['status']='completed'
        with self.assertRaises(ValueError):self.check()
    def test_replacement_cannot_use_old_campaign(self):
        self.b['labels'][sorted(REPLACEMENTS)[0]]['campaign']=STUDENT_CAMPAIGN
        with self.assertRaises(ValueError):self.check()
    def test_wrong_replacement_plan_rejected(self):
        n=sorted(REPLACEMENTS)[0];item=self.b['labels'][n]
        item['claim']['plan_sha256']=digest(self.b['plan']);item['terminal']['claim_sha256']=digest(item['claim'])
        with self.assertRaises(ValueError):self.check()
    def test_missing_failure_archive(self):
        self.b['input_manifest']['files'].pop(ARCHIVES[sorted(FAILED_STUDENTS)[0]]+'/bundle_receipt.json')
        with self.assertRaises(ValueError):self.check()
    def test_original_owner_spec_cannot_be_rewritten(self):
        self.b['replacement_spec']['owner']['stage_cap_cents']+=1
        with self.assertRaises(ValueError):self.check()
    def test_occupied_provider_cannot_be_omitted(self):
        self.b['labels'][sorted(REPLACEMENTS)[0]]['owned_containers']=1
        with self.assertRaises(ValueError):self.check()
    def test_old22source_review_does_not_cover_new_runtime(self):
        self.b['code_review']['scope']='p008_cpu_lineage_integrity_code'
        with self.assertRaises(ValueError):self.check()
    def test_code_review_is_not_numeric_review(self):
        self.b['numeric_review']['scope']='p008_cpu_replacement_integrity_code'
        with self.assertRaises(ValueError):self.check()
    def test_actual_bytes_must_include_replacements_and_failures(self):
        self.b['io_gate']['actual_transfer_bytes']-=10
        with self.assertRaises(ValueError):validate_all_labels(self.b,self.labels)
    def test_rehashed_changed_physical_config(self):
        n=sorted(REPLACEMENTS)[0];self.labels[n]['config']=dict(self.labels[n]['config'],logical_run_id='wrong')
        self.b['labels'][n]['label_sha256']=digest(self.labels[n]);self.b['config_sha256'][n]=digest(self.labels[n]['config'])
        with self.assertRaises(ValueError):validate_label(self.b,n,self.labels[n])
    def test_failure_preservation_bytes_cannot_change(self):
        n=sorted(FAILED_STUDENTS)[0]
        self.labels[n]['preserved_manifest']['intent.json']['sha256']='e'*64
        self.labels[n]['preserved_manifest_json']=json.dumps(self.labels[n]['preserved_manifest'])
        self.b['labels'][n]['label_sha256']=digest(self.labels[n])
        with self.assertRaises(ValueError):validate_label(self.b,n,self.labels[n])


def state_fixture(root,name,mutation=None):
    import torch
    label,recipe,frozen=plan_fixture(name)
    cfg=label['config'];u=cfg['updates'];src=root/'source';src.mkdir()
    release=dict(commit='fixture',source_files={'fixture.py':'a'*64})
    recipe['identity'].update(source_commit=release['commit'],source_sha256=digest(release['source_files']))
    scores={str(i):bool(i%2) for i in range(1319)}
    result=dict(updates=u,targets=cfg['targets'],endpoint=dict(question_correct=scores,correct=sum(scores.values())))
    if name in REPLACEMENTS:
        logical=REPLACEMENTS[name];spec=json.loads(Path('reports/p008_20261013/student_lr_replacement_admission_v1/ADMISSION.json').read_text())
        label['replacement_spec']=spec
        result.update(physical_run_id=name,logical_run_id=logical,replacement_of_failed_parent=True)
        dump(src/'replacement_lineage.json',dict(logical_run_id=logical,physical_run_id=name,
            parent=spec['parents'][logical],zero_update_reconciliation_sha256=spec['zero_update_reconciliation_sha256'],owner_sha256=digest(spec['owner'])))
    dump(src/'intent.json',dict(config=cfg,plan=dict(campaign_id='fixture'),release=release));dump(src/'result.json',result)
    dump(src/'recipe.json',recipe)
    hashes={}
    for step in ([1024,2048] if u==2048 else [256]):
        targets=cfg['targets'] if step==u else cfg['targets']//2
        state=dict(schema='complete_lora_v1',identity=recipe['identity'],step=step,cursor=step,
            supervised_tokens=targets,processed_tokens=step*3,schedule=frozen['updates'],lrs=list(frozen['lrs']),
            trainable_names=['adapter.a'],adapter={'adapter.a':torch.ones(2)},
            optimizer={'state':{0:{'step':torch.tensor(float(step)),'exp_avg':torch.zeros(2)}},'param_groups':[{'params':[0]}]},rng=ck.rng_state())
        if mutation:mutation(state)
        ck.save(src,state);hashes[str(step)]=sha(src/f'checkpoint_{step:04d}/state.pt')
        dump(src/'completed'/f'update_{step:04d}.json',dict(cumulative_targets=targets,cumulative_processed=step*3))
    pack(src);files=manifest(src);dump(src/'artifact_manifest.json',files)
    oracle=dict(passed=True,run_id=name,role=cfg['role'],updates_verified=u,targets_verified=cfg['targets'],outputs_rescored=1319,
        correct=sum(scores.values()),artifact_digest=digest(files),state_sha256=hashes[str(u)],
        forensic_checkpoints={k:dict(sha256=v) for k,v in hashes.items() if k!=str(u)})
    if name in REPLACEMENTS:oracle.update(logical_run_id=REPLACEMENTS[name],parent_status='failed',outcome_blind_zero_update_replacement=True)
    label.update(campaign='fixture',local_oracle=oracle,envelope=dict(result=result,artifact_manifest=files,
        receipt=dict(status='completed',evidence_sha256=digest(files))))
    return src,label


class FullState(unittest.TestCase):
    def run_fixture(self,name,mutation=None):
        with tempfile.TemporaryDirectory() as tmp:
            src,label=state_fixture(Path(tmp),name,mutation)
            return verify_packed_run(src,Path(tmp)/'checked',label)
    def test_original_uses_exact_frozen_lr(self):
        with patch('experiments.sft_allocation_p008.contract.lrs',side_effect=AssertionError('must not recompute')):
            self.assertTrue(self.run_fixture('d1_b1_p4_breadth_t1')['passed'])
    def test_replacement_keeps_logical_and_physical_identity(self):
        self.assertTrue(self.run_fixture('d1_b1_p0_breadth_t1_replacement_r1')['passed'])
    def test_forensic_and_terminal_fullstates(self):
        self.assertEqual(set(self.run_fixture('d1_b8_p0_breadth_t8')['checkpoint_sha256']),{'1024','2048'})
    def test_rehashed_lr_difference_rejected(self):
        def mutate(s):s['lrs'][10]+=1e-12
        with self.assertRaises(ValueError):self.run_fixture('d1_b1_p4_depth_t1',mutate)
    def test_nonfinite_optimizer_rejected(self):
        import torch
        def mutate(s):s['optimizer']['state'][0]['step']=torch.tensor(float('inf'))
        with self.assertRaises(ValueError):self.run_fixture('d1_b1_p0_depth_t1_replacement_r1',mutate)
    def test_wrong_prefix_dose_rejected(self):
        with self.assertRaises(ValueError):self.run_fixture('d1_b8_p0_depth_t8',lambda s:s.update(supervised_tokens=s['supervised_tokens']+1))



class FailedArchive(unittest.TestCase):
    def exercise(self,add_unit=False,status='failed'):
        from experiments.sft_allocation_p008.audit_failed_student import verify_failed_student
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);original=root/'original';original.mkdir()
            n=sorted(FAILED_STUDENTS)[0]
            cfg=dict(run_id=n,role='main');plan=dict(campaign_id=STUDENT_CAMPAIGN)
            release=dict(commit='synthetic',source_files={'fixture.py':'a'*64})
            dump(original/'intent.json',dict(config=cfg,plan=plan,release=release))
            dump(original/'block_journal_metrics.json',dict(block_boundary_calls=0,completed_blocks=0,completed_local_updates=0))
            dump(original/'failure.json',dict(error='synthetic zero-update failure'))
            if add_unit:dump(original/'completed/update_0001.json',dict(step=1))
            files=manifest(original);dump(original/'failure_manifest.json',files)
            contents=manifest(original);pack(original)
            claim=dict(plan_sha256=digest(plan))
            terminal=dict(status=status,claim_sha256=digest(claim),evidence_sha256=digest(files))
            spec=dict(parents={n:dict(claim=claim,terminal=terminal)},
                zero_update_reconciliation=dict(runs={n:dict(training_updates_attempted=0,training_updates_completed=0,
                    supervised_targets=0,endpoint_outputs=0,unresolved_scientific_units=0)}),
                original_spec=dict(configs={n:cfg}),original_releases={n:release},original_execution_plan=plan)
            label=dict(campaign=STUDENT_CAMPAIGN,run_id=n,config=cfg,replacement_spec=spec,claim=claim,terminal=terminal,
                preserved_manifest=contents,archive_files={k:manifest(original)[k] for k in CONTAINERS})
            with patch('experiments.sft_allocation_p008.audit_failed_student.REPLACEMENT_SPEC',digest(spec)):
                return verify_failed_student(original,root/'checked',label)
    def test_failed_archive_keeps_failed_identity(self):
        result=self.exercise();self.assertEqual(result['original_status'],'failed');self.assertEqual(result['attempted_updates'],0)
    def test_rehashed_archive_with_scientific_unit_rejected(self):
        with self.assertRaises(ValueError):self.exercise(add_unit=True)
    def test_failed_archive_cannot_be_called_completed(self):
        with self.assertRaises(ValueError):self.exercise(status='completed')


if __name__=='__main__':unittest.main()
