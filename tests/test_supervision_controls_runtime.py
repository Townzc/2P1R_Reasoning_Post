from contextlib import ExitStack, nullcontext, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.supervision_controls_v1.io import Ledger, independent_output, sha, source_check
from experiments.supervision_controls_v1 import io as phase_io
from experiments.supervision_controls_v1.runner import checked_component
from experiments.supervision_controls_v1.analyze import paired_interval
from experiments.supervision_controls_v1 import train
from experiments.public_math_pilot_v1.preflight import training_batch
from experiments.public_math_pilot_v1.losses import qdw_token_weights
from experiments.supervision_controls_v1.masks import make_control


class LedgerSafety(unittest.TestCase):
    def test_duplicate_reservation_survives_new_process_object(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"ledger.jsonl"
            Ledger(path).reserve("generation",["job/p"])
            with self.assertRaises(RuntimeError):
                Ledger(path).reserve("generation",["job/p"])
            self.assertEqual(len(Ledger(path).events()),1)

    def test_over_budget_has_no_partial_append(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/"ledger.jsonl")
            ledger.reserve("optimizer_update",[str(i) for i in range(256)])
            with self.assertRaises(RuntimeError):
                ledger.reserve("optimizer_update",["257"])
            self.assertEqual(len(ledger.events()),256)

    def test_historical_phase_cannot_be_reset(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"ledger.jsonl"
            path.write_text(json.dumps(dict(phase="public_math_pilot_v1",kind="generation",logical_id="old"))+"\n")
            with self.assertRaises(ValueError):
                Ledger(path).reserve("generation",["new"])

    def test_new_output_cannot_alias_or_contain_prior(self):
        with tempfile.TemporaryDirectory() as td:
            prior=Path(td)/"prior"
            prior.mkdir()
            alias=Path(td)/"alias"
            alias.symlink_to(prior, target_is_directory=True)
            for out in (prior, prior/"child", Path(td), alias):
                with self.assertRaises(ValueError):
                    independent_output(out,prior)

    def test_component_hash_and_path_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"store";root.mkdir()
            path=root/"model.pt";path.write_bytes(b"fixture")
            rec=dict(volume=0,path="model.pt",bytes=7,sha256=sha(path))
            self.assertEqual(checked_component(rec,[root]),path.resolve())
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                checked_component(rec,[root])
            with self.assertRaises(ValueError):
                checked_component(dict(rec,path="../outside"),[root])


class StatisticsAndWeights(unittest.TestCase):
    def test_perfect_paired_difference_and_unknown_bounds(self):
        r=paired_interval([1]*12,[1]*12,replicates=300)
        self.assertEqual(r["interval"],[1,1])
        r=paired_interval([-1]*12,[1]*12,replicates=300)
        self.assertEqual(r["interval"],[-1,1])
        self.assertEqual(r["questions"],12)

    def test_matched_controls_preserve_weight_mass_and_multiset(self):
        length=41
        a=dict(L=length,K=4,eligible_indices=list(range(40)),selected_indices=[0,4,9,20],
               full_logp=[-.1*(i%7) for i in range(length)],mask=[i in [0,4,9,20] for i in range(length)])
        labels=torch.tensor([[-100,-100]+list(range(length))])
        orig=qdw_token_weights(labels,torch.tensor([[False,False]+a["mask"]]))
        for condition in ("random","position_difficulty"):
            r=make_control("fixture",a,condition)
            weights=qdw_token_weights(labels,torch.tensor([[False,False]+r["mask"]]))
            self.assertTrue(torch.allclose(weights.sum(1),torch.tensor([float(length)])))
            self.assertTrue(torch.equal(weights.sort().values,orig.sort().values))
            self.assertEqual(weights[0,0].item(),0)
            self.assertEqual(weights[0,-1].item(),orig[0,-1].item())


class ArchiveSourceGuard(unittest.TestCase):
    def test_archive_requires_external_hash_and_checks_full_python_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve()
            public=root/"experiments/public_math_pilot_v1"
            current=root/"experiments/supervision_controls_v1"
            public.mkdir(parents=True);current.mkdir()
            (public/"runtime.py").write_text("# inherited fixture\n")
            (current/"io.py").write_text("# control fixture\n")
            (current/"PROTOCOL.md").write_text("frozen fixture")
            inventory=dict(commit="a"*40,
                python_source_sha256={p.relative_to(root).as_posix():sha(p) for p in root.rglob("*.py")},
                configuration_sha256={"experiments/supervision_controls_v1/PROTOCOL.md":sha(current/"PROTOCOL.md")})
            manifest=root/"SOURCE_INVENTORY.json"
            manifest.write_text(json.dumps(inventory))
            expected=sha(manifest)
            with patch.object(phase_io,"__file__",str(current/"io.py")):
                with self.assertRaises(ValueError):
                    source_check("a"*40)
                self.assertEqual(source_check("a"*40,expected),inventory)
                (public/"extra.py").write_text("# unexpected\n")
                with self.assertRaises(ValueError):
                    source_check("a"*40,expected)


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.table=torch.nn.Embedding(8,8)
    def forward(self,input_ids,attention_mask=None,use_cache=False):
        return SimpleNamespace(logits=self.table(input_ids))


class TrainerIntegration(unittest.TestCase):
    def fixture(self,td):
        rows=[dict(problem_id=f"p{i}",input_ids=[1,2,3],labels=[-100,2,3],
                   response_ids=[2,3],response_start=1) for i in range(32)]
        batches=[rows for _ in range(128)]
        contract=dict(batches=[[r["problem_id"] for r in rows] for _ in range(128)],
                      denominators=[64]*128,learning_rates=[1e-4]*127+[0.0],
                      scientific_identity=dict(model_sha256="a"*64))
        args=SimpleNamespace(output=str(Path(td)/"output"),volume_root=[str(Path(td)/"store")],
                             base="not-a-real-model",source_commit="b"*40,deadline_unix=10**12)
        masks={r["problem_id"]:[True,False] for r in rows}
        return args,contract,batches,masks

    def test_full_finite_loop_checkpoint_and_no_completed_replay(self):
        with tempfile.TemporaryDirectory() as td, ExitStack() as stack:
            args,contract,batches,masks=self.fixture(td)
            # Tiny vocabulary only; real serialization is covered by inherited tokenizer tests.
            stack.enter_context(patch("experiments.public_math_pilot_v1.preflight.ASSISTANT_END_ID",3))
            stack.enter_context(patch("experiments.public_math_pilot_v1.preflight.EOS_ID",0))
            stack.enter_context(patch.object(train,"load_base",side_effect=lambda *a,**k:TinyModel()))
            stack.enter_context(patch.object(train,"training_batch",side_effect=lambda rows,masks:training_batch(rows,masks=masks,device="cpu")))
            stack.enter_context(patch.object(train,"wait_for_training_memory",return_value=None))
            stack.enter_context(patch.object(train,"host_available_bytes",return_value=100*2**30))
            stack.enter_context(patch.object(train.torch,"autocast",side_effect=lambda *a,**k:nullcontext()))
            for name in ("synchronize","reset_peak_memory_stats"):
                stack.enter_context(patch.object(train.torch.cuda,name,return_value=None))
            stack.enter_context(patch.object(train.torch.cuda,"max_memory_allocated",return_value=0))
            with redirect_stdout(io.StringIO()):
                result=train.train_arm(args,contract,batches,masks,"random")
                repeated=train.train_arm(args,contract,batches,masks,"random")
            self.assertEqual(result["status"],"complete")
            self.assertEqual(repeated["status"],"already_complete")
            events=Ledger(Path(args.output)/"physical_ledger.jsonl").events()
            self.assertEqual(len(events),128)
            store=train.store_for(args.output,args.volume_root,contract,"random")
            endpoint=store.latest_manifest()
            self.assertTrue(endpoint["terminal"])
            self.assertEqual(endpoint["token_step"],8192)
            self.assertEqual(len(endpoint["metadata"]["history"]),128)
            self.assertEqual(endpoint["metadata"]["history"][-1]["learning_rate"],0)

    def test_ambiguous_uncommitted_update_stops_before_model_load(self):
        with tempfile.TemporaryDirectory() as td:
            args,contract,batches,masks=self.fixture(td)
            Ledger(Path(args.output)/"physical_ledger.jsonl").reserve("optimizer_update",["random/1"])
            with patch.object(train,"load_base") as load:
                with self.assertRaises(RuntimeError):
                    train.train_arm(args,contract,batches,masks,"random")
                load.assert_not_called()


if __name__=="__main__":
    unittest.main()
