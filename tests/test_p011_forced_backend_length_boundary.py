"""Only new backend-length selection boundary; old successful tests not repeated."""
import unittest
from experiments.p011.forced_answer import forced_request, original_digest


class BackendLengthBoundary(unittest.TestCase):
    def test_native_or_special_classification_does_not_filter_backend_length(self):
        for classification,unmapped in [('native_eos',[]),('invalid_special_token',[]),('length_cap',[3])]:
            raw={'id':'math500:0001:sample:0','request_sha256':'a'*64,'prompt_token_ids':[1],
                'answers':[{'token_ids':[3]*16384,'finish_reason':'length'}]}
            decoded={'id':raw['id'],'raw_record_sha256':original_digest(raw),'backend_finish_reason':'length',
                'stop_reason':classification,'unmapped_model_token_ids':unmapped}
            result=forced_request(raw,decoded,[2])
            self.assertEqual(result['prompt_token_ids'],[1]+[3]*16384+[2])


if __name__=='__main__':unittest.main()
