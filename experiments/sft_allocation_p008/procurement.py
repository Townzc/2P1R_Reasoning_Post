"""Exact virtual procurement wallets over a shared, non-oracular candidate cache.

Only public history and known prompts enter action selection. Calls consume no
cache rows until after an immutable proposal/reservation has been committed.
Physical cache cost remains outside these hypothetical policy wallets.
"""
from fractions import Fraction
from experiments.sft_allocation_acquisition.policy_contract import Policy
from .contract import BASE_CAP,M


def fraction(value):
    return dict(numerator=value.numerator,denominator=value.denominator)


class Wallet:
    def __init__(self,ordered_ids,prompt_lengths,draw,budget_multiple,price_level,policy):
        if draw not in (1,2) or budget_multiple not in (1,4,8) or price_level not in (0,4) or policy not in ('breadth','depth'):
            raise ValueError('Unregistered virtual policy')
        if set(ordered_ids)!=set(prompt_lengths) or any(type(n) is not int or n<=0 or n+1024>2048 for n in prompt_lengths.values()):
            raise ValueError('Prompt lengths must be known before outcomes, without truncation')
        self.policy=Policy(list(ordered_ids),1 if policy=='breadth' else 4)
        self.name=f'd{draw}_b{budget_multiple}_p{price_level}_{policy}'
        self.draw=draw;self.lengths=dict(prompt_lengths);self.price=price_level*M
        self.cap=Fraction(BASE_CAP*budget_multiple);self.spent=Fraction(0);self.pending=None
        self.stop_reason=None;self.settlements=[];self.consumed=[]

    def propose(self):
        if self.pending is not None:raise ValueError('Unsettled reservation cannot be replaced')
        if self.stop_reason is not None:return None
        action=self.policy.propose()
        if len(action['items'])!=16:
            self.stop_reason='no_full16_action';return None
        reserved=self.price*len(action['new_problem_ids'])+sum(self.lengths[x['problem_id']]+1024 for x in action['items'])
        if self.spent+reserved>self.cap:
            self.stop_reason='cannot_reserve_full16_action';return None
        # There is intentionally no cache, length-of-return, score or teacher access here.
        return dict(wallet=self.name,batch=f'batch_{len(self.settlements):04d}',action=action,
            reserved_units=fraction(reserved),spent_before=fraction(self.spent),cap=fraction(self.cap))

    def begin(self,proposal):
        if proposal!=self.propose() or proposal is None:raise ValueError('Changed/unpayable proposal')
        self.policy.begin(proposal['batch'],proposal['action']);self.pending=proposal

    def settle(self,rows):
        if self.pending is None:raise ValueError('Cannot see outputs before committing action')
        p=self.pending;items=p['action']['items']
        if len(rows)!=16 or [dict(problem_id=r['problem_id'],attempt=r['attempt']) for r in rows]!=items:
            raise ValueError('Foreign/reordered candidate consumption')
        for r in rows:
            expected=f"d{self.draw}::{r['problem_id']}::{r['attempt']}"
            if (r['candidate_id']!=expected or type(r['usable']) is not bool
                    or r['prompt_tokens']!=self.lengths[r['problem_id']] or type(r['completion_tokens']) is not int
                    or not 0<r['completion_tokens']<=1024):
                raise ValueError('Unknown/incorrect identity or token count; preserve unresolved work')
        reserved=Fraction(**{'numerator':p['reserved_units']['numerator'],'denominator':p['reserved_units']['denominator']})
        charge=self.price*len(p['action']['new_problem_ids'])+sum(r['prompt_tokens']+r['completion_tokens'] for r in rows)
        if charge>reserved or self.spent+charge>self.cap:raise ValueError('Overspend')
        self.policy.complete(p['batch'],rows);self.spent+=charge;self.consumed.extend(rows)
        done=dict(wallet=self.name,batch=p['batch'],candidate_ids=[r['candidate_id'] for r in rows],
            charged_units=fraction(charge),cumulative_units=fraction(self.spent),reserved_units=p['reserved_units'])
        self.settlements.append(done);self.pending=None;return done

    def summary(self):
        return dict(wallet=self.name,**self.policy.summary(),cap=fraction(self.cap),charge=fraction(self.spent),
            unused_fraction=fraction((self.cap-self.spent)/self.cap),stop_reason=self.stop_reason,
            usable_answers=sum(r['usable'] for r in self.consumed),
            covered_parents=len({r['problem_id'] for r in self.consumed if r['usable']}),
            consumed_candidate_ids=[r['candidate_id'] for r in self.consumed],
            accepted_candidate_ids=[r['candidate_id'] for r in self.consumed if r['usable']])


def pending_union(wallets,cache):
    """Only committed actions. Never determine affordability from cached returns."""
    missing={}
    for w in wallets:
        if w.pending is None:continue
        for item in w.pending['action']['items']:
            key=f"d{w.draw}::{item['problem_id']}::{item['attempt']}"
            if key not in cache:
                if item['attempt']>1 and f"d{w.draw}::{item['problem_id']}::{item['attempt']-1}" not in cache:
                    raise ValueError('Attempt prefix is unavailable')
                missing[key]=dict(draw=w.draw,**item,candidate_id=key)
    return [missing[k] for k in sorted(missing)]


def replay(ordered_ids,prompt_lengths,draw,budget_multiple,price_level,policy,events,cache):
    w=Wallet(ordered_ids,prompt_lengths,draw,budget_multiple,price_level,policy)
    for event in events:
        proposal=w.propose()
        if proposal!=event['intent']:raise ValueError('Not a legal prefix/pre-output reservation')
        w.begin(proposal)
        keys=[f"d{draw}::{r['problem_id']}::{r['attempt']}" for r in proposal['action']['items']]
        done=w.settle([cache[k] for k in keys])
        if done!=event['done']:raise ValueError('Payment differs from immutable candidate cache')
    if w.propose() is not None:raise ValueError('Policy tape ended before legal stopping; report incomplete')
    return w.summary()
