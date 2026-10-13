"""Delayed allocation is a measurement failure, not authorization to replay work."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.sft_allocation_p008.phase0_runtime import gpu_probe
from experiments.sft_allocation_p008.contract import PHASE0_ROLES

class Clock:
 def __init__(self):self.now=100.
 def time(self):return self.now
 def sleep(self,n):self.now+=n

class Store:
 def __init__(self,ready,acks):self.ready=ready;self.acks=acks;self.data={}
 def put(self,k,v,skip_if_exists):
  if k in self.data:return False
  self.data[k]=v;return True
 def get(self,k):
  if k in self.data:return self.data[k]
  role=k.rsplit('/',1)[1]
  return (self.ready if '/ready/' in k else self.acks).get(role)

class Volume:
 def commit(self):pass
 def reload(self):pass

class ConcurrencyTest(unittest.TestCase):
 def probe(self,missing_ready=False,missing_ack=False,corrupt=False):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);role=PHASE0_ROLES[0];ready={};acks={};clock=Clock()
   for i,r in enumerate(PHASE0_ROLES):
    p=root/r;p.mkdir();blob=hashlib.sha256(r.encode()).digest()*2
    ready[r]=dict(role=r,epoch=100.,gpu=f'H100, 81920, GPU-{i}\n',sha256=hashlib.sha256(blob).hexdigest())
    if r!=role:(p/'io_probe.bin').write_bytes(blob)
    acks[r]=dict(role=r,epoch=100.,read_sha256={})
   if corrupt:(root/PHASE0_ROLES[-1]/'io_probe.bin').write_bytes(b'bad')
   if missing_ready:ready.pop(PHASE0_ROLES[-1])
   if missing_ack:acks.pop(PHASE0_ROLES[-1])
   store=Store(ready,acks)
   with patch('experiments.sft_allocation_p008.phase0_runtime.time',clock),patch(
      'experiments.sft_allocation_p008.phase0_runtime.subprocess.check_output',return_value='H100, 81920, GPU-0\n'):
    result=gpu_probe(dict(run_id=role,probe_bytes=64,barrier_seconds=4),root/role,store,'p',Volume(),lambda:None)
   self.assertLessEqual(clock.now,104.)
   return result,store
 def test_all_ready_and_ack(self):
  result,_=self.probe();self.assertEqual(result['status'],'four_gpu_verified')
 def test_late_ready_is_recorded_without_retry(self):
  result,store=self.probe(missing_ready=True)
  self.assertEqual(result['reason'],'readiness_timeout');self.assertEqual(result['status'],'concurrency_not_achieved')
  self.assertFalse(any('/ack/' in k for k in store.data))
 def test_late_ack_is_recorded_without_retry(self):
  result,_=self.probe(missing_ack=True)
  self.assertEqual(result['reason'],'ack_timeout');self.assertEqual(result['status'],'concurrency_not_achieved')
 def test_corrupt_payload_still_fails(self):
  with self.assertRaisesRegex(ValueError,'payload differs'):self.probe(corrupt=True)

if __name__=='__main__':unittest.main()
