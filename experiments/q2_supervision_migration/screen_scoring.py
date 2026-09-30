"""Synchronous dual-suite scoring; imports and candidate execution stay in Linux workers."""
from __future__ import annotations
import json
import os
from pathlib import Path
import pickle

from .contracts import SuiteVerdict, VerdictStatus
from .gpu_profile import ProfileError, durable_json, sha256


def score_pair(problem, reference, code, checker, *, fast_check=False, recover_initialization=False):
    result={}
    for label,suite in [('base','base'),('extra','plus')]:
        try:
            inputs,expected=problem[f'{suite}_input'],reference[suite]
            timings=reference[f'{suite}_time']
            if len(expected)!=len(inputs) or len(timings)!=len(inputs):
                raise ProfileError('canonical reference metadata misaligned')
            if not inputs:
                if label!='extra': raise ProfileError('empty base suite is not admitted')
                result[label]={'status':'pass','detail':json.dumps({'test_count':0,'tests_observed':0,'vacuous_empty_extra':True})}
                continue
            status,details=checker('mbpp',code,inputs,problem['entry_point'],expected=expected,
                                   atol=problem['atol'],ref_time=timings,fast_check=fast_check)
            recovery=None
            if status=='timeout' and recover_initialization:
                from .initialization_guard import diagnose_initialization_timeout
                recovery=diagnose_initialization_timeout('mbpp',code,inputs,problem['entry_point'],
                    expected,problem['atol'],timings,fast_check)
                recovery['original_status']='timeout'
                recovery['original_tests_observed']=len(details)
                if recovery['confirmed_candidate_initialization_timeout']:
                    status,details='fail',recovery['observed']
            if status not in ('pass','fail','timeout'):
                raise ProfileError('unknown evaluator outcome')
            if status=='pass' and (len(details)!=len(inputs) or not all(details)):
                raise ProfileError('incomplete PASS is a scorer error')
            result[label]={'status':status,'detail':json.dumps({'tests_observed':len(details),
                'test_count':len(inputs),'test_passes_observed':sum(bool(x) for x in details),
                'initialization_timeout_diagnosis':recovery,
                'inner_fail_attribution':'EvalPlus internal FAIL can conflate candidate and inner exceptions'})}
        except BaseException as exc:
            result[label]={'status':'scorer_error','detail':repr(exc)}
    return result


def load_problems(data_path,data_sha):
    os.environ['MBPP_OVERRIDE_PATH']=str(Path(data_path).resolve())
    if sha256(data_path)!=data_sha: raise ProfileError('MBPP input changed')
    from evalplus.data import get_mbpp_plus
    return get_mbpp_plus(version='v0.2.0')


def load_references(root):
    root=Path(root); manifest=json.loads((root/'manifest.json').read_text())
    if sha256(root/'groundtruth.pickle')!=manifest['sha256']:
        raise ProfileError('owned reference cache changed')
    # Only the cache computed in this study's bounded reference worker is loaded.
    with (root/'groundtruth.pickle').open('rb') as f: gt=pickle.load(f)
    if sorted(gt)!=manifest['task_ids']: raise ProfileError('reference task IDs changed')
    return gt,manifest


def scoring_process(conn,data_path,data_sha,reference_root,selected,fast_check=False,recover_initialization=False):
    try:
        os.environ['CUDA_VISIBLE_DEVICES']=''
        problems=load_problems(data_path,data_sha);refs,manifest=load_references(reference_root)
        if manifest['data_sha256']!=data_sha: raise ProfileError('reference data identity mismatch')
        if not set(selected)<=set(problems) or not set(selected)<=set(refs):
            raise ProfileError('missing frozen reference task')
        from evalplus.eval import untrusted_check
        conn.send({'ready':True,'prompts':{k:problems[k]['prompt'] for k in selected}})
        while True:
            request=conn.recv()
            if request is None: return
            task,code=request
            if task not in selected: raise ProfileError('task outside phase')
            conn.send(score_pair(problems[task],refs[task],code,untrusted_check,
                fast_check=fast_check,recover_initialization=recover_initialization))
    except BaseException as exc:
        try: conn.send({'fatal':repr(exc)})
        except (EOFError,BrokenPipeError): pass
    finally: conn.close()
