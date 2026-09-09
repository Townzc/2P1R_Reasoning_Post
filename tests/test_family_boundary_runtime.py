import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import scripts.prepare_absent_boundary as preparation
import src.family_boundary_runtime as runtime
from scripts.audit_matching_selection import characterize
from src.countdown_smoke import canonical, render_trace, safe_parse
from src.sft_data import encode_row, sha256_file


class FixtureTokenizer:
    """Offset-aware synthetic tokenizer with equal-size test surface frames."""
    eos_token_id = 0
    pattern = re.compile(r"Step \d+:|We now calculate:|Next, we obtain|This calculation gives us|[A-Za-z]+|\d+|[^\s]")

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        matches = list(self.pattern.finditer(text))
        ids = []
        for match in matches:
            token = match.group()
            if token.startswith(("Step ", "We now ", "Next,", "This calculation")):
                token = "FRAME"
            ids.append(int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 100000 + 1)
        result = {"input_ids": ids}
        if return_offsets_mapping:
            result["offset_mapping"] = [(match.start(), match.end()) for match in matches]
        return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in values))


def canonical_row(problem, expression, tokenizer):
    tree = safe_parse(expression)
    row = {**problem, "expression": expression, "response": render_trace(tree),
           "path_id": canonical(tree), "ac_class": canonical(tree),
           "structure_id": canonical(tree, structure_only=True), "family": "identity_absent", "encodable": True}
    encoded = encode_row(row, tokenizer, 384)
    row.update({key: encoded[key] for key in ("n_supervised", "n_prompt", "n_processed", "response_hash")})
    return row


def fixture_objects(block_count=17):
    tokenizer, problems, pathsets = FixtureTokenizer(), {}, {}
    for scale in range(1, 257):
        a, b, c, d = [n * scale for n in (12, 18, 25, 37)]
        pid = f"p{scale:03d}"
        problem = {"problem_id": pid, "numbers": [a, b, c, d], "target": b,
                   "prompt": f"Use {a}, {b}, {c}, {d} once to make {b}. Show calculations."}
        problems[pid] = problem
        if scale <= block_count * 4:
            expressions = [f"(({b} / {a}) * ({d} - {c}))", f"(({b} / ({d} - {c})) * {a})",
                           f"(({d} - {c}) / ({a} / {b}))", f"({a} / (({d} - {c}) / {b}))"]
            rows = sorted([canonical_row(problem, expr, tokenizer) for expr in expressions], key=lambda row: row["structure_id"])
            assert len({row["n_supervised"] for row in rows}) == 1
            pathsets[pid] = rows
    packed = []
    for index in range(block_count):
        ids = sorted(problems)[4 * index:4 * index + 4]
        structures = [row["structure_id"] for row in pathsets[ids[0]]]
        witnesses = {pid: {"problem_id": pid, "n_supervised": pathsets[pid][0]["n_supervised"],
                           "slots": [{"structure_id": row["structure_id"], "ac_class": row["ac_class"],
                                      "family": "identity_absent", "record": row} for row in pathsets[pid]]}
                     for pid in ids}
        packed.append({"group_id": index, "problem_ids": ids,
                       "representative": {"structures": structures, "problem_ids": ids, "witnesses": witnesses}})
    ids = sorted(pathsets)
    sources = {"packing": {"input_join_complete": True, "solver_status": 0,
                            "primal_block_count": block_count, "blocks": packed, "used_problem_ids": ids},
               "summary": {"diagnostic_id": "C012", "status": "complete", "join_complete": True,
                           "gpu_seconds_added": 0, "model_or_development_outputs_read": False,
                           "packing_block_count": block_count, "source_commit": "c" * 40,
                           "config": {"training_family": "identity_absent", "training_seed": 31,
                                      "selection_seed": 31, "training_updates": 1024, "block_tiers": [32, 16]}},
               "selection": characterize(problems, {"individual_family_feasible": ids,
                                                     "shared_key_supported": ids, "packed": ids})}
    return problems, sources, tokenizer


def write_fixture_sources(repo, problems, sources, tokenizer):
    original = repo / runtime.ORIGINAL_DIR
    items = [{"problem": problem, "paths": []} for problem in problems.values()]
    write_json(original / "train_blocks.json", [{"problems": items[i:i + 4]} for i in range(0, 256, 4)])
    refs = []
    for i in range(128):
        nums = [5 * i + j for j in (2, 3, 4, 5)]
        problem = {"problem_id": f"dev{i:03d}", "numbers": nums, "target": sum(nums), "prompt": f"Add {nums}."}
        a, b, c, d = nums
        refs.append(canonical_row(problem, f"(({a} + {b}) + ({c} + {d}))", tokenizer))
    write_jsonl(original / "dev_matched.jsonl", refs[:64])
    write_jsonl(original / "dev_broad.jsonl", refs[64:])
    split = {"stage": "before_solving_or_augmentation", "groups": {
        "train": [problem["numbers"] for problem in problems.values()], "dev": [row["numbers"] for row in refs],
        "holdout_reserved": [[7001, 7002, 7003, 7004], [8001, 8002, 8003, 8004]]}}
    write_json(original / "split_allocation.json", split)
    write_json(repo / "configs/models.lock.json", {"main": runtime.MODEL})
    candidate = repo / "reports/fixture_candidate"
    for name in ("packing", "selection"):
        write_json(candidate / (name + ".json"), sources[name])
    sources["summary"]["output_sha256"] = {name + ".json": sha256_file(candidate / (name + ".json"))
                                           for name in ("packing", "selection")}
    write_json(candidate / "summary.json", sources["summary"])
    return {name: sha256_file(original / name) for name in runtime.ORIGINAL_HASHES}, candidate


class FamilyBoundaryRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problems, cls.sources, cls.tokenizer = fixture_objects()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.original_hashes, candidate = write_fixture_sources(self.repo, copy.deepcopy(self.problems),
                                                                copy.deepcopy(self.sources), self.tokenizer)
        self.out = self.repo / "runs/boundary_fixture"
        self.patches = [mock.patch.object(runtime, "REPO_ROOT", self.repo),
                        mock.patch.object(runtime, "ORIGINAL_HASHES", self.original_hashes),
                        mock.patch.object(preparation, "ORIGINAL_HASHES", self.original_hashes),
                        mock.patch.object(preparation, "source_provenance", return_value={"source_commit": "a" * 40,
                                          "source_worktree_dirty": False, "source_files_sha256": {}}),
                        mock.patch.object(preparation, "verified_tokenizer", return_value=(self.tokenizer, {"fixture": True}))]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.manifest = preparation.prepare_absent_boundary(self.out, self.repo / "fixture_tokenizer",
                                                            candidate_dir=candidate, repo=self.repo)
        self.cfg = {"data_dir": str(self.out), "data_manifest_sha256": sha256_file(self.out / "manifest.json"),
                    "arm": "paths", "mode": "scientific_pilot", "model_role": "main", "seed": 31, "eval_seed": 17,
                    "batch_size": 4, "microbatch_size": 2, "steps": 1024, "max_length": 384,
                    "max_new_tokens": 384, "learning_rate": 5e-5, "weight_decay": .01, "grad_clip": 1.0}

    def rehash_artifact(self, filename):
        manifest = json.loads((self.out / "manifest.json").read_text())
        manifest["files_sha256"][filename] = sha256_file(self.out / filename)
        write_json(self.out / "manifest.json", manifest)
        self.cfg["data_manifest_sha256"] = sha256_file(self.out / "manifest.json")

    def test_full_fixture_reconstruction_and_token_audit(self):
        rows, dev, broad, schedule, audit = runtime.load_family_boundary_inputs(self.cfg, self.tokenizer)
        self.assertEqual((len(rows), len(dev), len(broad), len(schedule)), (256, 64, 64, 1024))
        self.assertEqual(self.manifest["cycles"], 16)
        self.assertEqual(audit["arms"]["paths"]["presentations"], 4096)
        self.assertEqual(len({row["problem_id"] for row in rows}), 64)
        self.assertEqual(audit["planned_arms"], ["paths", "gcm"])
        self.assertEqual(audit["compatibility_only_arms"], ["repeat", "surface"])
        self.assertEqual(runtime.load_family_boundary_inputs(self.cfg)[3], schedule)
        for name in runtime.COPY_FILES:
            self.assertEqual((self.out / name).read_bytes(), (self.repo / runtime.ORIGINAL_DIR / name).read_bytes())

    def test_32_block_tier_and_complete_equal_exposure_schedule(self):
        problems, sources, _ = fixture_objects(33)
        blocks, rows, schedule, selection, cycles = runtime.build_boundary_payload(problems, sources)
        self.assertEqual((len(blocks), cycles, len(schedule)), (32, 8, 1024))
        self.assertEqual(selection["stages"]["training_selected"]["count"], 128)
        self.assertEqual(len(selection["omitted_packing_blocks"]), 1)
        self.assertEqual(len(rows["paths"]), 512)

    def test_incomplete_support_and_tiny_packing_are_not_ready(self):
        for change in ("incomplete", "tiny", "wrong_family", "wrong_seed"):
            sources = copy.deepcopy(self.sources)
            if change == "incomplete":
                sources["summary"]["join_complete"] = False
            elif change == "tiny":
                sources["packing"]["blocks"] = sources["packing"]["blocks"][:15]
                sources["packing"]["primal_block_count"] = sources["summary"]["packing_block_count"] = 15
            elif change == "wrong_family":
                sources["packing"]["blocks"][0]["representative"]["witnesses"]["p001"]["slots"][0]["record"]["family"] = "identity_present"
            else:
                sources["summary"]["config"]["training_seed"] = 17
            with self.subTest(change=change), self.assertRaises(ValueError):
                runtime.build_boundary_payload(self.problems, sources)

    def test_repeated_question_and_changed_prompt_rejected(self):
        for change in ("repeat", "prompt"):
            sources = copy.deepcopy(self.sources)
            if change == "repeat":
                sources["packing"]["blocks"][1] = copy.deepcopy(sources["packing"]["blocks"][0])
            else:
                sources["packing"]["blocks"][0]["representative"]["witnesses"]["p001"]["slots"][0]["record"]["prompt"] += " new"
            with self.subTest(change=change), self.assertRaises(ValueError):
                runtime.build_boundary_payload(self.problems, sources)

    def test_unplanned_arm_recipe_and_seed_changes_rejected(self):
        for key, value in (("arm", "surface"), ("seed", 17), ("eval_seed", 31), ("steps", 1023),
                           ("model_role", "debug"), ("microbatch_size", 1), ("learning_rate", 1e-5)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                runtime.load_family_boundary_inputs(dict(self.cfg, **{key: value}))

    def test_plain_byte_tamper_fails_hash_check(self):
        with (self.out / "train_paths.jsonl").open("a") as stream:
            stream.write("\n")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            runtime.load_family_boundary_inputs(self.cfg)

    def test_rehashed_row_tamper_still_fails_source_reconstruction(self):
        path = self.out / "train_paths.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["round_id"] = 99
        write_jsonl(path, rows)
        self.rehash_artifact(path.name)
        with self.assertRaisesRegex(ValueError, "rows differ"):
            runtime.load_family_boundary_inputs(self.cfg)

    def test_rehashed_schedule_tamper_still_fails_seeded_reconstruction(self):
        path = self.out / "schedule_seed31.json"
        schedule = json.loads(path.read_text())
        schedule[0], schedule[1] = schedule[1], schedule[0]
        write_json(path, schedule)
        self.rehash_artifact(path.name)
        with self.assertRaisesRegex(ValueError, "Schedule differs"):
            runtime.load_family_boundary_inputs(self.cfg)

    def test_rehashed_dev_change_does_not_bypass_original_bytes(self):
        path = self.out / "dev_matched.jsonl"
        path.write_text(path.read_text() + "\n")
        self.rehash_artifact(path.name)
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            runtime.load_family_boundary_inputs(self.cfg)

    def test_original_train_source_tamper_is_rejected(self):
        path = self.repo / runtime.ORIGINAL_DIR / "train_blocks.json"
        path.write_text(path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "Original frozen source changed"):
            runtime.load_family_boundary_inputs(self.cfg)

    def test_overlap_with_raw_holdout_and_duplicate_dev_are_rejected(self):
        split = json.loads((self.out / "split_allocation.json").read_text())
        dev = [json.loads(line) for line in (self.out / "dev_matched.jsonl").read_text().splitlines()]
        broad = [json.loads(line) for line in (self.out / "dev_broad.jsonl").read_text().splitlines()]
        original = list(self.problems.values())[:64]
        split["groups"]["holdout_reserved"].append(original[0]["numbers"])
        with self.assertRaisesRegex(ValueError, "split groups overlap"):
            runtime.check_split_membership(original, dev, broad, split)
        split["groups"]["holdout_reserved"].pop()
        with self.assertRaises(ValueError):
            runtime.check_split_membership(original, dev, [dev[0]] + broad[1:], split)

    def test_output_overwrite_refused_and_frozen_file_list_complete(self):
        with self.assertRaises(FileExistsError):
            preparation.prepare_absent_boundary(self.out, Path("unused"), repo=self.repo)
        self.assertEqual(set(self.manifest["files_sha256"]), runtime.DATA_FILES)
        self.assertEqual(set(path.name for path in self.out.iterdir()), runtime.DATA_FILES | {"manifest.json"})


if __name__ == "__main__":
    unittest.main()
