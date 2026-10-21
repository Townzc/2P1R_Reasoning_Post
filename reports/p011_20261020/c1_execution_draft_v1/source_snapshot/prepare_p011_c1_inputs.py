"""Future one-time C1 original-byte copy; full shared C1 CR required first.

Does not tokenize, normalize, score, load a model, or repeat teacher outputs.
Both local and future worker validate original saved token sequences unchanged.
"""
import argparse
import json
from pathlib import Path

from experiments.p011 import c1_evidence, c1_nll
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify

ROOT=Path('.local/p011_20261020/r1')
OUT=ROOT/'c1_inputs_r1'
FENCE=ROOT/'C1_INPUT_COPY_ATTEMPT.json'
SCOPE='p011-C1-complete-path-CR'


def load_pack(root,manifest,expected_inventory):
    root=Path(root);verify(root,manifest)
    names={f'{t}_n{n}' for t in ('t15','t7','t72') for n in (400,3200)}
    expected_files={f'{name}/{kind}.json' for name in names for kind in ('config','rows','encoded')}
    if set(manifest)!=expected_files:
        raise ValueError('Exactly18 original files in six C1 groups required')
    groups={name:{kind:read(root/name/(kind+'.json')) for kind in ('config','rows','encoded')}
            for name in sorted(names)}
    tasks,memberships=c1_nll.inventory(groups)
    actual=inventory_metadata(tasks,memberships)
    if actual!=expected_inventory:
        raise ValueError('Exact original C1 token inventory changed')
    return tasks,memberships


def inventory_metadata(tasks,memberships):
    return {'unique_sequences':len(tasks),'members_per_group':{k:len(v) for k,v in memberships.items()},
        'unique_input_tokens':sum(len(x['input_ids']) for x in tasks.values()),
        'unique_supervised_tokens':sum(x['supervised_tokens'] for x in tasks.values()),
        'max_sequence_length':max(len(x['input_ids']) for x in tasks.values()),
        'tasks_sha256':digest(tasks),'memberships_sha256':digest(memberships),
        'journal_chunks':(len(tasks)+31)//32,'model_batch_size':1,'reencoded_sequences':0,
        'original_EOS':151643,'actual_A1_accepted':False,'paid_runtime_admitted':False}


def prepare(binding_file,code_binding,review_file):
    from datetime import datetime,timezone
    if datetime.now(timezone.utc)>=datetime(2026,10,22,5,tzinfo=timezone.utc):
        raise ValueError('Original P011 cutoff reached')
    source=read(code_binding);review=read(review_file);binding=read(binding_file)
    if (review.get('scope')!=SCOPE or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or review.get('source_files')!=source['source_files']
            or review.get('original_group_binding_sha256')!=sha(binding_file)
            or review.get('input_preparation_authorized') is not True
            or len(review.get('target_commit',''))!=40
            or sha(review['local_report_path'])!=review['report_sha256']):
        raise ValueError('Real exact shared full C1 path CR required before original input copy')
    for path,expected in source['source_files'].items():
        if sha(path)!=expected:raise ValueError('Reviewed C1 source changed')
    if FENCE.exists() or OUT.exists():
        raise ValueError('Original C1 copy already attempted; preserve partial, no retry')
    dump(FENCE,{'utc':datetime.now(timezone.utc).isoformat(),'source_files':source['source_files'],
        'original_group_binding_sha256':sha(binding_file),'review_sha256':sha(review_file)})
    OUT.mkdir();files={}
    try:
        groups=c1_evidence.load_original_groups(binding)
        tasks,memberships=c1_nll.inventory(groups)
        inventory=inventory_metadata(tasks,memberships)
        for name,b in binding.items():
            for kind,oldname in b['filenames'].items():
                path=Path(b['root'])/oldname;newname=f'{name}/{kind}.json';dest=OUT/newname
                dest.parent.mkdir(exist_ok=True)
                with path.open('rb') as src,dest.open('xb') as dst:
                    for block in iter(lambda:src.read(8*1024*1024),b''):dst.write(block)
                item={'sha256':sha(dest),'bytes':dest.stat().st_size}
                if item!=b['files'][oldname]:raise ValueError('Original raw input copy changed')
                files[newname]=item
        dump(OUT/'INPUT_FILES.json',files)
        dump(OUT/'ORIGINAL_GROUP_BINDING.json',binding)
        dump(OUT/'TASK_INVENTORY.json',inventory)
        dump(OUT/'INPUT_COPY_COMPLETED.json',{'utc':datetime.now(timezone.utc).isoformat(),
            'source_files':source['source_files'],'review_sha256':sha(review_file),
            'group_binding_sha256':sha(binding_file),'files':files,
            'task_inventory_sha256':sha(OUT/'TASK_INVENTORY.json'),
            'model_calls':0,'tokenizations':0,'actual_A1_accepted':False})
        dump(OUT/'MANIFEST.json',{p.relative_to(OUT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
                                for p in sorted(OUT.rglob('*')) if p.is_file()})
        return inventory
    except BaseException as exc:
        dump(OUT/'FAILED.json',{'type':type(exc).__name__,'message':str(exc),
            'automatic_retry_allowed':False,'original_inputs_unchanged':True});raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-binding',required=True)
    parser.add_argument('--code-binding',required=True)
    parser.add_argument('--review',required=True)
    args=parser.parse_args();prepare(args.original_binding,args.code_binding,args.review)
