import unittest
from experiments.sft_allocation_acquisition.contract import roster,completion,assess,summarize

class AcquisitionContractTests(unittest.TestCase):
    def test_finite_roster(self):
        p=[dict(id=str(i),rank=i+1) for i in range(128)]
        b=roster(p);items=[x for y in b for x in y['items']]
        self.assertEqual((len(b),len(items),len({r['candidate_id'] for r in items})),(40,1024,1024))
        self.assertEqual([r['attempt'] for r in items if r['problem_id']=='0'],list(range(1,9)))
    def test_native_eos_and_padding(self):
        r=completion([12,151645,151643,151643]);self.assertEqual(r['token_ids'],[12,151645])
        self.assertTrue(r['eos']);self.assertFalse(r['truncated'])
    def test_unknown_stop_rejected(self):
        with self.assertRaises(ValueError):completion([1,2,3])
        with self.assertRaises(ValueError):completion([1,151645,2])
    def test_length_capped_correct_is_not_usable(self):
        s=completion([1]*1024)
        r=assess({'answer':'42'},r'\boxed{42}',s,{})
        self.assertTrue(r['score']['answer_correct']);self.assertFalse(r['usable'])
    def test_duplicate_has_cost_bearing_record(self):
        s=completion([1,151645]);r=assess({'answer':'42'},r'\boxed{42}',s,{})
        self.assertTrue(r['usable'])
        second=assess({'answer':'42'},'  '+r'\boxed{42}'+'  ',s,{r['normalized_text_sha256']:'p::1'})
        self.assertFalse(second['usable']);self.assertEqual(second['duplicate_of'],'p::1')
    def test_wrong_conflict_and_no_gold_search(self):
        s=completion([1,151645])
        for text in [r'\boxed{43}',r'\boxed{42} and \boxed{43}','42']:
            self.assertFalse(assess({'answer':'42'},text,s,{})['usable'])
    def test_empty_parent_stays_censored(self):
        r=summarize([{'id':'a'},{'id':'b'}],[])
        self.assertEqual(r['parents'],2);self.assertEqual(r['supply'][0]['right_censored_k'],[1,2,4])
    def test_invalid_duplicates_are_not_double_charged_or_double_counted_as_usable(self):
        parents=[{'id':'p','answer':'42'}];seen={};records=[]
        for n,text in enumerate([r'\boxed{43}',r'\boxed{43}',r'\boxed{42}',r'\boxed{42}'],1):
            stop=completion([1,151645]);v=assess(parents[0],text,stop,seen)
            cid=f'p::{n}';seen.setdefault(v['normalized_text_sha256'],cid)
            records.append(dict(problem_id='p',candidate_id=cid,attempt=n,stop=stop,**v))
        r=summarize(parents,records)
        self.assertEqual((r['recorded_outputs'],r['usable'],r['wrong_or_unusable'],r['rejected_valid_duplicates']),(4,1,2,1))
        self.assertEqual(r['duplicates'],2)

    def test_reference_not_in_prompt(self):
        from experiments.sft_allocation_acquisition.contract import messages
        r=messages({'problem':'Compute six times seven.','answer':'42','reference':'SECRET_GOLD'})
        self.assertEqual(r[1],{'role':'user','content':'Compute six times seven.'})
        self.assertNotIn('SECRET_GOLD',str(r));self.assertNotIn('42',str(r))

if __name__=='__main__':unittest.main()
