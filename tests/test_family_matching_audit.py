import unittest
from scripts.audit_family_matching import policy_filter, per_problem_support, preview, FAMILIES
from src.path_family_matching import find_supported_keys, greedy_blocks


def record(pid, family, i, length=40):
    return {'problem_id':pid, 'family':family, 'structure_id':family+str(i),
            'ac_class':pid+family+str(i), 'n_supervised':length, 'n_prompt':7,
            'n_processed':length+7, 'expression':str(i), 'surface_compatible':True,
            'encodable':True, 'numeric_features':dict(identity_nodes=1 if family==FAMILIES[0] else 0,
                zero_nodes=0,one_nodes=0,negative_nodes=0,fraction_nodes=0,depth=3,
                max_abs_intermediate=10,operators={'+':3})}


class AuditTests(unittest.TestCase):
    def test_first_representative_loses_cross_family_choice(self):
        rows = [record('p',f,i) for f in FAMILIES for i in range(4)]
        for r in rows:
            r['structure_id'] = r['expression']
        self.assertTrue(per_problem_support(rows)['p']['structure_matched'])
        selected = policy_filter(rows,'first_representative')
        self.assertEqual(len(selected),4)
        self.assertFalse(per_problem_support(selected)['p']['raw_disjoint'])

    def test_token_support_cannot_combine_lengths(self):
        rows = [record('p', f, i, 40+j) for j,f in enumerate(FAMILIES) for i in range(4)]
        s=per_problem_support(rows)['p']
        self.assertTrue(s['raw_disjoint'])
        self.assertFalse(s['token_matched'])

    def test_variable_length_preview_has_equal_positive_padding(self):
        rows = [record(str(j),f,i,40+j) for j in range(4) for f in FAMILIES for i in range(4)]
        keys=find_supported_keys(rows)['keys']
        blocks,totals=preview(greedy_blocks(keys)['blocks'])
        self.assertEqual(len(blocks),1)
        values=list(totals.values())
        self.assertTrue(all(v['padding_tokens']==8 for v in values))
        self.assertTrue(all(v['presentations']==16 for v in values))
        for family in FAMILIES:
            b=blocks[0]['conditions']
            for i in range(4):
                self.assertEqual(len({u['records'][i]['ac_class'] for u in b[family+'_paths']}),4)
                self.assertEqual(len({u['records'][i]['ac_class'] for u in b[family+'_gcm']}),1)

    def test_surface_independent_of_primary(self):
        rows=[record('p',f,i) for f in FAMILIES for i in range(4)]
        rows[0]['surface_compatible']=False
        self.assertTrue(per_problem_support(rows)['p']['structure_matched'])
        self.assertFalse(per_problem_support(policy_filter(rows,'surface'))['p']['structure_matched'])

if __name__=='__main__':
    unittest.main()
