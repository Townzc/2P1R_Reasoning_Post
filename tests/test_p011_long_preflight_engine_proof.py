"""New exact engineering engine readback check, no model or old test rerun."""
from copy import deepcopy
from pathlib import Path
import unittest
from tests.test_p011_long_preflight import candidate
from experiments.p011.long_preflight import evidence,path

class EngineProofTests(unittest.TestCase):
    def test_every_actual_engine_field_and_export_path_are_bound(self):
        j=candidate()['jobs']['preflight_S-L15_s17_r1']
        actual={'max_model_len':j['context'],'enforce_eager':False,'dtype':'torch.bfloat16',
            'max_num_seqs':256,'max_num_batched_tokens':8192,'enable_chunked_prefill':True,
            'enable_prefix_caching':False,'gpu_memory_utilization':.80,'compilation_level':3,
            'cudagraph_mode':'FULL_AND_PIECEWISE','cudagraph_capture_sizes':[1,2,4,8,16,32,64,128,256]}
        value={'requested':evidence.long_execution.engine_settings(j['context']),'actual':actual,
               'model_path':str(Path(path.BASE)/path.logical(j)/'model_for_vllm')}
        evidence.engine_proof(value,j)
        for key in actual:
            bad=deepcopy(value);bad['actual'][key]=None
            with self.assertRaises(ValueError):evidence.engine_proof(bad,j)
        bad=deepcopy(value);bad['model_path']='old/student/merged'
        with self.assertRaises(ValueError):evidence.engine_proof(bad,j)

if __name__=='__main__':unittest.main()
