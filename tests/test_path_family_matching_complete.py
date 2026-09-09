import hashlib
import itertools
import json
import random
import unittest
from unittest import mock

from src.path_family_matching import FAMILIES, find_supported_keys
import src.path_family_matching_complete as complete_join
from src.path_family_matching_complete import (canonical_json_line,
                                               complete_supported_key_join,
                                               record_reference)
from tests.test_path_family_matching import (SI, SN, brute_assignment_exists,
                                             row, simple_block, simple_problem)


def compact_naive_key(key):
    compact = {"identity_structures": key["identity_structures"],
               "nonidentity_structures": key["nonidentity_structures"],
               "problem_ids": key["problem_ids"], "witnesses": {}}
    for pid, witness in key["witnesses"].items():
        compact["witnesses"][pid] = {
            "problem_id": pid, "n_supervised": witness["n_supervised"],
            "slots": [{"family": slot["family"], "structure_id": slot["structure_id"],
                       "ac_class": slot["ac_class"], "record_ref": record_reference(slot["record"])}
                      for slot in witness["slots"]]}
    return compact


def signature(key):
    return tuple(key["identity_structures"]), tuple(key["nonidentity_structures"])


class CompleteFamilyJoinTests(unittest.TestCase):
    def assert_matches_naive(self, records):
        expected = find_supported_keys(records, max_key_pair_checks=1_000_000,
                                       max_structure_nodes=1_000_000, clock=lambda: 0.0)
        self.assertTrue(expected["complete"])
        streamed = []
        actual = complete_supported_key_join(records, on_key=streamed.append, clock=lambda: 0.0)
        self.assertTrue(actual["complete"])
        self.assertEqual({signature(key): key for key in streamed},
                         {signature(key): compact_naive_key(key) for key in expected["keys"]})
        self.assertEqual(actual["valid_key_count"], len(streamed))
        self.assertEqual(actual["supported_problem_ids"], expected["supported_problem_ids"])
        self.assertEqual(actual["represented_pairs"], actual["total_candidate_pairs"])
        self.assertEqual(actual["represented_pairs"], actual["pruned_pairs"] + actual["exact_pairs"])
        self.assertEqual(actual["unrepresented_pairs"], 0)
        self.assertEqual(actual["counters"]["started_exact_pairs"], actual["exact_pairs"])
        self.assertEqual(actual["key_stream_sha256"],
                         hashlib.sha256(b"".join(canonical_json_line(key) for key in streamed)).hexdigest())
        return actual, streamed

    def test_variable_lengths_and_compact_record_references_match_naive(self):
        records = simple_block()
        records += simple_problem("p0", 30)
        records += simple_problem("p0", 10)[:-1]
        actual, streamed = self.assert_matches_naive(records)
        self.assertEqual(len(streamed), 1)
        self.assertEqual({pid: w["n_supervised"] for pid, w in streamed[0]["witnesses"].items()},
                         {f"p{p}": 20 + p for p in range(4)})
        by_ref = {record_reference(record): record for record in records}
        for pid, witness in streamed[0]["witnesses"].items():
            for slot in witness["slots"]:
                self.assertNotIn("record", slot)
                self.assertEqual(by_ref[slot["record_ref"]]["problem_id"], pid)
        self.assertEqual(actual["support_group_count"], 1)

    def test_same_masks_do_not_imply_same_ac_feasibility(self):
        records = simple_block(si=tuple("abcde"))
        for record in records:
            if record["structure_id"] in ("a", "w"):
                record["ac_class"] = "forced-shared"
        actual, keys = self.assert_matches_naive(records)
        self.assertEqual(actual["mask_groups_by_family"], {family: 1 for family in FAMILIES})
        self.assertEqual(actual["total_candidate_pairs"], 5)
        self.assertEqual(actual["exact_pairs"], 5)
        self.assertEqual(actual["valid_key_count"], 1)
        self.assertEqual(keys[0]["identity_structures"], list("bcde"))

    def test_cross_length_stitching_and_mixed_classes_remain_invalid(self):
        split = simple_block()
        for record in split:
            if record["family"] == FAMILIES[1]:
                record["n_supervised"] += 100
        actual, keys = self.assert_matches_naive(split)
        self.assertEqual(actual["exact_pairs"], 1)
        self.assertEqual(keys, [])
        mixed = [row(f"p{p}", 20, family, structure, structure)
                 for p in range(4) for family in FAMILIES for structure in SI]
        actual, keys = self.assert_matches_naive(mixed)
        self.assertEqual(actual["valid_key_count"], 0)
        self.assertEqual(keys, [])

    def test_mask_group_product_pruned_and_fully_counted(self):
        records = [row(f"p{p}", 20, FAMILIES[0], structure, structure)
                   for p in range(4) for structure in "abcde"]
        records += [row(f"p{p}", 20, FAMILIES[1], structure, structure)
                    for p in range(4, 8) for structure in "uvwxy"]
        actual, keys = self.assert_matches_naive(records)
        self.assertEqual(actual["total_candidate_pairs"], 25)
        self.assertEqual(actual["pruned_pairs"], 25)
        self.assertEqual(actual["exact_pairs"], 0)
        self.assertEqual(actual["counters"]["group_pair_checks"], 1)
        self.assertEqual(actual["counters"]["pruned_group_pairs"], 1)
        self.assertEqual(keys, [])

    def test_multiple_mask_groups_and_support_groups_match_naive(self):
        records = simple_block(si=tuple("abcde"), sn=tuple("vwxyz"))
        # Only the base key has support from this additional fifth problem.
        records += simple_problem("p4", 31)
        actual, keys = self.assert_matches_naive(records)
        self.assertEqual(actual["valid_key_count"], 25)
        self.assertEqual(actual["support_group_count"], 2)
        self.assertEqual(sorted(g["valid_key_count"] for g in actual["support_groups"]), [1, 24])
        for group in actual["support_groups"]:
            eligible = [key for key in keys if key["problem_ids"] == group["problem_ids"]]
            self.assertEqual(group["representative_key"], min(eligible, key=signature))

    def test_random_small_inventory_complete_key_equality(self):
        rng = random.Random(991)
        records = simple_block()
        for p in range(6):
            for length in (20, 21):
                for family, structures in zip(FAMILIES, (tuple("abcde"), tuple("vwxyz"))):
                    for structure in structures:
                        if rng.random() < .7:
                            for ac in (f"{family}:{structure}", "shared"):
                                if ac != "shared" or rng.random() < .3:
                                    records.append(row(f"p{p}", length, family, structure, ac))
        self.assert_matches_naive(records)

    def test_deterministic_input_order_stream_and_representative(self):
        records = simple_block(si=tuple("abcde"))
        records += [{**records[0], "response": "z"}, {**records[0], "response": "a"}]
        shuffled = list(records)
        random.Random(4).shuffle(shuffled)
        first_stream, second_stream = [], []
        first = complete_supported_key_join(records, on_key=first_stream.append, clock=lambda: 0.0)
        second = complete_supported_key_join(shuffled, on_key=second_stream.append, clock=lambda: 0.0)
        self.assertEqual(first, second)
        self.assertEqual(first_stream, second_stream)
        self.assertEqual(first["support_group_count"], 1)
        self.assertEqual(first["support_groups"][0]["valid_key_count"], 5)
        self.assertNotIn("keys", first)

    def test_deadline_before_start_does_not_claim_no_solution(self):
        times = iter([0.0, 600.0, 600.0])
        result = complete_supported_key_join(simple_block(), clock=lambda: next(times))
        self.assertFalse(result["complete"])
        self.assertEqual(result["stop_reason"], "deadline")
        self.assertEqual(result["stop_stage"], "indexing")
        self.assertEqual(result["represented_pairs"], 0)
        self.assertIsNone(result["total_candidate_pairs"])
        self.assertFalse(result["cursor_is_standalone_resume_checkpoint"])

    def test_deadline_inside_pair_excludes_unfinished_decision_and_stream(self):
        current_time = [0.0]
        calls = [0]
        original = complete_join._slot_assignment

        def expire_after_one_assignment(*args):
            calls[0] += 1
            result = original(*args)
            current_time[0] = 600.0
            return result

        streamed = []
        with mock.patch.object(complete_join, "_slot_assignment", side_effect=expire_after_one_assignment):
            result = complete_supported_key_join(simple_block(), on_key=streamed.append,
                                                  clock=lambda: current_time[0])
        self.assertFalse(result["complete"])
        self.assertEqual(result["stop_stage"], "exact_assignment")
        self.assertEqual(result["total_candidate_pairs"], 1)
        self.assertEqual(result["counters"]["started_exact_pairs"], 1)
        self.assertEqual(result["exact_pairs"], 0)
        self.assertEqual(result["represented_pairs"], 0)
        self.assertEqual(result["unrepresented_pairs"], 1)
        self.assertEqual(result["valid_key_count"], 0)
        self.assertEqual(result["support_groups"], [])
        self.assertEqual(streamed, [])
        self.assertEqual(calls[0], 1)

    def test_stop_after_committed_key_keeps_once_only_accounting(self):
        now = [0.0]
        stream = []

        def write_and_expire(key):
            stream.append(key)
            now[0] = 600.0

        result = complete_supported_key_join(simple_block(si=tuple("abcde")),
                                              on_key=write_and_expire, clock=lambda: now[0])
        self.assertFalse(result["complete"])
        self.assertEqual(result["total_candidate_pairs"], 5)
        self.assertEqual(result["represented_pairs"], 1)
        self.assertEqual(result["exact_pairs"], 1)
        self.assertEqual(result["counters"]["started_exact_pairs"], 1)
        self.assertEqual(result["valid_key_count"], 1)
        self.assertEqual(result["support_groups"][0]["valid_key_count"], 1)
        self.assertEqual(result["unrepresented_pairs"], 4)
        self.assertEqual(result["key_stream_sha256"], hashlib.sha256(canonical_json_line(stream[0])).hexdigest())
        self.assertEqual(result["cursor"]["identity_tuple"], 1)

    def test_stop_after_group_pruning_does_not_double_count_product(self):
        records = [row(f"p{p}", 20, FAMILIES[0], structure, structure)
                   for p in range(4) for structure in "abcde"]
        records += [row(f"p{p}", 20, FAMILIES[1], structure, structure)
                    for p in range(4, 8) for structure in "uvwxy"]
        original = complete_join._TimeBudget.check

        def expire_at_completion(budget, stage):
            if stage == "completion":
                raise complete_join._Deadline(stage)
            return original(budget, stage)

        with mock.patch.object(complete_join._TimeBudget, "check", new=expire_at_completion):
            result = complete_supported_key_join(records, clock=lambda: 0.0)
        self.assertFalse(result["complete"])
        self.assertEqual(result["represented_pairs"], 25)
        self.assertEqual(result["pruned_pairs"], 25)
        self.assertEqual(result["unrepresented_pairs"], 0)
        self.assertEqual(result["counters"]["pruned_group_pairs"], 1)

    def test_stream_bytes_and_reference_are_explicit(self):
        record = {**simple_problem()[0], "response": "é"}
        expected = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        self.assertEqual(record_reference(record), hashlib.sha256(expected.encode()).hexdigest())
        self.assertEqual(canonical_json_line(record), (expected + "\n").encode())
        result = complete_supported_key_join([], clock=lambda: 0.0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["total_candidate_pairs"], 0)
        self.assertEqual(result["key_stream_sha256"], hashlib.sha256(b"").hexdigest())

    def test_per_family_mode_uses_actual_lengths_and_no_false_common_header(self):
        records = simple_block()
        for record in records:
            if record["family"] == FAMILIES[1]:
                record["n_supervised"] += 100
        # Incomplete smaller present length must not win the lexicographic choice.
        records += [r for r in simple_problem("p0", 10)[:3]]
        common = complete_supported_key_join(records, clock=lambda: 0.0)
        self.assertEqual(common["valid_key_count"], 0)
        stream = []
        separate = complete_supported_key_join(records, length_mode="per_family",
                                                on_key=stream.append, clock=lambda: 0.0)
        self.assertTrue(separate["complete"])
        self.assertEqual(separate["valid_key_count"], 1)
        refs = {record_reference(r): r for r in records}
        for p in range(4):
            witness = stream[0]["witnesses"][f"p{p}"]
            self.assertNotIn("n_supervised", witness)
            self.assertEqual(witness["family_lengths"],
                             {FAMILIES[0]: 20 + p, FAMILIES[1]: 120 + p})
            for slot in witness["slots"]:
                self.assertEqual(refs[slot["record_ref"]]["n_supervised"],
                                 witness["family_lengths"][slot["family"]])

    def test_per_family_mode_never_stitches_within_family_or_reuses_ac_class(self):
        split = simple_block()
        for record in split:
            if record["family"] == FAMILIES[0] and record["structure_id"] in ("c", "d"):
                record["n_supervised"] += 50
        result = complete_supported_key_join(split, length_mode="per_family", clock=lambda: 0.0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["valid_key_count"], 0)
        mixed = [row(f"p{p}", 20 + f, family, structure, structure)
                 for p in range(4) for f, family in enumerate(FAMILIES) for structure in SI]
        result = complete_supported_key_join(mixed, length_mode="per_family", clock=lambda: 0.0)
        self.assertEqual(result["valid_key_count"], 0)

    def test_per_family_small_complete_keys_match_independent_brute_force(self):
        rng = random.Random(319)
        records = []
        domains = {FAMILIES[0]: tuple("abcde"), FAMILIES[1]: tuple("vwxyz")}
        for p in range(5):
            for f, family in enumerate(FAMILIES):
                for length in (20 + f * 10, 21 + f * 10):
                    for structure in domains[family]:
                        guaranteed = p < 4 and length == 20 + f * 10 and structure in (SI if f == 0 else SN)
                        if guaranteed or rng.random() < .6:
                            records.append(row(f"p{p}", length, family, structure, f"{family}:{structure}"))
                            if rng.random() < .25:
                                records.append(row(f"p{p}", length, family, structure, "shared"))
        expected = {}
        for si in itertools.combinations(domains[FAMILIES[0]], 4):
            for sn in itertools.combinations(domains[FAMILIES[1]], 4):
                support = {}
                for pid in sorted({r["problem_id"] for r in records}):
                    problem = [r for r in records if r["problem_id"] == pid]
                    options = [{r["n_supervised"] for r in problem if r["family"] == family}
                               for family in FAMILIES]
                    for li, ln in itertools.product(sorted(options[0]), sorted(options[1])):
                        inventory = [r for r in problem if
                                     (r["family"] == FAMILIES[0] and r["n_supervised"] == li) or
                                     (r["family"] == FAMILIES[1] and r["n_supervised"] == ln)]
                        if brute_assignment_exists(inventory, si, sn):
                            support[pid] = {FAMILIES[0]: li, FAMILIES[1]: ln}
                            break
                if len(support) >= 4:
                    expected[(si, sn)] = support
        stream = []
        result = complete_supported_key_join(records, length_mode="per_family", on_key=stream.append,
                                              clock=lambda: 0.0)
        actual = {signature(key): {pid: witness["family_lengths"] for pid, witness in key["witnesses"].items()}
                  for key in stream}
        self.assertTrue(result["complete"])
        self.assertTrue(expected)
        self.assertEqual(actual, expected)
        self.assertEqual(result["represented_pairs"], result["total_candidate_pairs"])

    def test_callback_failure_propagates_and_invalid_deadlines_rejected(self):
        def failing_callback(key):
            raise OSError("synthetic write error")

        with self.assertRaises(OSError):
            complete_supported_key_join(simple_block(), on_key=failing_callback, clock=lambda: 0.0)
        for value in (0, -1, True, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                complete_supported_key_join([], max_seconds=value)
        with self.assertRaises(ValueError):
            complete_supported_key_join([], length_mode="unspecified")


if __name__ == "__main__":
    unittest.main()
