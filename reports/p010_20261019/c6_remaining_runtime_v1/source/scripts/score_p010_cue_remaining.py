"""Original frozen C6 scoring, bound to the real split failed/new lineage."""
import argparse,json
from experiments.p010.common import read,sha
from scripts.score_p010_cue_benchmark import score


def execute(a):
    from pathlib import Path
    root=Path(a.oracle);proof=read(root/'COMPLETED.json');spec=read(a.spec)
    if ((root/'FAILED.json').exists() or proof.get('passed') is not True
            or proof.get('original_parent_status')!='failed' or proof.get('outputs_from_failed_parent')!=18871
            or proof.get('outputs_from_new_remaining_call')!=2500 or proof['spec_sha256']!=sha(a.spec)
            or proof['original_failure_manifest_sha256']!=spec['failed_parent_manifest_sha256']
            or proof['original_preserved_ledger_sha256']!=spec['failed_parent_ledger_sha256']
            or proof['source_files']!=spec['source_files'] or proof['verification_source_files']!=spec['verification_source_files']
            or proof['new_symbolic_scoring']!=0 or proof['old_binary_loads']!=0):
        raise ValueError('Complete real failed-prefix plus new remaining raw proof required')
    return score(a)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('spec','oracle','inputs','run','out'):p.add_argument('--'+n,required=True)
    print(json.dumps(execute(p.parse_args())))
