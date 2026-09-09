import itertools
import random
import unittest

from src.path_family_matching import (FAMILIES, family_structure_assignment,
                                      find_supported_keys, greedy_blocks, slot_assignment)


SI = tuple("abcd")
SN = tuple("wxyz")


def row(pid, length, family, structure, ac_class, **extra):
    return {"problem_id": pid, "n_supervised": length, "family": family,
            "structure_id": structure, "ac_class": ac_class, **extra}


def simple_problem(pid="p0", length=20, si=SI, sn=SN):
    return [row(pid, length, family, structure, f"{family}:{structure}")
            for family, structures in zip(FAMILIES, (si, sn)) for structure in structures]


def simple_block(si=SI, sn=SN):
    return [record for p in range(4) for record in simple_problem(f"p{p}", 20 + p, si, sn)]


def brute_assignment_exists(records, si, sn):
    """Independent exhaustive choice-set oracle; no augmenting path algorithm."""
    choices = [{r["ac_class"] for r in records
                if r["family"] == family and r["structure_id"] == structure}
               for family, structures in zip(FAMILIES, (si, sn)) for structure in structures]
    choices.sort(key=len)

    def visit(position, used):
        if position == len(choices):
            return True
        return any(visit(position + 1, used | {candidate})
                   for candidate in choices[position] - used)

    return visit(0, set())


def brute_keys(records):
    domains = {family: sorted({r["structure_id"] for r in records if r["family"] == family})
               for family in FAMILIES}
    by_problem_length = {}
    for r in records:
        by_problem_length.setdefault(r["problem_id"], {}).setdefault(r["n_supervised"], []).append(r)
    found = {}
    for si in itertools.combinations(domains[FAMILIES[0]], 4):
        for sn in itertools.combinations(domains[FAMILIES[1]], 4):
            support = {}
            for pid, lengths in sorted(by_problem_length.items()):
                for length, inventory in sorted(lengths.items()):
                    if brute_assignment_exists(inventory, si, sn):
                        support[pid] = length
                        break
            if len(support) >= 4:
                found[(si, sn)] = support
    return found


class PathFamilyMatchingTests(unittest.TestCase):
    def assert_witness(self, witness, expected_pid=None):
        self.assertIsNotNone(witness)
        self.assertEqual(len(witness["slots"]), 8)
        self.assertEqual(len({s["ac_class"] for s in witness["slots"]}), 8)
        if expected_pid is not None:
            self.assertEqual(witness["problem_id"], expected_pid)
        for family in FAMILIES:
            selected = [s for s in witness["slots"] if s["family"] == family]
            self.assertEqual(len(selected), 4)
            self.assertEqual(len({s["structure_id"] for s in selected}), 4)
        for slot in witness["slots"]:
            self.assertEqual(slot["record"]["problem_id"], witness["problem_id"])
            self.assertEqual(slot["record"]["n_supervised"], witness["n_supervised"])
            for field in ("family", "structure_id", "ac_class"):
                self.assertEqual(slot[field], slot["record"][field])

    def test_fixed_slots_and_distinct_family_structure_tuples(self):
        witness = slot_assignment(simple_problem(), SI, SN)
        self.assert_witness(witness, "p0")
        self.assertEqual({s["structure_id"] for s in witness["slots"] if s["family"] == FAMILIES[0]}, set(SI))
        self.assertEqual({s["structure_id"] for s in witness["slots"] if s["family"] == FAMILIES[1]}, set(SN))

    def test_mixed_ac_classes_are_not_double_counted(self):
        records = [row("p0", 20, family, structure, structure)
                   for family in FAMILIES for structure in SI]
        self.assertIsNone(slot_assignment(records, SI, SI))
        self.assertIsNone(family_structure_assignment(records))
        # Providing a second class at every absent slot enables eight distinct classes.
        records += [row("p0", 20, FAMILIES[1], structure, "new:" + structure) for structure in SI]
        self.assert_witness(slot_assignment(records, SI, SI))
        self.assert_witness(family_structure_assignment(records))

    def test_augmenting_path_reassigns_earlier_slot(self):
        records = simple_problem()
        records = [r for r in records if not (r["family"] == FAMILIES[0] and r["structure_id"] in ("a", "b"))]
        records += [row("p0", 20, FAMILIES[0], "a", ac) for ac in ("0-shared", "1-alternative")]
        records += [row("p0", 20, FAMILIES[0], "b", "0-shared")]
        witness = slot_assignment(records, SI, SN)
        self.assert_witness(witness)
        assignments = {s["structure_id"]: s["ac_class"] for s in witness["slots"]}
        self.assertEqual(assignments["a"], "1-alternative")
        self.assertEqual(assignments["b"], "0-shared")

    def test_local_ac_bottleneck_defeats_counts_and_raw_structure_support(self):
        records = []
        for pid in ("p0", "p1", "p2", "p3"):
            inventory = simple_problem(pid)
            for r in inventory:
                if r["structure_id"] in ("a", "w"):
                    r["ac_class"] = "forced-shared"
            inventory.append(row(pid, 20, FAMILIES[0], "b", "extra-class"))
            self.assertEqual(len({r["ac_class"] for r in inventory}), 8)
            self.assertIsNone(slot_assignment(inventory, SI, SN))
            self.assertIsNone(family_structure_assignment(inventory))
            records.extend(inventory)
        result = find_supported_keys(records)
        self.assertTrue(result["complete"])
        self.assertEqual(result["counters"]["raw_key_pairs_support_at_least_four"], 1)
        self.assertEqual(result["keys"], [])

    def test_unfixed_structure_flow_can_use_alternative_structure(self):
        records = simple_problem()
        for r in records:
            if r["structure_id"] in ("a", "w"):
                r["ac_class"] = "forced-shared"
        records.append(row("p0", 20, FAMILIES[0], "e", "alternative-structure-class"))
        self.assertIsNone(slot_assignment(records, SI, SN))
        witness = family_structure_assignment(records)
        self.assert_witness(witness)
        self.assertIn("e", {s["structure_id"] for s in witness["slots"]})
        too_few = [r for r in records if r["family"] != FAMILIES[1] or r["structure_id"] != "w"]
        self.assertIsNone(family_structure_assignment(too_few))

    def test_different_problem_lengths_share_key_and_choose_lowest_feasible(self):
        records = simple_block()
        # Add a larger complete length and an incomplete smaller length to p0.
        records += simple_problem("p0", 30)
        records += simple_problem("p0", 10)[:-1]
        result = find_supported_keys(records)
        self.assertTrue(result["complete"])
        self.assertEqual(result["length_mode"], "variable_per_problem")
        self.assertEqual(len(result["keys"]), 1)
        key = result["keys"][0]
        self.assertNotIn("n_supervised", key)
        self.assertEqual({pid: w["n_supervised"] for pid, w in key["witnesses"].items()},
                         {f"p{p}": 20 + p for p in range(4)})
        blocks = greedy_blocks(result["keys"])
        self.assertEqual(blocks["n_blocks"], 1)
        self.assertEqual(len({w["n_supervised"] for w in blocks["blocks"][0]["witnesses"].values()}), 4)

    def test_cannot_stitch_one_problem_across_lengths(self):
        records = simple_block()
        for r in records:
            if r["family"] == FAMILIES[1]:
                r["n_supervised"] += 100
        result = find_supported_keys(records)
        self.assertTrue(result["complete"])
        self.assertEqual(result["counters"]["raw_key_pairs_support_at_least_four"], 1)
        self.assertEqual(result["keys"], [])

    def test_four_occurrences_of_one_problem_do_not_make_four_problem_support(self):
        records = [r for length in range(20, 24) for r in simple_problem("p0", length)]
        result = find_supported_keys(records)
        self.assertTrue(result["complete"])
        self.assertEqual(result["counters"]["key_pair_checks"], 0)
        self.assertEqual(result["keys"], [])

    def test_pruned_search_matches_small_exhaustive_reference(self):
        rng = random.Random(812)
        records = []
        for p in range(6):
            for length in (20, 21):
                for family, base in zip(FAMILIES, (SI, SN)):
                    for structure in (*base, "extra", "rare"):
                        if structure == "rare" and p >= 3:
                            continue
                        guaranteed = p < 4 and length == 20 + p % 2 and structure in base
                        if guaranteed or rng.random() < .55:
                            records.append(row(f"p{p}", length, family, structure, f"{family}:{structure}"))
                            if rng.random() < .3:
                                records.append(row(f"p{p}", length, family, structure, "shared"))
        expected = brute_keys(records)
        self.assertTrue(expected)
        result = find_supported_keys(records)
        self.assertTrue(result["complete"])
        actual = {(tuple(key["identity_structures"]), tuple(key["nonidentity_structures"])):
                  {pid: w["n_supervised"] for pid, w in key["witnesses"].items()}
                  for key in result["keys"]}
        self.assertEqual(actual, expected)
        self.assertFalse(any("rare" in si or "rare" in sn for si, sn in actual))
        for key in result["keys"]:
            for witness in key["witnesses"].values():
                self.assert_witness(witness)

    def test_deterministic_record_order_and_representative_selection(self):
        records = simple_block(si=tuple("abcde"))
        records += [{**records[0], "response": "z-last"}, {**records[0], "response": "a-first"}]
        rng = random.Random(7)
        shuffled = list(records)
        rng.shuffle(shuffled)
        a, b = find_supported_keys(records), find_supported_keys(shuffled)
        a.pop("elapsed_seconds")
        b.pop("elapsed_seconds")
        self.assertEqual(a, b)
        self.assertEqual(greedy_blocks(a["keys"]), greedy_blocks(reversed(b["keys"])))
        inventory = [r for r in records if r["problem_id"] == "p0"]
        self.assertEqual(slot_assignment(inventory, SI, SN), slot_assignment(reversed(inventory), tuple(reversed(SI)), SN))
        self.assertEqual(family_structure_assignment(inventory), family_structure_assignment(reversed(inventory)))
        # A canonical-JSON representative is chosen even when duplicate records have extra fields.
        variants = [{**r, "response": text} for r in simple_problem() for text in ("z", "a")]
        witness = slot_assignment(variants, SI, SN)
        self.assertTrue(all(s["record"]["response"] == "a" for s in witness["slots"]))

    def test_caps_preserve_found_keys_and_do_not_claim_exhaustion(self):
        records = simple_block(si=tuple("abcde"))
        result = find_supported_keys(records, max_key_pair_checks=1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["stop_reason"], "key_pair_checks_cap")
        self.assertEqual(result["counters"]["key_pair_checks"], 1)
        self.assertEqual(len(result["keys"]), 1)
        self.assertEqual(result["supported_union_interpretation"],
                         "discovered_feasible_support_only_not_an_upper_bound")
        for kwargs, reason, counter in (
            ({"max_key_pair_checks": 0}, "key_pair_checks_cap", "key_pair_checks"),
            ({"max_structure_nodes": 0}, "structure_nodes_cap", "structure_nodes"),
        ):
            capped = find_supported_keys(records, **kwargs)
            self.assertFalse(capped["complete"])
            self.assertEqual(capped["stop_reason"], reason)
            self.assertEqual(capped["counters"][counter], 0)
            self.assertEqual(capped["keys"], [])
        # Consuming exactly the last required check is complete, not spuriously capped.
        exact = find_supported_keys(simple_block(), max_key_pair_checks=1, max_structure_nodes=8)
        self.assertTrue(exact["complete"])
        self.assertEqual(exact["counters"]["structure_nodes"], 8)

    def test_deadline_discards_unfinished_key(self):
        class TickClock:
            def __init__(self):
                self.tick = -1

            def __call__(self):
                self.tick += 1
                return float(self.tick)

        # 32 rows + 4 mask checks + 8 prefix nodes + pair check = 45 ticks;
        # permit one problem witness, then stop before the whole key is verified.
        result = find_supported_keys(simple_block(), max_seconds=49, clock=TickClock())
        self.assertFalse(result["complete"])
        self.assertEqual(result["stop_reason"], "deadline")
        self.assertEqual(result["stop_stage"], "exact_assignment")
        self.assertGreater(result["counters"]["slot_assignment_checks"], 0)
        self.assertEqual(result["keys"], [])

    def test_greedy_is_disjoint_but_not_claimed_maximal(self):
        def key(tag, pids):
            return {"identity_structures": [tag + x for x in SI], "nonidentity_structures": list(SN),
                    "problem_ids": pids, "witnesses": {pid: {"problem_id": pid} for pid in pids}}

        keys = [key("a", ["p0", "p1", "p2", "p3", "p4"]),
                key("b", ["p0", "p1", "p5", "p6"]),
                key("c", ["p2", "p3", "p7", "p8"])]
        packed = greedy_blocks(keys)
        self.assertEqual(packed["n_selected_problems"], 4)
        self.assertEqual(len(packed["supported_problem_ids"]), 9)
        self.assertFalse(packed["maximum_packing_claimed"])
        self.assertIn("need not maximize", packed["warning"])
        # The latter two keys exhibit an alternative feasible packing of eight.
        self.assertEqual(greedy_blocks(keys[1:])["n_selected_problems"], 8)
        selection = [pid for block in packed["blocks"] for pid in block["problem_ids"]]
        self.assertEqual(len(selection), len(set(selection)))

    def test_invalid_inputs_rejected_and_empty_search_is_complete(self):
        self.assertIsNone(slot_assignment([], SI, SN))
        self.assertIsNone(family_structure_assignment([]))
        self.assertTrue(find_supported_keys([])["complete"])
        with self.assertRaises(ValueError):
            slot_assignment(simple_problem(), tuple("aabc"), SN)
        for records in (simple_problem("p0") + simple_problem("p1"),
                        simple_problem("p0", 20) + simple_problem("p0", 21)):
            with self.assertRaises(ValueError):
                slot_assignment(records, SI, SN)
            with self.assertRaises(ValueError):
                family_structure_assignment(records)
        for field, value in (("n_supervised", True), ("n_supervised", 0), ("family", "other"),
                             ("problem_id", ""), ("ac_class", None), ("extra", float("nan"))):
            with self.assertRaises(ValueError):
                find_supported_keys([{**simple_problem()[0], field: value}])
        for kwargs in ({"max_key_pair_checks": -1}, {"max_structure_nodes": True},
                       {"max_seconds": 0}, {"max_seconds": float("nan")}):
            with self.assertRaises(ValueError):
                find_supported_keys([], **kwargs)


if __name__ == "__main__":
    unittest.main()
