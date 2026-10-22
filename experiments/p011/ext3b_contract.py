"""Direct owner options2+3: immutable prefix reuse, new3B dose, same90/45caps."""
from pathlib import Path
from experiments.p011.owner_0205_common import read, sha

LARGE = 'long_R9072x1_S-F15_s17'
SMALL = 'long_R3024xE3_S-F15_s17'
INPUTS = Path('.local/p011_20261020/r1/ext3b_inputs_r1')
PRIOR_INPUTS = Path('.local/p011_20261020/r1/ext4b_inputs_r1')
OWNER = 'reports/p011_20261020/EXT3B_OWNER_OPTIONS_2_3_20261022.json'
DATA_SPEC = 'reports/p011_20261020/ext3b_prefix_input_preflight_v1/SPEC.json'
DATA_SCOPE = 'p011-ext-3B-prefix-input-reschedule-CR'


def prefix_metadata(rows):
    if (len(rows) != 12096 or len({r['path_id'] for r in rows}) != 12096
            or len({r['parent_sha256'] for r in rows}) != 12096
            or any(type(r['n_supervised']) is not int or r['n_supervised'] <= 0 for r in rows)):
        raise ValueError('Exact completed12096 unique original roster required')
    return rows[:9072], rows[:3024]


def admit_data(spec_path, review_path):
    spec, cr = read(spec_path), read(review_path)
    owner = read(OWNER)
    if (spec['owner_amendment_sha256'] != sha(OWNER) or owner['adopted_options'] != [2,3]
            or owner['large_questions'] != 9072 or owner['small_questions'] != 3024
            or owner['pair_cap_usd'] != 90 or owner['per_cell_cap_usd'] != 45
            or spec['jobs'] != [LARGE,SMALL] or spec['output'] != str(INPUTS)
            or cr.get('scope') != DATA_SCOPE or cr.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or cr.get('spec_sha256') != sha(spec_path) or cr.get('source_files') != spec['source_files']
            or sha(cr['local_report_path']) != cr['report_sha256']
            or any(cr.get(k) is not True for k in spec['required_flags'])):
        raise ValueError('Exact new owner options2+3 prefix/dose source CR required')
    for p,h in spec['source_files'].items():
        if sha(p) != h:raise ValueError('Prefix source changed '+p)
    return spec
