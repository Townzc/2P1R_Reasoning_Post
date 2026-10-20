import copy
import unittest
from experiments.p010.dataset_selection import select_grid, inventory
from experiments.p010.multi_answer_plan import make_plan, validate_plan


def row(pid, attempt, correct=True, text=None):
    return dict(candidate_id=f'{pid}::attempt{attempt:02d}', problem_id=pid,
        attempt=attempt, answer_text=text or f'full solution {attempt}',
        stop={'stop_reason': 'native_eos'}, usable=correct,
        score={'score': {'correct': correct, 'parsed': True, 'box_extracted': True}})


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ids=[f'p{i}' for i in range(3200)]
        cls.roster={'400':ids[:400],'3200':ids}
        cls.records={}
        for i,pid in enumerate(ids):
            for a in range(1,17 if i<400 else 2):
                x=row(pid,a);cls.records[x['candidate_id']]=x

    def test_fixed_attempt_order_nesting_and_question_coverage(self):
        result=select_grid('t7',self.records,self.roster)['cells']
        self.assertEqual([result[k]['N'] for k in ('n400_k1','n3200_k1','n400_k4','n400_k8')], [400,3200,1600,3200])
        self.assertFalse(result['n400_k8']['nesting_conflicts'])
        self.assertEqual(result['n400_k4']['selected_ids'][:4], [f'p0::attempt{i:02d}' for i in range(1,5)])

    def test_normalized_duplicates_do_not_fill_slots(self):
        data=copy.deepcopy(self.records)
        data['p0::attempt02']['answer_text']='  full   solution 1\n'
        r=select_grid('t72',data,self.roster)['cells']['n400_k4']
        self.assertEqual(r['selected_ids'][:4], ['p0::attempt01','p0::attempt03','p0::attempt04','p0::attempt05'])
        self.assertEqual(r['normalized_duplicates'][0]['duplicate_of'],'p0::attempt01')

    def test_unconfirmed_retry_is_not_a_failure(self):
        data=copy.deepcopy(self.records)
        data['p500::attempt01']=row('p500',1,False)
        with self.assertRaisesRegex(ValueError,'incomplete'):
            select_grid('t7',data,self.roster)

    def test_unverified_fallback_cannot_silently_break_nesting(self):
        data=copy.deepcopy(self.records)
        for a in range(1,5):data[f'p0::attempt{a:02d}']=row('p0',a,False)
        cells=select_grid('t7',data,self.roster)['cells']
        self.assertEqual(cells['n400_k1']['unverified_questions'],['p0'])
        self.assertEqual(cells['n400_k4']['selected_ids'][0],'p0::attempt05')
        self.assertTrue(cells['n400_k4']['selection_conflict_requires_owner_resolution'])

    def test_no_question_backfill_for_short_supply(self):
        data=copy.deepcopy(self.records)
        for pid in self.roster['400']:
            for a in range(3,17):data[f'{pid}::attempt{a:02d}']=row(pid,a,False)
        cells=select_grid('t15',data,self.roster,{
            str(n):[{'problem_id':p,'attempt':1,'path_id':f'{p}::attempt01','response':'full solution 1'}
                    for p in self.roster[str(n)]] for n in (400,3200)})['cells']
        self.assertEqual(cells['n400_k8']['N'],800)
        self.assertEqual(cells['n400_k8']['P_cov'],400)
        self.assertTrue(cells['n400_k8']['report_before_training'])

    def test_stop_box_and_identity_are_not_trusted_flags(self):
        for change in ({'stop':{'stop_reason':'length_cap'}},
                       {'score':{'score':{'correct':True,'parsed':True,'box_extracted':False}}},
                       {'attempt':True}):
            x=row('p0',1);x.update(change)
            with self.assertRaises(ValueError):inventory({'p0::attempt01':x})


class MultiAnswerPlanTests(unittest.TestCase):
    def encoded(self):
        rows=[]
        for i in range(8):
            size=4*2**i
            rows.append(dict(problem_id=f'p{i//4}',path_id=f'p{i//4}/a{i%4}',
                input_ids=[1,2]+[3]*(size-1)+[99],labels=[-100,-100]+[3]*(size-1)+[99],
                n_prompt=2,n_supervised=size,n_processed=size+2,response_hash=f'h{i}'))
        return rows

    def test_same_question_multiple_paths_exact_dose_and_exposure(self):
        rows=self.encoded();p=make_plan(rows,17,99)
        budget=validate_plan(rows,p,17,99)
        self.assertEqual(budget['supervised_response_tokens'],2097148)
        self.assertEqual(budget['optimizer_updates'],1024)
        self.assertEqual(len(budget['problem_exposures']),2)
        self.assertGreaterEqual(min(p['row_exposures']),1)
        p['lrs'][0]*=2
        with self.assertRaises(ValueError):validate_plan(rows,p,17,99)

    def test_unrepresentable_balanced_remainder_stays_a_failure(self):
        rows=self.encoded()
        for i,x in enumerate(rows):
            size=100+i
            x.update(input_ids=[1,2]+[3]*(size-1)+[99],
                     labels=[-100,-100]+[3]*(size-1)+[99],
                     n_supervised=size,n_processed=size+2)
        with self.assertRaisesRegex(ValueError,'No balanced exact'):
            make_plan(rows,17,99)

    def test_no_path_duplication_truncation_or_zero_exposure(self):
        rows=self.encoded()
        for mutation in ('duplicate','missing_eos','mask'):
            bad=copy.deepcopy(rows)
            if mutation=='duplicate':bad[1]['path_id']=bad[0]['path_id']
            elif mutation=='missing_eos':bad[0]['input_ids'][-1]=3
            else:bad[0]['labels'][0]=1
            with self.assertRaises(ValueError):make_plan(bad,17,99)
        large=[]
        for i in range(2200):
            x=copy.deepcopy(rows[0]);x.update(path_id=f'big{i}',input_ids=[1,2]+[3]*1023+[99],
                labels=[-100,-100]+[3]*1023+[99],n_supervised=1024,n_processed=1026);large.append(x)
        with self.assertRaisesRegex(ValueError,'exceeds original dose'):make_plan(large,17,99)


if __name__=='__main__':unittest.main()
