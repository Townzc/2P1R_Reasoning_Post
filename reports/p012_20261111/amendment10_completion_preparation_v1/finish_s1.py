"""Wait for the existing S1 queue, then prepare its authorized CPU review packet.

This process never creates a model client, retries an experiment, trains,
changes settings, or sends an external message.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
PREP = Path('reports/p012_20261111/amendment10_training_review_v1')
STATE = Path('.local/p012_20261111/amendment10_v1/RECOVERY_QUEUE.json')
read = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0,'.local/p012_20261111/amendment7_v1')
from a7_ops import lock, publish


def record(value):
    value['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (HERE/'STATUS.json').write_text(json.dumps(value,indent=2)+'\n')


def check_sources():
    for filename,expected in read(HERE/'SOURCES.json').items():
        assert sha(filename)==expected,'CPU preparation source changed: '+filename
    assert Path(__file__).read_bytes()==subprocess.check_output(['git','show','HEAD:'+str(HERE/'finish_s1.py')])


def current_state():
    # The existing controller writes this small JSON in place. Retry a torn
    # read only; this cannot repeat a model call or scientific operation.
    for attempt in range(3):
        try:return read(STATE)
        except json.JSONDecodeError:
            if attempt==2:raise
            time.sleep(1)


def main():
    with lock('A10_CPU_COMPLETION.lock'):
        assert not (HERE/'STATUS.json').exists(),'Refuse duplicate completion processor'
        check_sources()
        record({'status':'waiting_for_existing_S1','paid_model_calls':0,'training_started':False})
        try:
            while True:
                state=current_state()
                assert state['length_review_commit']=='f0369f2590dfd4f70dab909c81a9d386bde672ae'
                assert state['cap_authority_commit']=='c9a534808e65ec648da1995ba26ee52929509de9'
                if state['status']=='generation_complete_data_and_training_review_required':break
                if state['status']=='stopped_for_inspection':
                    raise RuntimeError('S1 stopped: '+state.get('error','reason in S1 status'))
                assert state['status'] in ['running','ready_to_resume_batch2']
                time.sleep(30)
            check_sources()
            record({'status':'preparing_CPU_data_and_review','paid_model_calls':0,'training_started':False})
            for script in ['freeze_data.py','prepare_requests.py','package_review.py']:
                check_sources()
                subprocess.run([sys.executable,str(PREP/script)],check=True)
            budget=read(PREP/'PROSPECTIVE_BUDGET.json')
            ready={'status':'combined_review_ready','paid_model_calls':0,'training_started':False,
                'review_packet':'reports/p012_20261111/amendment10_combined_training_review_v1/README.md',
                'prepared_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'whole_phase_forecast_usd':budget['whole_phase_forecast_usd'],
                'budget_attention':budget['whole_phase_forecast_usd']>200 or budget['training_and_evaluation_forecast_usd']>125,
                'next_step':'Owner relays complete packet to Claude; no training before combined review and live admission'}
            record(ready)
            publish([HERE/'STATUS.json'],'P012 A10: CPU preparation complete; combined review required before training')
        except BaseException as exc:
            record({'status':'stopped_for_inspection','reason':str(exc),'paid_model_calls':0,'training_started':False})
            publish([HERE/'STATUS.json'],'P012 A10: preserve CPU completion stop; no experiment restarted')
            raise


if __name__=='__main__':
    main()
