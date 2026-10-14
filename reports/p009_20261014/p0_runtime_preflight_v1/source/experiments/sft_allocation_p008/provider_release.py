"""Read exact provider identities; recent-app list absence is not release proof."""
import json
import subprocess


def validate_stopped_apps(app_ids, infos, containers):
    if len(set(app_ids)) != len(app_ids) or len(infos) != len(app_ids):
        raise ValueError('Exact unique provider roster required')
    if containers:
        raise ValueError('Require zero current containers before single-child dispatch')
    for expected, info in zip(app_ids, infos):
        if (info.get('app_id') != expected
                or info.get('lifecycle', {}).get('state') != 'stopped'
                or not info['lifecycle'].get('stopped_at')):
            raise ValueError('Exact original app is not confirmed stopped')
    return infos


def read_stopped_apps(cli, app_ids, containers):
    # CLI app info resolves each exact ID via AppGetLifecycle/AppGetInfo.
    # Errors, missing IDs and unknown states propagate; never synthesize rows.
    infos = [json.loads(subprocess.check_output(
        [cli, 'app', 'info', app_id, '--json'], text=True, timeout=30))
        for app_id in app_ids]
    return validate_stopped_apps(app_ids, infos, containers)
