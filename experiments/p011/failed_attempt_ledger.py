"""Read completed and explicitly bound failed attempts without inventing RESULT.

This changes only local admission evidence. Original files and reservations are
read-only; every saved failed terminal must be bound by the exact reviewed SPEC.
"""
from pathlib import Path
from decimal import Decimal
import math
import re
from experiments.p011 import c1_outer
from experiments.sft_allocation_midpoint.common import read, sha, digest


def bound_failure(root, logical, binding, intent, submitted, provider):
    expected={'intent','submitted','failure','provider','named_dispatch',
              'named_claim','named_terminal','preservation'}
    if set(binding.get('files',{}))!=expected:
        raise ValueError('Complete original failed-attempt binding required')
    values={}
    for label,item in binding['files'].items():
        p=Path(item['path'])
        if (p.is_absolute() or '..' in p.parts or (Path(root)/p).is_symlink()
                or sha(Path(root)/p)!=item['sha256']):
            raise ValueError('Original failed-attempt evidence changed')
        values[label]=read(Path(root)/p)
    terminal=values['failure'];preserved=values['preservation'];key=binding['key']
    reserve=Decimal(str(binding['reserved_usd']))
    if (values['intent']!=intent or values['submitted']!=submitted
            or values['provider']!=provider or terminal.get('status')!='failed'
            or terminal.get('logical_id')!=logical or terminal.get('app_id')!=submitted['app_id']
            or terminal.get('automatic_retry_allowed') is not False
            or type(terminal.get('finished_epoch')) not in (int,float)
            or not math.isfinite(terminal['finished_epoch'])
            or provider['observed_epoch']<terminal['finished_epoch']
            or not reserve.is_finite() or reserve<=0
            or intent['budget']['category']!=binding['category']
            or Decimal(str(intent['budget']['new_reserved_usd']))!=reserve
            or preserved.get('stable_inventory') is not True
            or preserved.get('scientific_completion') is not False):
        raise ValueError('Original failed terminal/provider/reservation differs')
    for name in ('dispatch','claim','terminal'):
        if values['named_'+name].get('key')!=key+'/'+name or values['named_'+name].get('value') is None:
            raise ValueError('Original failed named fences absent')
    claim=values['named_claim']['value']
    if (values['named_dispatch']['value']!=intent or values['named_terminal']['value']!=terminal
            or claim.get('logical_id')!=logical or claim.get('app_id')!=submitted['app_id']
            or claim.get('execution')!=intent['execution'] or claim.get('dispatch_sha256')!=digest(intent)):
        raise ValueError('Original failed dispatch/claim/terminal inconsistent')
    return terminal


def ledger(root,spec):
    base=Path(root)/c1_outer.LOCAL/'dispatch'; bindings=spec.get('failed_attempt_bindings',{})
    if not isinstance(bindings,dict) or not bindings:
        raise ValueError('Exact saved failed-attempt bindings absent')
    records=[];seen=set()
    if not base.is_dir():raise ValueError('Original shared attempt ledger absent')
    for directory in sorted(base.iterdir()):
        if not directory.is_dir() or directory.is_symlink():raise ValueError('Unexpected ledger entry')
        intent=read(directory/'INTENT.json');logical=directory.name
        if logical!=intent['logical_id']:raise ValueError('Shared dispatch identity differs')
        value=dict(intent);value.pop('app_id',None)
        submitted=None
        if (directory/'SUBMITTED.json').exists():
            submitted=read(directory/'SUBMITTED.json')
            if (submitted['logical_id']!=logical
                    or not re.fullmatch(r'ap-[A-Za-z0-9]+',submitted['app_id'])
                    or not re.fullmatch(r'fc-[A-Za-z0-9]+',submitted['call_id'])):
                raise ValueError('Original submission identity invalid')
            value['app_id']=submitted['app_id']
        proof_file=directory/'PROVIDER_STOPPED0.json'
        if proof_file.exists():
            provider=read(proof_file)
            if (submitted is None or provider.get('app_id')!=submitted['app_id']
                    or provider.get('state')!='stopped'
                    or type(provider.get('owned_containers')) is not int or provider['owned_containers']!=0
                    or type(provider.get('observed_epoch')) not in (int,float)
                    or not math.isfinite(provider['observed_epoch'])):
                raise ValueError('Saved STOPPED0 identity/time differs')
            if logical in bindings:
                if (directory/'RESULT.json').exists():raise ValueError('Failed parent cannot have a completed result')
                terminal=bound_failure(root,logical,bindings[logical],intent,submitted,provider)
                value['preserved_failed_terminal']=terminal;seen.add(logical)
            else:
                result=read(directory/'RESULT.json')
                if (result.get('status')!='completed' or result.get('app_id')!=submitted['app_id']
                        or type(result.get('finished_epoch')) not in (int,float)
                        or not math.isfinite(result['finished_epoch'])
                        or provider['observed_epoch']<result['finished_epoch']):
                    raise ValueError('Saved completed result/provider mismatch')
            value['saved_provider']=provider
        elif logical in bindings:
            raise ValueError('Reviewed failed parent STOPPED0 proof absent')
        records.append(value)
    if seen!=set(bindings):raise ValueError('Reviewed failed attempts missing from complete shared ledger')
    return records


def remote_fences(root,spec,store):
    """Read only exact saved failed-parent keys, never poll its closed app."""
    for binding in spec['failed_attempt_bindings'].values():
        for name in ('dispatch','claim','terminal'):
            item=binding['files']['named_'+name];p=Path(item['path'])
            if p.is_absolute() or '..' in p.parts or sha(Path(root)/p)!=item['sha256']:
                raise ValueError('Failed fence evidence bytes differ')
            saved=read(Path(root)/p)
            if saved['key']!=binding['key']+'/'+name or store.get(saved['key'])!=saved['value']:
                raise ValueError('Original remote failed fence differs')
