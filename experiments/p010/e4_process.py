"""Isolated E4 training followed by mandatory process exit before vLLM."""
import os
from pathlib import Path
import time
import traceback
from experiments.p010.common import dump,read,digest,verify
from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal


class MeasuredJournal(BlockTrainingJournal):
    def __init__(self,*args,start,stop,**kwargs):
        super().__init__(*args,**kwargs);self.start=start;self.stop=stop;self.times=[];self.tick=None
    def begin(self,name,record):
        if name.startswith('update_') and self.cursor%16==0 and self.active is None:
            self.tick=time.time()
            maximum=max([43.307480978]+self.times)
            future=1.2*(maximum*((1024-self.cursor)//16)+6*20.412141323+600)
            f=dict(elapsed=time.time()-self.start,future_seconds=future,old_Qwen_proxy=True,
                max_block=maximum,remaining_blocks=(1024-self.cursor)//16,allowance_calibrated=False)
            dump(self.out/'forecasts'/f'{self.cursor:04d}.json',f);self.commit()
            if time.time()+future>self.stop-30:raise TimeoutError('Measured E4 remainder does not fit4500s')
        super().begin(name,record)
    def end(self,name,record):
        super().end(name,record)
        if name.startswith('update_') and self.cursor%16==0 and self.active is None:
            self.commit();seconds=time.time()-self.tick;self.times.append(seconds)
            dump(self.out/'timings'/f'{self.cursor:04d}.json',dict(seconds=seconds,updates=16));self.commit()


def child(conn,inputs,out,model,identity,claim,start,stop):
    try:
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('Determinism environment differs')
        import modal
        from experiments.p010.training import train_and_merge
        volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
        volume.reload();verify(model['remote_path'],model['files'])
        key='e4/'+identity['run_id']
        def deadline():
            if time.time()>stop-30:raise TimeoutError('Original E4 deadline')
        def check():
            deadline()
            if store.get(key+'/claim')!=claim:raise RuntimeError('Original claim differs')
        config=identity['config'];stem='e4_n'+str(config['n']);inputs=Path(inputs)
        rows,encoded,plan=[read(inputs/(stem+'_'+x+'.json')) for x in ('rows','encoded','plan')]
        journal=MeasuredJournal(Path(out),key,store,volume.commit,check,
            deadline=deadline,expected_updates=1024,start=start,stop=stop)
        result=train_and_merge(model['remote_path'],rows,encoded,plan,Path(out),Path(out)/'merged',journal,identity)
        dump(Path(out)/'TRAINING_PROCESS_RESULT.json',dict(result=result,pid=os.getpid(),block_seconds=journal.times));volume.commit()
        conn.send(('complete',result))
    except BaseException:
        conn.send(('error',traceback.format_exc()));raise
    finally:conn.close()
