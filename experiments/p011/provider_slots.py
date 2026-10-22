"""Normalize observed Modal CLI list schemas without dropping unknown slots."""


def shared_slots(apps, containers):
    if not isinstance(apps, list) or not isinstance(containers, list):
        raise ValueError('Unknown provider list schema')
    slots = 0
    identities = set()
    for row in apps:
        identity = row.get('app_id', row.get('App ID'))
        if not identity or identity in identities:
            raise ValueError('Missing or duplicate app identity')
        identities.add(identity)
        fields = {}
        for lower, upper in [('state', 'State'), ('tasks', 'Tasks')]:
            if lower in row and upper in row and row[lower] != row[upper]:
                raise ValueError('Conflicting provider field aliases')
            if lower not in row and upper not in row:
                raise ValueError('Missing provider slot field')
            fields[lower] = row[lower] if lower in row else row[upper]
        raw = str(fields['tasks'])
        if not raw.isdigit():
            raise ValueError('Unknown task count is not zero')
        tasks = int(raw)
        if str(fields['state']).lower() != 'stopped' or tasks:
            slots += max(1, tasks)
    return max(slots, len(containers))
