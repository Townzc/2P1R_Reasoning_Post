"""C1 input/evidence adapter, prepared only; a reviewed full entry must admit it.

No tokenizer, model loader, generator, optimizer or retry. Source manifests are
original input producers, not regenerated teacher answers. Once-only forward
chunks retain failures and require full confirmation before descriptive output.
"""
import math
from pathlib import Path
import time

from experiments.sft_allocation_midpoint.common import digest, dump, read, sha, verify
from experiments.p011 import c1_nll

ORIGINAL_ROOTS = {
    't15': '.local/p009_20261014/r1/stage1_s1_inputs_r1',
    't7': '.local/p010_20261019/r1/student_inputs_r2',
    't72': '.local/p010_20261019/r1/student_inputs_r2',
}


def original_names(teacher, n):
    if teacher not in ORIGINAL_ROOTS or n not in (400, 3200):
        raise ValueError('Only the six original C1 groups')
    if teacher == 't15':
        return {k: f's1_s17_n{n}_{k}.json' for k in ('config','rows','encoded')}
    return {k: f'{teacher}_s17_n{n}_k1/{k}.json' for k in ('config','rows','encoded')}


def load_original_groups(binding):
    expected={f'{t}_n{n}' for t in ORIGINAL_ROOTS for n in (400,3200)}
    if set(binding) != expected:
        raise ValueError('Exact six original group bindings required')
    groups={}
    for name in sorted(expected):
        teacher, n=name.split('_n'); n=int(n); b=binding[name]
        root=Path(ORIGINAL_ROOTS[teacher]); names=original_names(teacher,n)
        if b['root'] != str(root) or b['filenames'] != names or set(b['files']) != set(names.values()):
            raise ValueError('C1 source must trace to original exact writer paths')
        manifest_path=root/'MANIFEST.json'
        if manifest_path.is_symlink() or sha(manifest_path) != b['original_manifest_sha256']:
            raise ValueError('Original input manifest changed')
        original=read(manifest_path)
        if any(original.get(f) != item for f,item in b['files'].items()):
            raise ValueError('Input binding not a member of the original manifest')
        verify(root,b['files'])
        groups[name]={k:read(root/f) for k,f in names.items()}
    return groups


def validate_forward_result(task, obj):
    values=obj['token_nll']
    if (obj['sequence_sha256'] != task['sequence_sha256']
            or obj['target_positions'] != task['target_positions']
            or obj['supervised_tokens'] != task['supervised_tokens']
            or len(values) != task['supervised_tokens']
            or any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in values)
            or obj['nll_sum'] != math.fsum(values)
            or obj['mean_nll'] != math.fsum(values)/len(values)):
        raise ValueError('Exact finite original-span forward result required')


def check_confirmed_evidence(out,tasks,memberships,basis):
    """Read-only closure verification; no forwards, tokenization or statistics."""
    out=Path(out);intent=read(out/'INTENT.json');final=read(out/'ALL_CONFIRMED.json')
    keys=sorted(tasks);basis_sha=digest(basis)
    if ((out/'FAILED.json').exists() or intent['basis_sha256']!=basis_sha
            or intent.get('chunk_size')!=320 or intent['task_ids']!=keys or intent['membership_sha256']!=digest(memberships)
            or read(out/'MEMBERSHIPS.json')!=memberships or final['basis_sha256']!=basis_sha
            or final['unique_sequences']!=len(keys) or final['chunks']!=(len(keys)+319)//320
            or final['summary_file_sha256']!=sha(out/'DESCRIPTIVE_SUMMARY.json')):
        raise ValueError('Complete exact C1 evidence required')
    for first in range(0,len(keys),320):
        part=keys[first:first+320];chunk=out/'chunks'/f'{first//320:05d}'
        plan=read(chunk/'INTENT.json');ack=read(chunk/'CONFIRMED.json')
        if (plan!={'basis_sha256':basis_sha,'first_index':first,'sequence_ids':part}
                or ack['basis_sha256']!=basis_sha or ack['first_index']!=first
                or ack['count']!=len(part)
                or [r['sequence_sha256'] for r in ack['records']]!=part):
            raise ValueError('Partial or changed chunk confirmation')
        for item in ack['records']:
            key=item['sequence_sha256'];path=chunk/(key+'.RESULT.json')
            if sha(path)!=item['result_file_sha256']:raise ValueError('Saved forward bytes changed')
            record=read(path);attempt=read(chunk/(key+'.ATTEMPT.json'))
            if (record['basis_sha256']!=basis_sha or record['task_sha256']!=digest(tasks[key])
                    or attempt['sequence_sha256']!=key or attempt['basis_sha256']!=basis_sha):
                raise ValueError('Original task/basis/attempt binding differs')
            validate_forward_result(tasks[key],record['result'])
    return {'complete':True,'unique_sequences':len(keys),'new_forward_calls':0,
            'statistics_recomputed':False,'actual_A3_accepted':False}
