import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p011.b_remaining import transport,selection,execution,evidence,numeric
from experiments.p011.short_generation import b_requests
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest

class Tokenizer:
    eos_token_id=151645
    def __init__(self):self.calls=[]
    def decode(self,ids,**kw):
        self.calls.append(list(ids))
        if 9 in ids:raise AssertionError('Decoder crossed an unmapped ID')
        return ''.join(str(x) for x in ids)

class TestTransport(unittest.TestCase):
    def run_case(self,ids,finish='stop'):
        t=Tokenizer();raw=dict(token_ids=ids,finish_reason=finish)
        value=transport.completion(raw,t,{1,2,151645,151643},151936,{151645,151643})
        return raw,t,value
    def test_mapped_original(self):
        _,_,(s,e)=self.run_case([1,2,151645]);self.assertEqual(s['stop_reason'],'native_eos');self.assertEqual(e['unmapped_model_token_ids'],[])
    def test_noncap_prefix_only(self):
        raw,t,(s,e)=self.run_case([1,9,2,151645]);self.assertEqual(t.calls,[[1]])
        self.assertEqual((s['stop_reason'],s['retained_tokens']),('invalid_special_token',2));self.assertEqual(e['unmapped_positions'],[1])
        decoded=dict(stop=s,transport=e,answer_text=s['answer_segment'],raw_record_sha256=digest(raw))
        transport.validate_saved(raw,decoded,{1,2,151645,151643},151936)
    def test_after_eos_rejected(self):
        with self.assertRaises(ValueError):self.run_case([1,151645,9])
    def test_second_unmapped_after_eos_rejected(self):
        with self.assertRaises(ValueError):self.run_case([9,151645,9])
    def test_outside_model_rejected(self):
        with self.assertRaises(ValueError):self.run_case([151936,151645])
    def test_no_eos_short_rejected(self):
        with self.assertRaises(ValueError):self.run_case([1,9])
    def test_old_length_exception_unchanged(self):
        class Permissive(Tokenizer):
            def decode(self,ids,**kw):return 'old mapped rendering'
        raw=dict(token_ids=[9]*1024,finish_reason='length');t=Permissive()
        from experiments.p010.teacher_transport import completion as old
        self.assertEqual(transport.completion(raw,t,{1,151645},151936,{151645}),old(raw,t,{1,151645},151936,{151645}))

def record(pid,a,unmapped=False):
    stop=dict(stop_reason='invalid_special_token' if unmapped else 'native_eos')
    return dict(candidate_id=f'{pid}::attempt{a:02d}',problem_id=pid,attempt=a,answer_text=f'a{a}',
        stop=stop,transport=dict(unmapped_model_token_ids=[9] if unmapped else []),
        score={'score':{'correct':False,'parsed':True,'box_extracted':True}},usable=False)

class TestSelection(unittest.TestCase):
    def fixture(self):
        ids=[f'p{i}' for i in range(400)];return ids,{f'{p}::attempt{a:02d}':record(p,a) for p in ids for a in range(1,17)}
    def test_fallback_skips_unmapped(self):
        ids,rows=self.fixture();rows['p0::attempt01']=record('p0',1,True)
        value=selection.select(ids,rows);self.assertEqual(value['selected_ids']['1'][0],'p0::attempt02');self.assertTrue(value['requires_owner_disposition'])
    def test_all_unmapped_parent_absent(self):
        ids,rows=self.fixture()
        for a in range(1,17):rows[f'p0::attempt{a:02d}']=record('p0',a,True)
        value=selection.select(ids,rows);self.assertEqual(value['all16_unmapped_absent_questions'],['p0']);self.assertEqual(len(value['selected_ids']['1']),399)

class Store(dict):
    def put(self,k,v,skip_if_exists=False):
        if skip_if_exists and k in self:return False
        self[k]=v;return True

class TestContinuation(unittest.TestCase):
    def fixture(self,root):
        ids=[f'p{i}' for i in range(400)];prompts={p:[1,2] for p in ids};rows=b_requests(ids,prompts)
        pack=dict(ordered400=ids,prompts=prompts,rows=rows);src=root/'old';src.mkdir();files={}
        def raw(part):
            return [dict(**{k:v for k,v in row['request'].items() if k in ('candidate_id','problem_id')},source_row_sha256=None,
                prompt_token_ids=row['request']['prompt_token_ids'],sampling=row['sampling'],output_count=1,
                token_ids=[1,151645],backend_text='1',finish_reason='stop',stop_reason=151645) for row in part]
        def decoded(x):return dict(stop=dict(answer_segment='1',stop_reason='native_eos'),transport={},answer_text='1',raw_record_sha256=digest(x))
        for i in range(5):
            d=src/'batches'/f'{i:03d}';part=rows[i*256:(i+1)*256];rr=raw(part)
            dump(d/'RAW.json',rr);dump(d/'FORECAST.json',{'historical':True})
            dump(d/'INTENT.json',dict(first=i*256,requests=[x['request'] for x in part],sampling=[x['sampling'] for x in part],roster_sha256=digest(rows)))
            if i<4:
                dump(d/'TRANSPORT.json',[decoded(x) for x in rr]);dump(d/'ACK.json',dict(first=i*256,count=256,raw_file_sha256=sha(d/'RAW.json'),transport_file_sha256=sha(d/'TRANSPORT.json')))
        for n in execution.prefix_names():files[n]=dict(bytes=(src/n).stat().st_size,sha256=sha(src/n))
        return pack,src,files,raw,decoded
    def execute(self,root,fail_batch=None):
        pack,src,files,raw,decoded=self.fixture(root);store=Store({'new/claim':{'x':1}});calls=[];decodes=[];ticks=iter(range(1000));out=root/'new'
        class Engine:
            def generate(self,requests,params,**kw):
                i=5+len(calls);calls.append(i)
                if i==fail_batch:raise RuntimeError('test failure')
                return raw(pack['rows'][i*256:(i+1)*256])
        def decode(x):decodes.append(x['candidate_id']);return decoded(x)
        with patch.object(execution,'returned_records',lambda req,params,output:output):
            value=execution.generate(pack,out,'new',{'x':1},store,lambda:None,Engine(),lambda **x:x,decode,
                lambda left,times:dict(left=left,times=list(times)),lambda:None,src,files,clock=lambda:next(ticks))
        return pack,src,files,out,store,calls,decodes,value
    def test_5120_only_and1280_byte_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            pack,src,files,out,store,calls,decodes,value=self.execute(Path(d))
            self.assertEqual(calls,list(range(5,25)));self.assertEqual(len(decodes),5376);self.assertEqual(value['new_outputs'],5120)
            for n in files:self.assertEqual((src/n).read_bytes(),(out/'original_prefix'/n).read_bytes())
    def test_full6400_oracle_without_redecoding(self):
        with tempfile.TemporaryDirectory() as d:
            pack,src,files,out,store,calls,decodes,value=self.execute(Path(d))
            def saved(x,y):self.assertEqual(y['raw_record_sha256'],digest(x))
            proof,raw,decoded=evidence.check_body(pack,out,'new',{'x':1},store,files,saved,lambda left,times:dict(left=left,times=list(times)))
            self.assertEqual(proof['verified_total_raw'],6400);self.assertEqual(len(raw),len(decoded))
    def test_existing_output_refuses_before_generation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pack,src,files,raw,decode=self.fixture(root);out=root/'new';out.mkdir()
            with self.assertRaises(ValueError):execution.generate(pack,out,'new',{},Store({'new/claim':{}}),lambda:None,None,None,decode,None,lambda:None,src,files)
    def test_partial_failure_keeps_prefix_and_permanent_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(RuntimeError):self.execute(root,fail_batch=5)
            self.assertTrue((root/'new/FAILED.json').is_file());self.assertTrue((root/'new/batches/005/INTENT.json').is_file());self.assertFalse((root/'new/batches/006').exists())
    def test_tampered_prefix_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pack,src,files,raw,decode=self.fixture(root);p=src/'batches/000/RAW.json';p.write_text('[]');out=root/'new';out.mkdir()
            with self.assertRaises((ValueError,AssertionError)):execution.copy_prefix(src,out,files,pack['rows'])

if __name__=='__main__':unittest.main()
