"""New CPU/mocked core checks only; no models, symbolic labels or old tests."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from experiments.sft_allocation_midpoint.common import digest, dump
from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal
from experiments.learning_regime_p009 import stage1_training_core as core
from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint, EndpointCursor


def release():
    rows = [dict(problem_id=f'p/{i}', path_id=f'p/{i}/a', prompt='q', response='a') for i in range(400)]
    encoded = [dict(problem_id=r['problem_id'], path_id=r['path_id'],
        n_supervised=3, n_processed=5) for r in rows]
    plan = dict(updates=[[0] for _ in range(1024)], lrs=[1e-4]*1024,
        row_path_ids=[r['path_id'] for r in rows], row_exposures=[1]*400)
    config = dict(setting='NC', seed=17, n=400, updates=1024, targets=2097148,
        model=deepcopy(core.MODELS['qwen']), encoded_rows_sha256=digest(encoded),
        training_rows_sha256=digest(rows), plan_sha256=digest(plan),
        lr_vector_sha256=core.LR_VECTOR_SHA256)
    return config, rows, encoded, plan


def endpoint(setting):
    rows = []
    for i in range(1319 if setting == 'NC' else 500):
        row = dict(problem_id=f'p/{i}', input_ids=[1, 2])
        rows.append(dict(**row, candidate_id=setting+'::'+row['problem_id'],
                         source_row_sha256=digest(row)))
    return rows


class ScientificCoreTests(unittest.TestCase):
    def test_unregistered_setting_seed_size_or_dose_rejected(self):
        config, rows, encoded, plan = release()
        for key, value in [('setting','S2'), ('seed',29), ('seed',True), ('n',100),
                           ('updates',256), ('targets',2097149)]:
            changed = {**config, key:value}
            with self.subTest(key=key,value=value), patch.object(core,'validate_plan') as validate:
                with self.assertRaises(ValueError): core.checked_recipe(changed,encoded,plan)
                validate.assert_not_called()

    def test_exact_answer_and_plan_binding_precedes_model(self):
        config, rows, encoded, plan = release()
        for key in ('encoded_rows_sha256','plan_sha256','lr_vector_sha256'):
            with patch.object(core.rt,'new_model') as model:
                with self.assertRaises(ValueError):
                    core.checked_recipe({**config,key:'0'*64},encoded,plan)
                model.assert_not_called()

    def test_original_plan_validator_receives_exact_seed_eos(self):
        config, rows, encoded, plan = release()
        config.update(setting='S1',seed=29)
        with patch.object(core,'validate_plan',return_value={'validated':True}) as validator:
            result=core.checked_recipe(config,encoded,plan)
            validator.assert_called_once_with(encoded,plan,29,151643)
            self.assertEqual((result['endpoint_count'],result['endpoint_max_new_tokens']),(500,1024))
            self.assertFalse(result['runtime_admitted'])

    def test_full_mocked_training_route_only_terminal_save_then_merge(self):
        config, rows, encoded, plan=release();identity={'config':config};events=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'evidence';out.mkdir();merged=root/'merged'
            store=SimpleNamespace(put=lambda *a,**k:True)
            journal=BlockTrainingJournal(out,'unit',store,lambda:None,lambda:None,
                deadline=lambda:None,expected_updates=1024)
            class Model:
                def eval(self):events.append('eval')
                def merge_and_unload(self,**kwargs):
                    self_test.assertEqual(kwargs,{'safe_merge':True});events.append('merge');return self
                def to(self,**kwargs):self_test.assertEqual(kwargs,{'dtype':'bf16'});return self
                def save_pretrained(self,path,**kwargs):(path/'model.safetensors').write_bytes(b'mocked')
            class Tokenizer:
                eos_token_id=151643
                def save_pretrained(self,path):(path/'tokenizer.json').write_text('{}')
            self_test=self
            def fake_train(model,tok,opt,enc,schedule,lrs,folder,j,ident,**kwargs):
                self.assertEqual(kwargs,{'save_steps':(1024,)})
                self.assertIs(enc,encoded);self.assertIs(schedule,plan['updates']);self.assertIs(lrs,plan['lrs'])
                events.append('train');j.cursor=1024
                dump(folder/'checkpoint_1024/manifest.json',dict(step=1024,supervised_tokens=2097148,
                    processed_tokens=3000000,identity_sha256=digest(ident),sha256='f'*64))
                return [{}]*1024,2097148,3000000
            with patch.object(core,'validate_plan',return_value={'mocked':True}), \
                 patch.object(core,'training_environment',return_value={'mocked':True}), \
                 patch.object(core.rt,'new_model',return_value=(Model(),Tokenizer())) as new, \
                 patch.object(core.rt,'encode',return_value=encoded), \
                 patch.object(core.rt,'optimizer_for',return_value=object()), \
                 patch.object(core.rt,'train',side_effect=fake_train) as train, \
                 patch.dict('sys.modules',{'torch':SimpleNamespace(bfloat16='bf16')}):
                result=core.train_and_merge('base',rows,encoded,plan,out,merged,journal,identity)
                new.assert_called_once_with('base',17);train.assert_called_once()
                self.assertEqual(events,['train','eval','merge']);self.assertFalse(result['evaluation_performed'])
                self.assertTrue((out/'MERGE_PROOF.json').exists())
                with self.assertRaises(ValueError):
                    core.train_and_merge('base',rows,encoded,plan,out,merged,journal,identity)
                train.assert_called_once()

    def test_endpoint_matches_original_caps_and_greedy_engine_seed(self):
        for setting,cap in [('NC',512),('S1',1024)]:
            params=checked_endpoint(setting,endpoint(setting))
            self.assertEqual((params['max_tokens'],params['seed'],params['temperature']),(cap,17,0))
            self.assertEqual(params['stop_token_ids'],[151643]);self.assertIsNone(params['stop'])

    def test_partial_or_duplicate_or_foreign_endpoint_rejected(self):
        rows=endpoint('NC')
        for bad in [rows[:-1],rows[:-1]+[rows[0]]]:
            with self.assertRaises(ValueError):checked_endpoint('NC',bad)
        bad=deepcopy(rows);bad[0]['input_ids']=[3]
        with self.assertRaises(ValueError):checked_endpoint('NC',bad)
        with self.assertRaises(ValueError):checked_endpoint('S2',rows)

    def test_full_input_overflow_is_not_truncated(self):
        rows=endpoint('S1');rows[0]['input_ids']=[1]*1025
        rows[0]['source_row_sha256']=digest({k:rows[0][k] for k in ('problem_id','input_ids')})
        with self.assertRaises(ValueError):checked_endpoint('S1',rows)

    def test_cursor_preserves_all_original_batches_and_never_replays(self):
        rows=endpoint('NC');cursor=EndpointCursor(rows);seen=[]
        for offset in range(0,len(rows),256):
            seen.extend(cursor.reserve(offset))
            with self.assertRaises(ValueError):cursor.reserve(offset)
        self.assertEqual(seen,rows)
        with self.assertRaises(ValueError):cursor.reserve(len(rows))

if __name__=='__main__':unittest.main()
