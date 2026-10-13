import sys,unittest
sys.path.insert(0,'.')
from tests.test_p008_block_journal import BlockJournalTests
from experiments.sft_allocation_p008.block_journal import verify_training_blocks
class P(BlockJournalTests):
    def test_probe_fence_midblock(self):
        for s in range(1,21):self.update(s)          # block1 acked, block2 at 4/16
        self.fenced=True
        for s in range(21,32):self.update(s)         # no remote check inside block
        with self.assertRaises(RuntimeError):self.update(32)   # ack check fails
        keys=sorted(k for k in self.store.records)
        print('remote keys',[k.split('/',1)[1] for k in keys])
        with self.assertRaises(RuntimeError):self.update(33)   # poisoned
    def test_probe_tamper(self):
        for s in range(1,257):self.update(s)
        i,d=self.records();d['update_0100']['loss']=0.5
        with self.assertRaises(ValueError):verify_training_blocks(i,d,self.store.records,'run/',256)
        i,d=self.records();del i['update_0005']
        with self.assertRaises(ValueError):verify_training_blocks(i,d,self.store.records,'run/',256)
        i,d=self.records();self.store.records['run/done/extra']={}
        with self.assertRaises(ValueError):verify_training_blocks(i,d,self.store.records,'run/',256)
        print('tamper ok, checks',self.checks)
    def test_probe_skip_and_mismatch(self):
        self.update(1)
        with self.assertRaises(ValueError):self.update(3)
unittest.main(argv=['x','-k','probe'],verbosity=1)
