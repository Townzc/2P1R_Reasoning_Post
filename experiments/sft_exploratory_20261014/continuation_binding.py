"""Exact finite three-child admission, separate immutable failed-parent linkage."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from copy import copy
import time
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.parallel_guard import _ReadSet
from .continuation_prefix import COUNTS, PARENT

CAMPAIGN='exploratory-continuation-20261014-r1'
WORKER_SECONDS=4800
PLATFORM_SECONDS=4860
FULL_WINDOW=5500
SLOT_CENTS=672
SCOPE='exploratory-exact-suffix-continuation-runtime-and-numeric'


def validate_spec(spec,plan,config,sources):
    if (plan!=spec['plan'] or plan['campaign_id']!=CAMPAIGN or sources!=spec['source_files'] or
            config!=spec['configs'].get(config['run_id']) or
            set(spec['configs'])!={k+'_remaining_r1' for k in COUNTS} or
            set(plan['slots'])!=set(spec['configs']) or spec['total_spending_cap_cents']!=3000 or
            spec['exploratory'] is not True or spec['preregistered'] is not False):
        raise ValueError('Exact exploratory three-child scope differs')
    for name,cfg in spec['configs'].items():
        logical=cfg['logical_run']
        if (logical not in COUNTS or name!=logical+'_remaining_r1' or cfg['offset']!=COUNTS[logical] or
                cfg['max_seconds']!=WORKER_SECONDS or cfg['updates']!=0 or cfg['targets']!=0 or
                cfg['input_sha256']!=spec['original_admission']['input_manifest_sha256'] or
                plan['slots'][name]['reserved_cents']!=SLOT_CENTS or
                spec['prefix_proofs'][logical]['passed'] is not True or
                spec['prefix_proofs'][logical]['binding']['offset']!=COUNTS[logical]):
            raise ValueError('No altered input, dose, prefix, cap or reservation')
    budget=spec['budget']
    if (sum(s['reserved_cents'] for s in plan['slots'].values())!=2016 or
            budget['original_stopped_cost_allowance_cents']+2016+budget['other_cost_allowance_cents']>3000 or
            budget['original_stopped_cost_allowance_cents']<budget['original_lifetime_resource_bound_cents'] or
            budget['original_stopped_cost_allowance_cents']<budget['original_delayed_meter_cents_ceiling'] or
            plan['total_cap_cents']!=2016 or sum(plan['stage_caps_cents'].values())!=2016):
        raise ValueError('Original plus future costs must fit total $30')
    if spec['new_training_updates']!=0 or spec['repeat_generation_allowed'] is not False:
        raise ValueError('No retraining or repeated generation')
    return digest(spec)


def validate_release(spec,plan,config,release):
    validate_spec(spec,plan,config,release['source_files'])
    a=release['acceptance']
    if (a['scope']!=SCOPE or a['decision'] not in ('PASS','PASS-WITH-NOTES') or
            a['source_files']!=spec['source_files'] or a['spec_sha256']!=digest(spec) or
            a['prefix_proofs_sha256']!=digest(spec['prefix_proofs']) or
            a['budget_sha256']!=digest(spec['budget']) or
            a['report_sha256']!=hashlib.sha256(release['review_report'].encode()).hexdigest() or
            len(a['review_commit'])!=40 or len(a['target_commit'])!=40 or
            release['original_input_readback']!=spec['original_input_readback']):
        raise ValueError('Real exact continuation runtime/numeric review required')


def parent_records(spec,config):
    logical=config['logical_run'];base='midpoint/'+PARENT+'/'
    b=spec['prefix_proofs'][logical]['binding']
    return {base+'claim/'+logical:b['original_claim'],base+'terminal/'+logical:b['original_terminal']}


def marker(spec,config):
    logical=config['logical_run']
    return ('midpoint/'+PARENT+'/suffix_continuation/'+logical,
            dict(child_campaign=CAMPAIGN,child_run=config['run_id'],config_sha256=digest(config),
                 spec_sha256=digest(spec),prefix_sha256=digest(spec['prefix_proofs'][logical]),
                 parent_status='failed',new_training_updates=0,repeat_generation=False))


def claim_parent_suffix(store,spec,config):
    for key,expected in parent_records(spec,config).items():
        if store.get(key)!=expected:raise ValueError('Original failed parent changed')
    key,value=marker(spec,config)
    if not store.put(key,value,skip_if_exists=True):
        raise ValueError('Parent suffix already reserved; no retry even if identical')
    return key,value


class ActiveCheck:
    """Fresh ten-key snapshot: seven child guard keys + failed parent + linkage."""
    def __init__(self,guard,spec,config):
        self.guard,self.spec,self.config=guard,spec,config
        self.pool=ThreadPoolExecutor(max_workers=8);self.failed=False
        self.metrics=dict(checks=0,remote_reads=0,seconds=0.,max_seconds=0.,cache_across_checks=False)

    def check(self,admission,reserve):
        if self.failed:raise ValueError('Failed check cannot be reused')
        g=self.guard;tick=time.monotonic();futures=[]
        try:
            if digest(g.plan)!=g.plan_hash:raise ValueError('Plan changed')
            keys=[g._key('campaign'),g._key('claim',admission.run_id),
                  g._key('attempt',admission.run_id+'/'+admission.attempt_id),g._key('terminal',admission.run_id)]
            keys += [g._key('reconciliation',run) for run in g.plan['slots']]
            dependencies=parent_records(self.spec,self.config)
            mk,mv=marker(self.spec,self.config);dependencies[mk]=mv;keys+=list(dependencies)
            futures=[self.pool.submit(g.store.get,k) for k in keys];records={}
            for k,f in zip(keys,futures):
                left=15-(time.monotonic()-tick)
                if left<=0:raise TimeoutError('Ten-key active read timeout')
                records[k]=f.result(timeout=left)
            if any(records[k]!=v for k,v in dependencies.items()):raise ValueError('Parent/child linkage changed')
            validator=copy(g);validator.store=_ReadSet(records)
            validator.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
            elapsed=time.monotonic()-tick
            if elapsed>=15:raise TimeoutError('Active read timeout')
            self.metrics['checks']+=1;self.metrics['remote_reads']+=len(keys)
            self.metrics['seconds']+=elapsed;self.metrics['max_seconds']=max(self.metrics['max_seconds'],elapsed)
        except BaseException:
            self.failed=True
            for f in futures:f.cancel()
            raise

    def close(self):
        self.pool.shutdown(wait=False,cancel_futures=True)
