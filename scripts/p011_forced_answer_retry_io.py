"""Original collect/oracle/scorer, new local/store identity, no upload operation."""
import argparse
from pathlib import Path
import scripts.p011_forced_answer_io as original
from experiments.p011.forced_answer import CELLS
from experiments.p011.forced_answer_relaunch import SPEC, SCOPE, STORE, REMOTE, admit
from experiments.p011.owner_0205_common import create, read, sha, utc


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['collect', 'audit', 'score'])
    p.add_argument('--review', required=True)
    p.add_argument('--cell', choices=CELLS)
    a = p.parse_args()
    spec = admit(SPEC, a.review, SCOPE)
    if a.mode in ('audit', 'score') and not a.cell:
        raise ValueError('Exact complete cell required')
    root = Path(spec['local_root'])
    if a.mode == 'collect':
        read(root/'cli/CLI_EXIT.json')
    original.STORE, original.REMOTE = STORE, REMOTE
    out = root/a.mode
    if a.cell:
        out = out/a.cell
    if a.mode == 'score':
        from experiments.p011.forced_answer_score_process import supervise
        audit = root/'audit'/a.cell
        proof = read(audit/'COMPLETE_PROOF.json')
        if sha(audit/'SCORING_ROWS.json') != proof['scoring_rows_sha256']:
            raise ValueError('Original v3 native64 oracle rows changed')
        supervise(out, read(audit/'SCORING_ROWS.json'),
                  {'oracle_sha256':sha(audit/'COMPLETE_PROOF.json'),
                   'source_CR_sha256':sha(a.review), 'spec_sha256':sha(SPEC)}, 7200)
        return
    out.mkdir(parents=True, exist_ok=False)
    create(out/'ATTEMPT.json', {'utc':utc(), 'mode':a.mode, 'cell':a.cell,
           'relaunch_CR_sha256':sha(a.review), 'original_upload_not_repeated':True,
           'automatic_retry':False})
    try:
        if a.mode == 'collect':
            original.collect(spec, out)
        else:
            original.audit(spec, out, a.cell)
    except BaseException as exc:
        create(out/'FAILED.json', {'utc':utc(), 'type':type(exc).__name__,
               'message':str(exc), 'automatic_retry':False})
        raise


if __name__ == '__main__':
    main()
