"""New bounded missing-input completion checks; fakeVolume, no remote calls."""
import hashlib,tempfile,unittest
from pathlib import Path
from scripts.complete_p010_k1_input_parts import finish_missing,confirmed_parts
from experiments.p010.common import dump

class Volume:
    def __init__(self,existing):self.data=dict(existing);self.read=[];self.written=[]
    def read_file(self,name):
        self.read.append(name)
        if name not in self.data:raise FileNotFoundError(name)
        if isinstance(self.data[name],Exception):raise self.data[name]
        yield self.data[name]
    def batch_upload(self,force):
        assert force is False
        return self
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def put_file(self,source,remote):
        assert remote not in self.data
        self.data[remote]=source.read_bytes();self.written.append(remote)

def entry(value):return {'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}

class InputCompletionTests(unittest.TestCase):
    def test_confirmed_not_read_again_missing_only_uploaded_existing_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inputs=root/'inputs';inputs.mkdir();out=root/'out';out.mkdir()
            expected={k:entry(k.encode()) for k in ('a','b','c')}
            for k in expected:(inputs/k).write_bytes(k.encode())
            v=Volume({'/p010-20261019/student_inputs/b':b'b'})
            confirmed={'a':dict(**expected['a'],reused_confirmed_readback=True)}
            result=finish_missing(v,inputs,out,expected,confirmed,(FileNotFoundError,))
            self.assertEqual(set(result),set(expected))
            self.assertNotIn('/p010-20261019/student_inputs/a',v.read)
            self.assertEqual(v.written,['/p010-20261019/student_inputs/c'])
            self.assertTrue(result['b']['existing_remote_reused'])

    def test_unknown_remote_read_never_triggers_upload(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'x').write_bytes(b'x');v=Volume({'/p010-20261019/student_inputs/x':TimeoutError('synthetic unknown')})
            with self.assertRaises(TimeoutError):finish_missing(v,root,root/'out',{'x':entry(b'x')},{},(FileNotFoundError,))
            self.assertFalse(v.written)

    def test_conflicting_remote_bytes_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'x').write_bytes(b'x');v=Volume({'/p010-20261019/student_inputs/x':b'wrong'})
            with self.assertRaisesRegex(ValueError,'differ'):finish_missing(v,root,root/'out',{'x':entry(b'x')},{},(FileNotFoundError,))
            self.assertFalse(v.written)

    def test_partial_proof_must_match_original_expected_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dump(root/'files/x.json.json',dict(**entry(b'x'),reused_original=False))
            value=confirmed_parts(root,{'input_files':{'x.json':entry(b'x')}})
            self.assertEqual(list(value),['x.json'])
            with self.assertRaises(ValueError):confirmed_parts(root,{'input_files':{'x.json':entry(b'bad')}})

if __name__=='__main__':unittest.main()
