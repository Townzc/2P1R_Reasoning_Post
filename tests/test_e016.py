import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from analyses import e016
from analyses.gsm8k_answer_audit import score
from src.real_math_engineering import score_completion


class Tokenizer:
    eos_token_id = 99
    def __call__(self, text, **kwargs):
        return {"input_ids": [1] * len(text.split())}
    def __len__(self):
        return 100
    def decode(self, ids, **kwargs):
        return "Answer: 1" if ids == [2] else "bad"


def example(correct=True):
    return score({"answer": "1"}, "Answer: " + ("1" if correct else "2"), True, False)


class InputTests(unittest.TestCase):
    def test_original_groups_and_rank_selection(self):
        parents = e016.selected_parents()
        self.assertEqual(len(parents), 64)
        self.assertEqual([p["rank"] for p in parents], list(range(17, 81)))
        self.assertEqual(len({p["group_id"] for p in parents}), 64)
        self.assertTrue(all(p["original_split"] == "train" for p in parents))

    def test_raw_identity_hash_and_context_checks(self):
        rows = [{"problem_id": str(i), "group_id": str(i), "development_rank": i+17,
                 "prompt": "How many?", "answer": "1"} for i in range(64)]
        parents = [{"id": r["problem_id"], "group_id": r["group_id"], "rank": r["development_rank"],
                    "problem_sha256": hashlib.sha256(r["prompt"].encode()).hexdigest(),
                    "answer_sha256": hashlib.sha256(r["answer"].encode()).hexdigest()} for r in rows]
        with patch.object(e016, "selected_parents", return_value=parents):
            self.assertEqual(len(e016.validate_rows(rows, Tokenizer())), 64)
            for field, value in [("prompt", "Different"), ("answer", "2"), ("problem_id", "wrong")]:
                changed = copy.deepcopy(rows); changed[0][field] = value
                with self.assertRaises(ValueError):
                    e016.validate_rows(changed, Tokenizer())
            with self.assertRaises(ValueError):
                e016.validate_rows(rows[:-1], Tokenizer())
            class LongTokenizer(Tokenizer):
                def __call__(self, text, **kwargs): return {"input_ids": [1]*257}
            with self.assertRaises(ValueError):
                e016.validate_rows(rows, LongTokenizer())

    def test_rental_admission_does_not_reset_window(self):
        start = datetime(2026, 9, 10, tzinfo=timezone.utc)
        self.assertEqual(e016.rental_window(start.isoformat(), start+timedelta(seconds=415))["remaining_seconds"], 785)
        for age in (-1, 416, 1200):
            with self.assertRaises(ValueError):
                e016.rental_window(start.isoformat(), start+timedelta(seconds=age))
        with self.assertRaises(ValueError): e016.rental_window("2026-09-10T00:00:00")

    def test_checkpoint_hash_inventory_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); folder = root / "checkpoint"; folder.mkdir()
            files = {}
            for i in range(12):
                p = folder / str(i); p.write_bytes(bytes([i]))
                files[p.name] = {"bytes": 1, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"kind": "weights_only_not_optimizer_rng_resume", "files": files}))
            cfg = {"checkpoint_manifest_sha256": e016.sha256_file(manifest)}
            with patch.object(e016, "CHECKPOINT_MANIFEST", manifest):
                self.assertTrue(e016.checkpoint_audit(folder, cfg)["all_files_verified"])
                (folder / "0").write_bytes(b"x")
                with self.assertRaises(ValueError): e016.checkpoint_audit(folder, cfg)
                (folder / "0").write_bytes(b"\0")
                link = root / "alias"; link.symlink_to(folder)
                with self.assertRaises(ValueError): e016.checkpoint_audit(link, cfg)
                (folder / "extra").write_bytes(b"")
                with self.assertRaises(ValueError): e016.checkpoint_audit(folder, cfg)


class DecisionTests(unittest.TestCase):
    def test_preserved_capability_and_loss_are_distinct(self):
        base = [example(i < 32) for i in range(64)]
        retained = [example(i < 24) for i in range(64)]
        result = e016.decisions({"base": base, "e015": retained})
        self.assertTrue(result["base_nonfloor_gate"])
        self.assertTrue(result["e015_retention_screen"])
        self.assertEqual(result["paired_lost"], 8)
        lost = e016.decisions({"base": base, "e015": [example(False)]*64})
        self.assertFalse(lost["e015_retention_screen"])
        self.assertEqual(lost["paired_net_correct_change"], -32)
        self.assertFalse(result["scientific_grid_authorized"])

    def test_floor_and_incomplete_denominator(self):
        values = [example(i < 7) for i in range(64)]
        self.assertFalse(e016.decisions({"base": values, "e015": values})["base_nonfloor_gate"])
        with self.assertRaises(ValueError): e016.decisions({"base": values[:-1], "e015": values})

    def test_good_answer_count_cannot_hide_format_failure(self):
        values = [example(True)]*47 + [score({"answer": "1"}, "unmarked", True, False)]*17
        self.assertFalse(e016.decisions({"base": values, "e015": values})["base_nonfloor_gate"])


class OutputAuditTests(unittest.TestCase):
    def test_raw_stream_and_sidecar_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); run = root / "run"; run.mkdir()
            release = root / "release.json"; release.write_text("{}")
            cfg = {"run_id": "fake", "max_new_tokens": 768}
            rows = [{"problem_id": str(i), "answer": "1"} for i in range(64)]
            def write(name, value):
                (run / name).write_text(json.dumps(value))
            write("run_manifest.json", {"status": "completed", "config": cfg,
                  "release_sha256": e016.sha256_file(release)})
            settings = {"do_sample": False, "num_beams": 1, "use_cache": True, "max_new_tokens": 768,
                        "eos_token_id": 151643, "pad_token_id": 151643, "repetition_penalty": 1.0,
                        "no_repeat_ngram_size": 0, "forced_eos_token_id": None, "forced_bos_token_id": None,
                        "stop_strings": None, "cache_implementation": None}
            for name in ("base", "e015"):
                predictions = [{**r, "text": "Answer: 1", "generated_ids": [2, 99], "generated_tokens": 2,
                                "score": score_completion(r, "Answer: 1", True, False)} for r in rows]
                (run / (name + ".jsonl")).write_text("".join(json.dumps(r)+"\n" for r in predictions))
                sidecar = [{"problem_id": r["problem_id"], "score": example()} for r in rows]
                (run / (name + "_marked.jsonl")).write_text("".join(json.dumps(r)+"\n" for r in sidecar))
                write(name + "_generation_config.json", settings)
                write(name + "_profile.json", {"n": 64, "output_tokens": 128, "generation_seconds": 2,
                      "peak_allocated_mib": 4, "peak_reserved_mib": 5})
            write("phase_timings.json", {"completed_phases_seconds": {"base_generation": 2, "e015_generation": 2}})
            write("metrics.json", e016.decisions({"base": [example()]*64, "e015": [example()]*64}))
            write("resource_receipt.json", {"run_id": "fake", "status": "completed", "exit_code": 0, "charged_seconds": 12})
            with patch.object(e016, "RELEASE", release), patch.object(e016, "load_release", return_value=(cfg, rows)):
                self.assertEqual(e016.audit_run(Tokenizer(), run, root / "ok.json")["raw_token_streams_checked"], 128)
                path = run / "base.jsonl"
                original = path.read_text(); path.write_text(original.replace('"generated_tokens": 2', '"generated_tokens": 3', 1))
                with self.assertRaises(ValueError): e016.audit_run(Tokenizer(), run, root / "bad.json")
                path.write_text(original)
                sidecar[0]["score"]["clean_correct"] = False
                (run / "base_marked.jsonl").write_text("".join(json.dumps(r)+"\n" for r in sidecar))
                with self.assertRaises(ValueError): e016.audit_run(Tokenizer(), run, root / "bad2.json")


if __name__ == "__main__": unittest.main()
