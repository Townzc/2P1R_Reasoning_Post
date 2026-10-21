import unittest
from experiments.p011.c2_reuse_projection import p1_records,indexed_records,prepare_projection
from experiments.sft_allocation_midpoint.common import digest


def rec(pid,a=1,good=True):
 text='answer';score={'id':f'{pid}::attempt{a:02d}','score':{'correct':good,'parsed':True,'box_extracted':True}}
 return {'candidate_id':score['id'],'problem_id':pid,'attempt':a,'answer_text':text,
  'stop':{'stop_reason':'native_eos','answer_segment':text},'score':score,
  'usable':good,'raw_record_sha256':'a'*64}

def old(pid='p',good=True):
 x=rec(pid,good=good);row={'id':x['candidate_id'],'problem_id':pid,'attempt':1,'dataset':'math_procurement','answer_segment':x['answer_text'],
 'original_generation_record':{'id':x['candidate_id'],'stop':x['stop'],'raw_file':'original/raw.json','raw_file_sha256':'a'*64,'source_row_sha256':'b'*64}}
 return row,x['score']

class NewC2Reuse(unittest.TestCase):
 def test_original_p1_projection(self):
  row,sc=old();x,proof=p1_records([row],[sc],['p']);self.assertEqual(x[row['id']]['score'],sc);self.assertEqual(proof[row['id']]['original_row_sha256'],digest(row))
 def test_unknown_not_false(self):
  row,sc=old();sc['score']['correct']=None
  with self.assertRaises(ValueError):p1_records([row],[sc],['p'])
 def test_changed_stop_rejected(self):
  row,sc=old();row['original_generation_record']['stop']['answer_segment']='changed'
  with self.assertRaises(ValueError):p1_records([row],[sc],['p'])
 def test_first_four_projection(self):
  a=rec('p');b=rec('p',5);x,proof=indexed_records({a['candidate_id']:a,b['candidate_id']:b},['p'],'t15');self.assertEqual(list(x),[a['candidate_id']]);self.assertEqual(proof[a['candidate_id']]['original_record_sha256'],digest(a))
 def fixture(self):
  ids=[f'p{i}' for i in range(401)];roster={'e1d_order':ids,'s1':{'400':ids[:400]},'unsupported':[],'e2_dev':[]}
  source=[{'problem_id':p,'problem':'q','gold':'1'} for p in ids];requests=[{'candidate_id':p+'::attempt01','problem_id':p,'attempt':1,'prompt_token_ids':[1,2]} for p in ids]
  right={x['candidate_id']:x for x in (rec(p) for p in ids)}
  rows,sc=zip(*(old(p,good=False) for p in ids))
  return roster,source,requests,right,{},list(rows),list(sc)
 def test_missing_only_window_and_overlap_retained(self):
  p=prepare_projection(*self.fixture(),window_size=2);self.assertEqual(len(p['plan']['new_requests']),6);self.assertEqual(p['plan']['window_parents'],['p0','p1']);self.assertTrue(all(x['request']['attempt'] in (2,3,4) for x in p['plan']['new_requests']));self.assertEqual(len(p['s1_ids']),400)
 def test_reused_t15_duplicate_blocked(self):
  x=list(self.fixture());a=rec('p0');x[4]={a['candidate_id']:a}
  with self.assertRaises(ValueError):prepare_projection(*x,window_size=2)
 def test_missing_original_t72_blocks(self):
  x=list(self.fixture());x[3].pop('p0::attempt01');p=prepare_projection(*x,window_size=2);self.assertEqual(p['plan']['initial_prefix']['blocked_missing_old_T72'],'p0');self.assertEqual(p['plan']['new_requests'],[])
 def test_missing_prompt_blocks(self):
  x=list(self.fixture());x[2].pop()
  with self.assertRaises(ValueError):prepare_projection(*x,window_size=2)

if __name__=='__main__':unittest.main()
