"""Once-only new I/O; original native64 decoder and frozen P1 scorer unchanged."""
import argparse
from pathlib import Path
from scripts import p011_forced_answer_io as original
from experiments.p011.forced_answer_ext3b import SPEC, SCOPE, CELLS, LOCAL, STORE, REMOTE, admit, actual
from experiments.p011.owner_0205_common import create, read, sha, utc


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['upload','collect','audit','score'])
    p.add_argument('--review',required=True);p.add_argument('--cell',choices=CELLS);a=p.parse_args()
    spec=admit(SPEC,a.review,SCOPE)
    if a.mode in ('audit','score') and not a.cell:raise ValueError('Exact cell required')
    if a.mode=='upload':actual(spec)
    if a.mode=='collect':read(LOCAL/'cli/CLI_EXIT.json')
    original.CELLS,original.STORE,original.REMOTE=CELLS,STORE,REMOTE
    out=LOCAL/a.mode
    if a.cell:out=out/a.cell
    if a.mode=='score':
        from experiments.p011.forced_answer_score_process import supervise
        audit_dir=LOCAL/'audit'/a.cell;proof=read(audit_dir/'COMPLETE_PROOF.json')
        if sha(audit_dir/'SCORING_ROWS.json')!=proof['scoring_rows_sha256']:raise ValueError('New oracle differs')
        supervise(out,read(audit_dir/'SCORING_ROWS.json'),{'oracle_sha256':sha(audit_dir/'COMPLETE_PROOF.json'),
            'source_CR_sha256':sha(a.review),'spec_sha256':sha(SPEC)},7200)
        return
    out.mkdir(parents=True,exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'mode':a.mode,'cell':a.cell,'source_CR_sha256':sha(a.review),'automatic_retry':False})
    try:
        if a.mode=='upload':original.upload(spec,out)
        elif a.mode=='collect':original.collect(spec,out)
        else:original.audit(spec,out,a.cell)
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise

if __name__=='__main__':main()
