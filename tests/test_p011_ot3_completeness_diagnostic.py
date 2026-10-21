import gzip
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import diagnose_p011_ot3_completeness as d


def disposition(key,complete,length=None,leaked=False):
    return {'parent_sha256':d.rules.identity(key),'row_count':16,
            'flags':{'incomplete':not complete,'decontamination_hit':leaked,'any_overlength':length},
            'eligible':complete and not leaked and length is False}


class CompletenessDiagnosticTests(unittest.TestCase):
    def test_exact_original_complete_called(self):
        with patch.object(d.rules,'complete',wraps=d.rules.complete) as f:
            result=d.describe('<think>x</think>\\boxed{2}')
        f.assert_called_once_with('<think>x</think>\\boxed{2}')
        self.assertTrue(result['complete']);self.assertTrue(result['boxed_after_last_think'])

    def test_categories_and_null_semantics(self):
        cases=[('<think>unfinished','N1'),('\\boxed{1}'+'x'*2001,'N2'),
               ('<think>\\boxed{1}</think>answer','N3'),('</think>none','N4')]
        for text,category in cases:
            result=d.describe(text);self.assertEqual(result['category'],category)
            self.assertFalse(result['complete'])
        self.assertIsNone(d.describe('none')['boxed_after_last_think'])
        self.assertTrue(d.describe('\\boxed{1}'+'x'*2001)['Rprime_complete'])

    def test_last_think_and_exact_prefix(self):
        value=d.describe(' <think>\\boxed{1}</think>x</think>none')
        self.assertEqual(value['t'],2);self.assertEqual(value['category'],'N3')
        self.assertFalse(value['starts_with_think'])
        self.assertTrue(d.describe('prefix</think>\\boxed{1}')['complete'])

    def test_last2000_boundary_and_no_text_cleaning(self):
        self.assertTrue(d.describe('x'*20+'\\boxed{'+'a'*1993)['boxed_last2000'])
        self.assertFalse(d.describe('x'*20+'\\boxed{'+'a'*1994)['boxed_last2000'])
        self.assertFalse(d.describe('\\boxed {1}')['boxed_any'])
        with self.assertRaises(ValueError):d.describe(None)

    def test_exact_character_quantiles(self):
        self.assertEqual(d.quantiles([]),{'10':None,'50':None,'90':None,'99':None})
        self.assertEqual(d.quantiles([7]),{'10':7,'50':7,'90':7,'99':7})
        self.assertEqual(d.quantiles([10,0])['50'],5)
        self.assertAlmostEqual(d.quantiles([10,0])['99'],9.9)

    def test_unknown_length_not_imputed(self):
        s=d.Summary();rows=[s.row(str(i),'\\boxed{1}'+'x'*2001) for i in range(16)]
        s.parent(rows,disposition('p',False));r=s.finish()
        self.assertEqual(r['Rprime_known_eligible_count'],0)
        self.assertEqual(r['Rprime_possible_eligible_upper_count'],1)
        self.assertEqual(r['Rprime_counts']['length_unknown_and_decontamination_pass'],1)
        self.assertTrue(r['request_reporting_threshold']['N2_at_least_10percent_incomplete'])
        self.assertFalse(r['request_reporting_threshold']['decision_rule_change_or_reselection_authorized'])

    def test_old_disposition_mismatch_fails(self):
        s=d.Summary();rows=[s.row(str(i),'\\boxed{1}') for i in range(16)]
        with self.assertRaises(ValueError):s.parent(rows,disposition('p',False))
        with self.assertRaises(ValueError):s.parent(rows[:-1],disposition('p',True,False))

    def test_known_exclusions_remain_separate(self):
        s=d.Summary()
        for number,(length,leaked) in enumerate([(False,False),(True,False),(None,True)]):
            rows=[s.row(f'{number}/{i}','\\boxed{1}') for i in range(16)]
            s.parent(rows,disposition(str(number),True,length,leaked))
        r=s.finish();self.assertEqual(r['Rprime_known_eligible_count'],1)
        self.assertEqual(r['Rprime_counts']['all16_complete_before_length_decontamination'],3)
        self.assertEqual(r['Rprime_counts']['decontamination_excluded'],1)
        self.assertEqual(r['Rprime_counts']['known_overlength_excluded'],1)

    def test_reservoir_deterministic_and_tail_only(self):
        a,b=d.Summary(),d.Summary()
        for i in range(70):
            for s in (a,b):s.row(str(i),'x'*500+str(i))
        self.assertEqual(a.samples,b.samples);self.assertEqual(len(a.samples['N1']),5)
        self.assertTrue(all(len(x['last400'])==400 for x in a.samples['N1']))
        self.assertEqual(a.samples['N5'],[])

    def test_reporting_thresholds_and_eligibility_uncertainty(self):
        s=d.Summary();s.counts.update(total=10,N1=9,N2=1)
        self.assertTrue(s.finish()['request_reporting_threshold']['report_owner_for_possible_rule_change'])
        s.counts.update(total=1,N1=1)
        self.assertFalse(s.finish()['request_reporting_threshold']['report_owner_for_possible_rule_change'])
        s.counterfactual.update(all16_complete_before_length_decontamination=8076,
            length_unknown_and_decontamination_pass=8076)
        r=s.finish();self.assertTrue(r['request_reporting_threshold']['Rprime_all16_complete_at_least_8076'])
        self.assertEqual(r['Rprime_eligible_8076_threshold'],'UNKNOWN_DUE_TO_UNMEASURED_LENGTH')

    def test_full_synthetic_readonly_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE rows(dataset TEXT,parent TEXT,source_file TEXT,row_index INTEGER,response TEXT)')
            for key,text in [('a','\\boxed{1}'),('b','\\boxed{2}'+'x'*2001)]:
                db.executemany('INSERT INTO rows VALUES(?,?,?,?,?)',[('ot3',key,'data/x',i,text) for i in range(16)])
            db.execute('INSERT INTO rows VALUES(?,?,?,?,?)',('ot3','wrong','data/x',0,'none'))
            db.execute('PRAGMA query_only=ON');before=db.total_changes
            dispositions={d.rules.identity(k):disposition(k,k=='a',False if k=='a' else None) for k in ('a','b')}
            with patch.object(d.rules,'complete',wraps=d.rules.complete) as called:
                result=d.diagnose(db,dispositions,p,lambda:None)
            self.assertEqual(called.call_count,32);self.assertEqual(result['responses'],32)
            self.assertEqual(result['parents'],2);self.assertEqual(db.total_changes,before)
            with gzip.open(p/'RESPONSE_DIAGNOSTICS.jsonl.gz','rt') as f:rows=[json.loads(x) for x in f]
            self.assertEqual(len(rows),32);self.assertEqual(rows[0]['path_id'],'ot3:data/x:0')
            with self.assertRaises(FileExistsError):d.diagnose(db,dispositions,p,lambda:None)
            db.close()

    def test_missing_disposition_and_interruption_retain_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE rows(dataset TEXT,parent TEXT,source_file TEXT,row_index INTEGER,response TEXT)')
            db.executemany('INSERT INTO rows VALUES(?,?,?,?,?)',[('ot3','p','data/x',i,'none') for i in range(16)])
            with self.assertRaises(ValueError):d.diagnose(db,{},p,lambda:None)
            self.assertTrue((p/'RESPONSE_DIAGNOSTICS.jsonl.gz').exists());self.assertFalse((p/'SUMMARY.json').exists())
            db.close()


if __name__=='__main__':unittest.main()
