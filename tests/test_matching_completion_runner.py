import io,unittest
from scripts.run_matching_completion import expand_key,hash_stream
from src.path_family_matching_complete import record_reference
class Tests(unittest.TestCase):
    def test_expansion_checks_real_token_length(self):
        r={'problem_id':'p','family':'identity_absent','structure_id':'s','ac_class':'a','n_supervised':12}
        ref=record_reference(r)
        key={'witnesses':{'p':{'problem_id':'p','n_supervised':11,'slots':[{'family':'identity_absent','structure_id':'s','ac_class':'a','record_ref':ref}]}}}
        with self.assertRaises(ValueError):expand_key(key,{ref:r})
        key['witnesses']['p']['n_supervised']=12
        self.assertEqual(expand_key(key,{ref:r})['witnesses']['p']['slots'][0]['record'],r)
    def test_stream_hash_counts_all_chunks(self):
        import hashlib
        b=b'a'*(1024*1024+11)
        self.assertEqual(hash_stream(io.BytesIO(b)),{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
if __name__=='__main__':unittest.main()
