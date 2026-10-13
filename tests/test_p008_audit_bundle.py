import tempfile,unittest,copy
from pathlib import Path
from experiments.sft_allocation_midpoint.common import dump,manifest,digest,sha
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_p008.contract import lrs
from experiments.sft_allocation_p008.evidence_bundle import pack
from experiments.sft_allocation_p008.audit_bundle import verify_packed_run


def fixture(root):
    src=root/'remote';src.mkdir();cfg=dict(role='pool',run_id='pool_d1',draw=1)
    result=dict(physical_outputs=0,engineering_fixture=True)
    dump(src/'intent.json',dict(config=cfg,plan=dict(campaign_id='fixture')));dump(src/'result.json',result)
    dump(src/'small.json',dict(kept='original'))
    pack(src);files=manifest(src);dump(src/'artifact_manifest.json',files)
    e=dict(result=result,artifact_manifest=files,receipt=dict(status='completed',evidence_sha256=digest(files)))
    return src,dict(campaign='fixture',run_id='pool_d1',config=cfg,envelope=e,local_oracle=dict(passed=True,manifest_digest=digest(files),draw=1,physical_outputs=0,all_raw_redecoded=True,all_wallets_replayed=True))


def student_fixture(root,u=256,mutate=None):
    """Synthetic complete serialized state, no training/model/inference call."""
    import torch
    src=root/'remote';src.mkdir();cfg=dict(role='main',run_id='student',updates=u,targets=u*2)
    release=dict(commit='fixture-commit',source_files={'fixture.py':'1'*64})
    identity=dict(config=cfg,source_commit=release['commit'],source_sha256=digest(release['source_files']))
    schedule=[[0]]*u;rates=lrs(u)
    scores={f'fixture/{i}':i%2==0 for i in range(1319)}
    result=dict(updates=u,targets=u*2,endpoint=dict(question_correct=scores,correct=sum(scores.values())))
    dump(src/'intent.json',dict(config=cfg,plan=dict(campaign_id='fixture'),release=release));dump(src/'result.json',result)
    dump(src/'recipe.json',dict(identity=identity,schedule=schedule,lrs=rates))
    state_hashes={}
    for step in ([1024,2048] if u==2048 else [u]):
        s=dict(schema='complete_lora_v1',identity=identity,step=step,cursor=step,supervised_tokens=step*2,processed_tokens=step*3,
          schedule=schedule,lrs=rates,trainable_names=['adapter.a'],adapter={'adapter.a':torch.ones(2)},
          optimizer={'state':{0:{'step':torch.tensor(float(step)),'exp_avg':torch.zeros(2)}},'param_groups':[{'params':[0]}]},
          rng=ck.rng_state())
        if mutate:mutate(s)
        ck.save(src,s);state_hashes[str(step)]=sha(src/f'checkpoint_{step:04d}/state.pt')
        dump(src/'completed'/f'update_{step:04d}.json',dict(cumulative_targets=step*2,cumulative_processed=step*3))
    pack(src);files=manifest(src);dump(src/'artifact_manifest.json',files)
    e=dict(result=result,artifact_manifest=files,receipt=dict(status='completed',evidence_sha256=digest(files)))
    oracle=dict(passed=True,artifact_digest=digest(files),run_id=cfg['run_id'],role=cfg['role'],updates_verified=u,targets_verified=u*2,
      outputs_rescored=1319,correct=sum(scores.values()),state_sha256=state_hashes[str(u)],
      forensic_checkpoints={k:dict(sha256=v) for k,v in state_hashes.items() if k!=str(u)})
    return src,dict(campaign='fixture',run_id=cfg['run_id'],config=cfg,envelope=e,local_oracle=oracle)

class AuditBundleTest(unittest.TestCase):
    def test_all_original_record_hashes_from_packed_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);result=verify_packed_run(src,root/'local',label)
            self.assertTrue(result['passed']);self.assertEqual(result['files_verified'],6);self.assertEqual(result['new_model_calls'],0)
    def test_changed_remote_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);(src/'artifact_manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'remote manifest'):verify_packed_run(src,root/'local',label)
    def test_replaced_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);(src/'compact_evidence.tar.gz').write_bytes(b'wrong')
            with self.assertRaises(ValueError):verify_packed_run(src,root/'local',label)
    def test_foreign_local_oracle_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);label['local_oracle']['manifest_digest']='f'*64
            with self.assertRaisesRegex(ValueError,'local oracle'):verify_packed_run(src,root/'local',label)
    def test_foreign_claimed_run_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);label['run_id']='pool_d2'
            with self.assertRaisesRegex(ValueError,'Foreign run'):verify_packed_run(src,root/'local',label)
    def test_no_silent_overwrite_after_partial_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);dst=root/'local';dst.mkdir()
            with self.assertRaises(FileExistsError):verify_packed_run(src,dst,label)
    def test_missing_student_state_even_with_rehashed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=fixture(root);label['config']=dict(role='main',run_id='s',updates=256,targets=524287)
            with self.assertRaisesRegex(ValueError,'complete states'):verify_packed_run(src,root/'local',label)
    def test_full_student_state_and_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root)
            result=verify_packed_run(src,root/'local',label)
            self.assertEqual(result['checkpoint_sha256'],{'256':label['local_oracle']['state_sha256']})
    def test_both_forensic_and_terminal_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root,u=2048)
            self.assertEqual(set(verify_packed_run(src,root/'local',label)['checkpoint_sha256']),{'1024','2048'})
    def test_rehashed_wrong_prefix_dose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root,mutate=lambda s:s.update(supervised_tokens=s['supervised_tokens']+1))
            with self.assertRaisesRegex(ValueError,'prefix dose'):verify_packed_run(src,root/'local',label)
    def test_rehashed_wrong_lr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root,mutate=lambda s:s.update(lrs=[0.001]*s['step']))
            with self.assertRaisesRegex(ValueError,'trajectory'):verify_packed_run(src,root/'local',label)
    def test_rehashed_missing_rng(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root,mutate=lambda s:s['rng'].pop('numpy'))
            with self.assertRaisesRegex(ValueError,'training state'):verify_packed_run(src,root/'local',label)
    def test_rehashed_nonfinite_optimizer(self):
        import torch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root,mutate=lambda s:s['optimizer']['state'][0].update(step=torch.tensor(float('inf'))))
            with self.assertRaisesRegex(ValueError,'nonfinite'):verify_packed_run(src,root/'local',label)
    def test_prior_oracle_state_hash_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src,label=student_fixture(root);label['local_oracle']['state_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'full-state oracle'):verify_packed_run(src,root/'local',label)

if __name__=='__main__':unittest.main()
