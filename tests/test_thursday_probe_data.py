import json
import unittest
from collections import Counter
from fractions import Fraction
from pathlib import Path
import tempfile

from experiments.thursday_probe.common import (motifs, path_record, operations, digest,
    learning_rates, epoch_schedule, dump, verify_manifest)
from experiments.thursday_probe.data import build_arms, compute_row, exercise_sets, prefixes
from src.countdown_smoke import safe_parse, value, verify_expression, canonical
from src.pilot_data import verify_row
from src.sft_data import sha256_file
from src.trace_audit import audit_trace


class ThursdayDataTests(unittest.TestCase):
    def test_directed_adjacent_interface_not_bag_of_operators(self):
        a = safe_parse('(9-3)*7')
        b = safe_parse('(9*7)-3')
        self.assertEqual(motifs(a), {'-->*': 1})
        self.assertEqual(motifs(b), {'*->-': 1})
        self.assertEqual(Counter(x[0] for x in operations(a)), Counter(x[0] for x in operations(b)))

    def test_whitelist_and_input_use(self):
        self.assertFalse(verify_expression('__import__("os").system("id")', [1,2,3,4], 10))
        self.assertFalse(verify_expression('(1+2)+(3+3)', [1,2,3,4], 9))
        self.assertFalse(verify_expression('1/(2-2)+4', [1,2,3,4], 10))
        self.assertEqual(value(safe_parse('(3/7)*14')), 6)

    def test_prep_probe_disjointness_and_operator_equality(self):
        x = exercise_sets('-->*')
        self.assertEqual(len(x['probes']), 96)
        self.assertEqual(Counter(r['category'] for r in x['probes']), {'atomic':32,'control':32,'target':32})
        self.assertEqual(x['prep_control'][:128], x['prep_bridge'][:128])
        for branch in ('prep_control','prep_bridge'):
            self.assertEqual(len(x[branch]), 256)
            self.assertFalse({r['number_group_hash'] for r in x[branch]} & {r['number_group_hash'] for r in x['probes']})
        cs = [Counter(op for r in x[k][128:] for op,count in r['operators'].items() for _ in range(count))
              for k in ('prep_control','prep_bridge')]
        self.assertEqual(cs[0], cs[1])
        self.assertTrue(all('-->*' in r['interfaces'] for r in x['prep_bridge'][128:]))
        self.assertTrue(all('-->*' not in r['interfaces'] for r in x['prep_control'][128:]))

    def test_balanced_three_arms_and_independent_resources(self):
        # Both programs reach 24 using exactly the same four inputs.
        a, b = map(safe_parse, ['(8-4)*(7-1)', '(8*4)-(7+1)'])
        self.assertEqual(value(a), value(b))
        ps=[]
        for i in range(8):
            paths = {'A': path_record(a), 'B': path_record(b)}
            for r in paths.values(): r['supervised_tokens_v0'] = 70
            ps.append({'problem_id':str(i),'target':24,'numbers':[1,4,7,8],
                       'prompt':'fixture','paths':paths})
        arms, assignment = build_arms(ps)
        self.assertEqual(Counter(assignment.values()), {'A':4,'B':4})
        for arm, rows in arms.items():
            self.assertEqual(Counter(r['coarse_path'] for r in rows), {'A':8,'B':8})
            self.assertEqual(Counter(r['rendering_id'] for r in rows), {0:8,1:8})
            for row in rows:
                verify_row(row)
                self.assertEqual(audit_trace(row['response'], row['numbers'],24)['complete_trace_status'],'verified')
            for i in range(8):
                group=[r for r in rows if r['problem_id']==str(i)]
                self.assertEqual(len({r['path_id'] for r in group}),2 if arm=='paths' else 1)
                self.assertEqual(len({r['response'] for r in group}),1 if arm=='repeat' else 2)

    def test_schedule_full_epochs_and_remainder(self):
        schedule=epoch_schedule(253,2,8)
        self.assertEqual(len(schedule),64)
        self.assertEqual([len(schedule[31]),len(schedule[63])],[5,5])
        self.assertEqual(Counter(i for b in schedule for i in b),dict.fromkeys(range(253),2))
        self.assertEqual(len(epoch_schedule(512,8,16)),256)
        lr=learning_rates(64)
        self.assertAlmostEqual(sum(lr),.003505)
        self.assertEqual(lr[-1],1e-5)
        self.assertTrue(all(x>0 for x in lr))

    def test_immutable_manifest_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); dump(p/'a.json',{'a':1})
            dump(p/'manifest.json',{'files_sha256':{'a.json':sha256_file(p/'a.json')}})
            verify_manifest(p)
            with self.assertRaises(FileExistsError):dump(p/'a.json',{'a':2})
            (p/'a.json').write_text('{}')
            with self.assertRaises(ValueError):verify_manifest(p)


if __name__=='__main__':unittest.main()
