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


def run_confirmed_forward(model, tasks, memberships, out, basis, deadline_epoch):
    """Called only by the future exact reviewed entry, once after its global claim.

    Batch size32 is journal grouping, not padded model inference. Each unique
    original token/mask sequence receives one forward. A partial chunk or job is
    permanently retained; this function has no resume/retry or partial summary.
    """
    if (type(deadline_epoch) not in (int,float) or not math.isfinite(deadline_epoch)
            or deadline_epoch <= time.time() or not tasks or not basis):
        raise ValueError('Bounded admitted C1 basis/window required')
    needed={r['sequence_sha256'] for rows in memberships.values() for r in rows}
    if needed != set(tasks):raise ValueError('Exact complete membership roster required')
    for key,task in tasks.items():
        if (key != task['sequence_sha256']
                or key != digest({'input_ids':task['input_ids'],'labels':task['labels']})):
            raise ValueError('Frozen task identity differs')
    out=Path(out);out.mkdir(parents=False,exist_ok=False)
    basis_sha=digest(basis);keys=sorted(tasks);confirmed={};started=time.monotonic()
    try:
        dump(out/'INTENT.json',{'basis':basis,'basis_sha256':basis_sha,
            'task_ids':keys,'membership_sha256':digest(memberships),
            'deadline_epoch':deadline_epoch,'forward_retries':0,'chunk_size':32})
        dump(out/'MEMBERSHIPS.json',memberships)
        for first in range(0,len(keys),32):
            chunk=out/'chunks'/f'{first//32:05d}';chunk.mkdir(parents=True,exist_ok=False)
            part=keys[first:first+32];tick=time.monotonic()
            dump(chunk/'INTENT.json',{'first_index':first,'sequence_ids':part,'basis_sha256':basis_sha})
            records=[]
            for key in part:
                if time.time() >= deadline_epoch:raise TimeoutError('Original C1 deadline reached')
                task=tasks[key];attempt=time.monotonic()
                dump(chunk/(key+'.ATTEMPT.json'),{'sequence_sha256':key,'basis_sha256':basis_sha,
                                                'started_epoch':time.time()})
                result=c1_nll.forward_one(model,task)
                validate_forward_result(task,result)
                record={'result':result,'forward_seconds':time.monotonic()-attempt,
                        'basis_sha256':basis_sha,'task_sha256':digest(task)}
                dump(chunk/(key+'.RESULT.json'),record)
                records.append({'sequence_sha256':key,'result_file_sha256':sha(chunk/(key+'.RESULT.json'))})
                confirmed[key]=result
            dump(chunk/'CONFIRMED.json',{'basis_sha256':basis_sha,'first_index':first,
                'records':records,'count':len(part),'elapsed_seconds':time.monotonic()-tick,
                'final_confirmation_write_excluded_from_elapsed':True})
        if time.time() >= deadline_epoch:raise TimeoutError('C1 completion deadline reached')
        summary=c1_nll.descriptive_summary(memberships,confirmed)
        dump(out/'DESCRIPTIVE_SUMMARY.json',summary)
        dump(out/'ALL_CONFIRMED.json',{'basis_sha256':basis_sha,'unique_sequences':len(keys),
            'chunks':(len(keys)+31)//32,'summary_file_sha256':sha(out/'DESCRIPTIVE_SUMMARY.json'),
            'elapsed_seconds':time.monotonic()-started,'final_marker_write_excluded_from_elapsed':True,
            'actual_A3_accepted':False})
        return summary
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'message':str(exc),
            'basis_sha256':basis_sha,'automatic_retry_allowed':False,
            'partial_is_not_a_completed_summary':True})
        raise


def check_confirmed_evidence(out,tasks,memberships,basis):
    """Read-only closure verification; no forwards, tokenization or statistics."""
    out=Path(out);intent=read(out/'INTENT.json');final=read(out/'ALL_CONFIRMED.json')
    keys=sorted(tasks);basis_sha=digest(basis)
    if ((out/'FAILED.json').exists() or intent['basis_sha256']!=basis_sha
            or intent['task_ids']!=keys or intent['membership_sha256']!=digest(memberships)
            or read(out/'MEMBERSHIPS.json')!=memberships or final['basis_sha256']!=basis_sha
            or final['unique_sequences']!=len(keys) or final['chunks']!=(len(keys)+31)//32
            or final['summary_file_sha256']!=sha(out/'DESCRIPTIVE_SUMMARY.json')):
        raise ValueError('Complete exact C1 evidence required')
    for first in range(0,len(keys),32):
        part=keys[first:first+32];chunk=out/'chunks'/f'{first//32:05d}'
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
