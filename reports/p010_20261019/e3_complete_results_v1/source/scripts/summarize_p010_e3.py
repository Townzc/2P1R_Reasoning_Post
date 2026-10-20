"""Original E3 descriptive metrics from saved outputs/scores; no rescoring."""
import argparse
from pathlib import Path
import os
import threading
from experiments.p010.common import read, dump, sha, digest, utc
from experiments.p010.e3_metrics import summarize


def bind_rows(spec, inputs, generated, scored, old_metadata):
    spec = read(spec); inputs, generated, scored, old_metadata = map(Path, (inputs,generated,scored,old_metadata))
    proof = read(generated/'COMPLETED.json'); score = read(scored/'LOCAL_ORACLE_AUDIT.json')
    if (not proof['passed'] or not read(scored/'COMPLETED.json')['passed']
            or sha(scored/'LOCAL_ORACLE_AUDIT.json') != read(scored/'COMPLETED.json')['oracle_sha256']
            or score['full_generation_proof_sha256'] != sha(generated/'COMPLETED.json')
            or score['scoring_payload_sha256'] != sha(scored/'job/payload/COMPLETED.json')
            or score['old_T08_symbolic_calls'] != 0 or score['technical_unknown'] != 0
            or (scored/'FAILED.json').exists() or (generated/'FAILED.json').exists()
            or sha(inputs/'ORIGINAL_T08_ROWS.json') != spec['original_T08_rows_sha256']
            or sha(old_metadata/'COMPLETED.json') != spec['original_T08_metadata_proof_sha256']
            or sha(inputs/'ROSTER.json') != spec['input_files']['ROSTER.json']['sha256']):
        raise ValueError('Complete original 3200 scores and unchanged original1600 required')
    for name,h in {**spec['source_files'],**spec['verification_source_files']}.items():
        if sha(name)!=h:raise ValueError('Exact frozen source changed: '+name)
    oldproof = read(old_metadata/'COMPLETED.json')
    if (oldproof['original_rows_sha256'] != sha(inputs/'ORIGINAL_T08_ROWS.json')
            or oldproof['length_rows_sha256'] != sha(old_metadata/'PHYSICAL_LENGTHS.json')
            or oldproof['old_raw_decodes'] != 0 or oldproof['old_symbolic_calls'] != 0):
        raise ValueError('Original saved raw-length metadata proof differs')
    lengths = read(old_metadata/'PHYSICAL_LENGTHS.json')
    originals = read(inputs/'ORIGINAL_T08_ROWS.json')
    if len(lengths)!=1600 or len(originals)!=1600:
        raise ValueError('All1600 matched old attempts required')
    all_rows=[]
    for item, meta in zip(originals,lengths):
        row=item['original_record']
        if (meta['candidate_id']!=row['candidate_id'] or item['original_record_sha256']!=digest(row)
                or meta['original_record_sha256']!=digest(row)
                or meta['raw_record_sha256']!=row['raw_record_sha256']):
            raise ValueError('Old original first-eight provenance differs')
        all_rows.append(dict(row,temperature_label='t08',temperature=.8,
                            physical_returned_tokens=meta['physical_returned_tokens']))
    decoded=read(generated/'DECODED_ROWS.json');scores=read(scored/'job/payload/ALL_SCORED_ROWS.json')
    if (len(decoded)!=3200 or len(scores)!=3200 or sha(generated/'DECODED_ROWS.json')!=proof['decoded_rows_sha256']
            or sha(scored/'job/payload/ALL_SCORED_ROWS.json')!=read(scored/'job/payload/COMPLETED.json')['scored_rows_sha256']):
        raise ValueError('Complete original new rows required')
    for row,s in zip(decoded,scores):
        if s['id']!=row['candidate_id'] or type(s['score']['correct']) is not bool:
            raise ValueError('Original score identity/Boolean differs')
        all_rows.append(dict(row,score=s))
    return all_rows,read(inputs/'ROSTER.json')['problem_ids']


def execute(a):
    rows,pids=bind_rows(a.spec,a.inputs,a.generation_oracle,a.scores,a.old_metadata)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(utc=utc(),spec_sha256=sha(a.spec),local_seconds=3600,
        old_symbolic_calls=0,new_symbolic_calls=0,new_raw_decodes=0,new_model_calls=0))
    timer=threading.Timer(3600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        result=summarize(rows,pids)
        dump(out/'METRICS.json',result)
        dump(out/'COMPLETED.json',dict(utc=utc(),passed=True,metrics_sha256=sha(out/'METRICS.json'),
            old_saved_rows=1600,new_saved_rows=3200,new_statistical_intervals=0,independent_A3_pending=True))
        return result
    except BaseException as exc:
        dump(out/'FAILED.json',dict(utc=utc(),type=type(exc).__name__,error=str(exc),partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('spec','inputs','generation-oracle','scores','old-metadata','out'):
        p.add_argument('--'+name,required=True)
    execute(p.parse_args())
