import copy,unittest
from experiments.p010.settlement_d1 import settle,summary


class Settlement(unittest.TestCase):
    def setUp(self):
        self.p=dict(app_id='app',state='stopped',owned_count=0,created_at='2026-10-20T02:10:00Z',stopped_at='2026-10-20T03:20:00Z')
        self.rows=[dict(object_id='app',interval_start='2026-10-20T02:00:00',cost='1.001'),dict(object_id='app',interval_start='2026-10-20T03:00:00',cost='.999')]
    def test_floor_and_rounding(self):
        x=settle('app','8',self.p,self.rows,['2.001']);self.assertEqual(x['charged_usd'],'2.41');self.assertEqual(x['released_usd'],'5.59')
    def test_missing_owned_proof_keeps_reserve(self):self.assertEqual(settle('app',8,None,self.rows,[])['charged_usd'],'8')
    def test_live_rejected(self):
        self.p['state']='ephemeral'
        with self.assertRaises(ValueError):settle('app',8,self.p,self.rows,[])
    def test_missing_last_hour_rejected(self):
        with self.assertRaises(ValueError):settle('app',8,self.p,self.rows[:1],[])
    def test_unrelated_cost_excluded(self):
        self.rows.append(dict(object_id='unrelated',interval_start='2026-10-20T03:00:00',cost='900'))
        self.assertEqual(settle('app',8,self.p,self.rows,[])['charged_usd'],'2.40')
    def test_negative_netting_rejected(self):
        self.rows[0]['cost']='-1'
        with self.assertRaises(ValueError):settle('app',8,self.p,self.rows,[])
    def test_nonzero_owned_rejected(self):
        self.p['owned_count']=1
        with self.assertRaises(ValueError):settle('app',8,self.p,self.rows,[])
    def test_high_actual_not_capped_at_old_reserve(self):self.assertEqual(settle('app',1,self.p,self.rows,[])['charged_usd'],'2.40')
    def test_exact_total_and_id_roster_required(self):
        with self.assertRaises(ValueError):summary([settle('app',8,None,self.rows,[])]*6)


if __name__=='__main__':unittest.main()
