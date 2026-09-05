import unittest
from scripts.audit_exact_matching import matching_blocks


class ExactMatchingTests(unittest.TestCase):
    def test_common_inventory_keeps_problem_groups_disjoint(self):
        inventories = [{60: {s: {} for s in 'abcde'}} for _ in range(12)]
        blocks, _ = matching_blocks(inventories, 2)
        self.assertEqual(len(blocks), 2)
        indices = [i for b in blocks for i in b['indices']]
        self.assertEqual(len(indices), len(set(indices)))
        for b in blocks:
            for i in b['indices']:
                self.assertTrue(set(b['structures']) <= inventories[i][b['response_tokens']].keys())

    def test_same_structure_with_different_lengths_does_not_match(self):
        inventories = [{60+i: {s: {} for s in 'abcd'}} for i in range(4)]
        self.assertEqual(matching_blocks(inventories, 1)[0], [])

    def test_partial_structure_overlap_does_not_count_as_four_paths(self):
        inventories = [{60: {s: {} for s in ('abc'+str(i))}} for i in range(4)]
        self.assertEqual(matching_blocks(inventories, 1)[0], [])


if __name__ == '__main__':
    unittest.main()
