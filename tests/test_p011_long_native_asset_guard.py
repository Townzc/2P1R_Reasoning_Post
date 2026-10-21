import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from tests.test_p011_long_full_path import job,spec,Store
from experiments.p011 import long_path as p
from experiments.sft_allocation_midpoint.common import dump,sha,digest,read
class NativeAsset(unittest.TestCase):
 def test_changed_native_stop_config_fails_before_claim_and_model(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);j=job();s=spec(j);sf=root/'SPEC.json';dump(sf,s);k=p.key(j);store=Store();raw='PASS'
   intent=dict(job_id=p.logical(j),logical_id=p.logical(j),execution='f'*40,app_id='ap-a',spec_sha256=digest(s),spec_file_sha256=sha(sf),job_sha256=digest(j),dispatch_epoch=1792556000.,budget_observed_epoch=1792556000.,review={'report_sha256':hashlib.sha256(raw.encode()).hexdigest()},budget={'prior_reserved_usd':'0'})
   store[k+'/dispatch']=intent;body=Mock();timer=Mock()
   with patch.object(p.time,'time',return_value=1792556001.),patch.object(p.shared,'exact_source'),patch.object(p,'reviewed'),patch.object(p,'verify'),patch.object(p,'read',return_value={'eos_token_id':[151645]}),patch.object(p,'BASE',str(root/'runs')),patch.object(p,'INPUTS',str(root/'inputs')):
    with self.assertRaises(ValueError):p.worker_body(s,sf,root,intent,raw,store,Mock(),lambda _:timer,body)
   body.assert_not_called();self.assertNotIn(k+'/claim',store);timer.cancel.assert_called_once()
if __name__=='__main__':unittest.main()
