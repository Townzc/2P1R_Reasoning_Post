import sys,time,copy
sys.path.insert(0,'.')
from experiments.sft_allocation_midpoint.guard import GuardError, RunGuard
from experiments.sft_allocation_p008.parallel_guard import ParallelActiveCheck
from tests.test_midpoint_guard import FakeAtomicStore, plan, intent
def setup():
    s=FakeAtomicStore();g=RunGuard(s,plan());g.register(now_epoch=1000)
    a=g.admit(intent(),attempt_id='w',now_epoch=1100,max_runtime_seconds=100);return s,g,a
def both(mut):
    s,g,a=setup();mut(s,g,a)
    try: g.check_active(a,now_epoch=1101,spent_cents=0,next_cost_cents=0);o='ok'
    except Exception as e:o=type(e).__name__
    p=ParallelActiveCheck(g,clock=lambda:1101)
    try: p.check_active(a,spent_cents=0,next_cost_cents=0);n='ok'
    except Exception as e:n=type(e).__name__
    p.close();return o,n
muts={
 'none':lambda s,g,a:None,
 'terminal':lambda s,g,a:s.records.__setitem__(g._key('terminal',a.run_id),{'x':1}),
 'del_claim':lambda s,g,a:s.records.pop(g._key('claim',a.run_id)),
 'campaign_changed':lambda s,g,a:s.records.__setitem__(g._key('campaign'),{'bad':1}),
 'plan_mutated':lambda s,g,a:g.plan.__setitem__('campaign_id','zz'),
}
for k,m in muts.items(): print(k,both(m))
s,g,a=setup()
class Slow:
    def __init__(s2,inner):s2.i=inner
    def get(s2,k,d=None):time.sleep(0.3);return s2.i.get(k,d)
    def put(s2,*a,**k):return s2.i.put(*a,**k)
g.store=Slow(s);p=ParallelActiveCheck(g,clock=lambda:1101,readers=1,read_timeout=0.5)
try:p.check_active(a,spent_cents=0);print('slow: ok?!')
except TimeoutError as e:print('slow: Timeout',e)
try:p.check_active(a,spent_cents=0)
except GuardError as e:print('reuse:',e)
p.close()
print('store attrs',[x for x in vars(s)])
# reconciliation fence on parent
s,g,a=setup()
slots=list(g.plan['slots']); other=[x for x in slots if x!=a.run_id][0]
s.records[g._key('reconciliation',other)]={'parent_run_id':a.run_id}
p=ParallelActiveCheck(g,clock=lambda:1101)
try:p.check_active(a,spent_cents=0);print('recon: ok?!')
except GuardError as e:print('recon fence:',e)
p.close()
# transport failure
s,g,a=setup()
class Bad:
    def get(s2,k,d=None):raise ConnectionError('net')
g.store=Bad();p=ParallelActiveCheck(g,clock=lambda:1101)
try:p.check_active(a,spent_cents=0)
except ConnectionError as e:print('transport: fail-closed',p.failed)
p.close()
# after-read clock past deadline
s,g,a=setup();p=ParallelActiveCheck(g,clock=lambda:1300)
try:p.check_active(a,spent_cents=0);print('late ok?!')
except GuardError as e:print('late clock:',e)
p.close()
