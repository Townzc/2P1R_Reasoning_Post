"""Bind preserved failed r1 and its original upload without repeating either."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import math

from experiments.sft_allocation_midpoint.common import read, sha, digest

R1 = 'C1_original_token_base_forward_r1'
KEY = 'c1/original_token_base_forward_r1'
FAILURE_REPORT_SHA = 'ecca9526ea51416f5b5e619e1d57ecac2c83900d3a489b091b9929d409b63450'


def checked_files(root, items):
    if not items:
        raise ValueError('Exact original evidence files required')
    result = {}
    for label, item in items.items():
        path = Path(item['path'])
        if (path.is_absolute() or '..' in path.parts or (Path(root)/path).is_symlink()
                or sha(Path(root)/path) != item['sha256']):
            raise ValueError('Preserved original evidence bytes changed')
        result[label] = read(Path(root)/path)
    return result


def original_upload(root, spec):
    b = spec['reused_input_upload']
    values = checked_files(root, {'completed': b['completed_file'], 'original_spec': b['original_spec_file']})
    done, original = values['completed'], values['original_spec']
    if (b['original_spec_file_sha256'] != b['original_spec_file']['sha256']
            or done['spec_file_sha256'] != b['original_spec_file_sha256']
            or done['source_files'] != b['original_source_files']
            or original['source_files'] != b['original_source_files']
            or original['input_files'] != spec['input_files']
            or done['input_files'] != spec['input_files']
            or done.get('all_remote_file_bytes_read_back') is not True):
        raise ValueError('Original successful upload and same eighteen inputs required')
    return done


def preserved(root, spec):
    values = checked_files(root, spec['prior_failed_C1']['files'])
    provider, terminal, review = values['provider'], values['failure'], values['review']
    sub, intent = values['submitted'], values['intent']
    if (intent['logical_id'] != R1 or sub['logical_id'] != R1
            or sub['app_id'] != terminal['app_id'] or provider['app_id'] != sub['app_id']
            or terminal.get('status') != 'failed' or terminal.get('automatic_retry_allowed') is not False
            or provider.get('state') != 'stopped' or type(provider.get('owned_containers')) is not int
            or provider['owned_containers'] != 0
            or any(type(x) not in (float, int) or not math.isfinite(x)
                   for x in (terminal['finished_epoch'], provider['observed_epoch']))
            or provider['observed_epoch'] < terminal['finished_epoch']
            or intent['budget']['category'] != 'C'
            or Decimal(intent['budget']['new_reserved_usd']) != Decimal('3.74')
            or review.get('decision') != 'PASS' or review.get('report_sha256') != FAILURE_REPORT_SHA
            or review.get('original_failed_call_integrity_accepted') is not True
            or review.get('C1_completed') is not False):
        raise ValueError('Exact failed r1, retained3.74 and actual failure review required')
    for name in ('dispatch', 'claim', 'terminal'):
        saved = values['named_' + name]
        if saved['key'] != KEY + '/' + name or saved['value'] is None:
            raise ValueError('Original permanent parent fence evidence missing')
    if (values['named_dispatch']['value'] != intent
            or values['named_terminal']['value'] != terminal
            or values['named_claim']['value']['dispatch_sha256'] != digest(intent)):
        raise ValueError('Original failed parent named records differ')
    return values


def records_with_failed_parent(root, spec, records):
    """Saved STOPPED0 is used for the original failed app; no closed-app repoll."""
    values = preserved(root, spec)
    records = deepcopy(records)
    matches = [x for x in records if x['logical_id'] == R1]
    if len(matches) != 1 or matches[0].get('app_id') != values['submitted']['app_id']:
        raise ValueError('Complete shared ledger must retain original failed attempt')
    item = matches[0]
    if (item['budget'] != values['intent']['budget']
            or item['execution'] != values['intent']['execution']):
        raise ValueError('Original failed reservation or execution changed')
    item['saved_provider'] = values['provider']
    item['preserved_failed_terminal'] = values['failure']
    return records


def remote_fences(root, spec, store):
    """Only the three required parent fence keys; no ledger enumeration or model."""
    values = preserved(root, spec)
    for name in ('dispatch', 'claim', 'terminal'):
        if store.get(KEY + '/' + name) != values['named_' + name]['value']:
            raise ValueError('Original remote failed parent fence changed or missing')
