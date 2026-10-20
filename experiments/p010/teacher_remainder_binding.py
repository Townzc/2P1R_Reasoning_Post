"""Bind a proposed once-only suffix to the intact failed T7 first batch."""
from pathlib import Path
from experiments.p010.common import read,sha,digest


def check_owner(owner,spec):
    expected=spec['t7_remainder_proposal']
    if (not isinstance(owner,dict) or owner.get('scope')!='p010-T7-unattempted-suffix'
            or owner.get('approved') is not True
            or owner.get('proposal_sha256')!=digest(expected)
            or not owner.get('direct_owner_message')
            or owner.get('new_output_replay_allowed') is not False
            or owner.get('extra_G_reserve_usd')!='5.50'):
        raise ValueError('Direct owner exception to no-automatic-retry is required')


def parent_prefix(store,volume,spec):
    p=spec['t7_remainder_proposal'];base=Path('/evidence/p010-20261019/teachers/t7')
    volume.reload()
    if (store.get('teacher/t7/claim')!=p['original_claim']
            or store.get('teacher/t7/terminal')!=p['original_terminal']
            or store.get('teacher/t7/done/00000') is not None):
        raise ValueError('Original failed parent or unacknowledged prefix changed')
    for name,expected in p['original_files'].items():
        if sha(base/name)!=expected:
            raise ValueError('Original failed-parent bytes changed')
    raw=read(base/'raw/00000.json');intent=read(base/'intents/00000.json')
    if len(raw)!=256 or len(intent['rows'])!=256:
        raise ValueError('Only the original256 outputs may be inherited')
    if any(x['candidate_id']!=r['candidate_id'] for x,r in zip(raw,intent['rows'])):
        raise ValueError('Parent request/raw mapping differs')
    return dict(raw=raw,rows=intent['rows'],raw_file_sha256=p['original_files']['raw/00000.json'],
                failed_interval_proxy_seconds=p['failed_interval_proxy_seconds'])
