"""Persistent cumulative limits for the approved six-run continuation."""
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import time
from experiments.thursday_probe.common import stamp
from experiments.thursday_probe_v2.training import atomic_json

HISTORICAL_GENERATIONS=592
GENERATION_CAP=4864
NEW_PLANNED_GENERATIONS=4192
MAX_POWERED_SECONDS=28800
MAX_RENTAL_CNY=65.0
EXPORT_RESERVE_SECONDS=1500
PROCESS_SLICE_SECONDS=7200


def epoch(value):return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


class ResumeGenerationBudget:
    def __init__(self,path):
        self.path=Path(path)
        if not self.path.exists():
            atomic_json(self.path,dict(cap=GENERATION_CAP,used=HISTORICAL_GENERATIONS,
                historical_consumed=HISTORICAL_GENERATIONS,planned_new=NEW_PLANNED_GENERATIONS,
                planned_total=4784,events=[],accounting='Historical592 includes16 fault repeats; never reset on batch/process/power-window restart.'))
        record=self.record()
        if record['cap']!=GENERATION_CAP or record['historical_consumed']!=HISTORICAL_GENERATIONS:
            raise ValueError('Cumulative generation limits changed')
        if record['used']!=HISTORICAL_GENERATIONS+sum(e['reserved'] for e in record['events']):
            raise ValueError('Generation ledger inconsistent')
    def record(self):return json.loads(self.path.read_text())
    @property
    def used(self):return self.record()['used']
    def reserve(self,name,n):
        r=self.record()
        if type(n) is not int or n<=0 or r['used']+n>r['cap']:
            raise ValueError('Cumulative generation cap exceeded')
        if name in {e['name'] for e in r['events']}:
            raise ValueError('Duplicate batch reservation; reconcile incomplete intent rather than regenerate')
        r['events'].append(dict(name=name,reserved=n,at_utc=stamp()));r['used']+=n
        atomic_json(self.path,r)


class RentalBudget:
    """Window closing is a provider-confirmed fact, never inferred from Python exit."""
    def __init__(self,path,power_on_at_utc,rate):
        self.path=Path(path)
        if not math.isfinite(rate) or not 0<rate<=65:
            raise ValueError('Verified positive current rental rate required')
        start=epoch(power_on_at_utc)
        if start>time.time():raise ValueError('Future power-on time')
        if self.path.exists():
            r=self.record()
            if r['maximum_powered_seconds']!=MAX_POWERED_SECONDS or r['maximum_rental_cny']!=MAX_RENTAL_CNY:
                raise ValueError('Resource package cannot be reset or enlarged')
            active=[w for w in r['windows'] if w.get('shutdown_confirmed_at_utc') is None]
            if active:
                if len(active)!=1 or epoch(active[0]['power_on_at_utc'])!=start or active[0]['rate_cny_per_hour']!=rate:
                    raise ValueError('Active power window must be preserved')
                return
            if r['windows'] and start<epoch(r['windows'][-1]['shutdown_confirmed_at_utc']):
                raise ValueError('Overlapping rental windows')
        else:
            r=dict(maximum_powered_seconds=MAX_POWERED_SECONDS,maximum_rental_cny=MAX_RENTAL_CNY,
                export_shutdown_reserve_seconds=EXPORT_RESERVE_SECONDS,windows=[],
                authority='Owner explicitly requested the six-run resume plan; finite8h/CNY65 package within existing explicitCNY3000 ceiling, no recharge or new instance.',
                prior_v2_window_cost_proxy_cny=5.734516666666667,prior_v2_charged_process_seconds=1543,
                prior_all_phases_charged_process_seconds=8915,prior_all_phases_receipts=24)
        r['windows'].append(dict(power_on_at_utc=power_on_at_utc,rate_cny_per_hour=rate,shutdown_confirmed_at_utc=None))
        atomic_json(self.path,r)
    def record(self):return json.loads(self.path.read_text())
    def remaining(self,now=None):
        now=time.time() if now is None else now;r=self.record();used=cost=0.;active=None
        for w in r['windows']:
            end=epoch(w['shutdown_confirmed_at_utc']) if w.get('shutdown_confirmed_at_utc') else now
            seconds=max(0,end-epoch(w['power_on_at_utc']));used+=seconds;cost+=seconds*w['rate_cny_per_hour']/3600
            if not w.get('shutdown_confirmed_at_utc'):active=w
        if active is None:raise ValueError('No active rental window')
        seconds=min(MAX_POWERED_SECONDS-used,(MAX_RENTAL_CNY-cost)*3600/active['rate_cny_per_hour'])
        return dict(powered_seconds_used=used,rental_cost_proxy_cny=cost,remaining_hard_seconds=max(0,seconds),
                    hard_deadline_epoch=now+max(0,seconds),worker_deadline_epoch=now+max(0,seconds)-EXPORT_RESERVE_SECONDS,
                    estimate_is_invoice=False)
    def close(self,confirmed_utc):
        r=self.record();active=[w for w in r['windows'] if not w.get('shutdown_confirmed_at_utc')]
        if len(active)!=1 or epoch(confirmed_utc)<epoch(active[0]['power_on_at_utc']):
            raise ValueError('Invalid provider closeout')
        active[0]['shutdown_confirmed_at_utc']=confirmed_utc;atomic_json(self.path,r)


def admit_unit(deadline,required_seconds,disk_free_gib,minimum_free_gib=1.0,now=None):
    """Only the next saveable unit is tested; no outcomes or whole-queue forecast."""
    now=time.time() if now is None else now
    if not math.isfinite(required_seconds) or required_seconds<=0:
        raise ValueError('Positive next-unit time estimate required')
    return now+required_seconds<deadline and disk_free_gib>=minimum_free_gib
