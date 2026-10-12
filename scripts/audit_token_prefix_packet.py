"""Read-only reproducible prefix audit; never calls a teacher or a student."""
import argparse
from pathlib import Path
from fractions import Fraction
from experiments.sft_allocation_midpoint.common import read,verify
from experiments.sft_allocation_acquisition.policy_contract import Policy


def audit(root):
    root=Path(root);verify(root,read(root/'manifest.json')['files'])
    meta=read(root/'prefix_simulation.json');out={}
    # Independent arithmetic/loop, with the common finite policy state machine.
    for cell,expected in meta['cells'].items():
        policy=Policy(meta['parent_ids'],1 if cell.startswith('breadth') else 4)
        price=Fraction(191151,128) if cell.endswith('p4') else Fraction(0)
        spent=Fraction(0);accepted=[];batches=0;settlements=[]
        for rows in read(root/(cell+'_trace.json')):
            proposal=policy.propose()
            prompt=sum(meta['prompt_lengths'][x['problem_id']] for x in proposal['items'])
            reserve=price*len(proposal['new_problem_ids'])+prompt+16*1024
            if spent+reserve>211257:break
            assert len(proposal['items'])==len(rows)==16
            assert proposal['items']==[dict(problem_id=x['problem_id'],attempt=x['attempt']) for x in rows]
            assert all(type(x['usable']) is bool and type(x['stop']['token_count']) is int and 0<=x['stop']['token_count']<=1024 for x in rows)
            assert all(x['prompt_tokens']==meta['prompt_lengths'][x['problem_id']] for x in rows)
            cost=price*len(proposal['new_problem_ids'])+sum(x['prompt_tokens']+x['stop']['token_count'] for x in rows)
            assert cost<=reserve;spent+=cost
            key=f'batch_{batches:04d}';policy.begin(key,proposal);policy.complete(key,rows)
            settlements.append(dict(batch=key,reserved_units=float(reserve),charged_units=float(cost),cumulative_units=float(spent),new_problem_ids=proposal['new_problem_ids']))
            accepted+=rows;batches+=1
        assert float(spent)==expected['charge'] and policy.cursor==expected['acquired']
        assert batches==expected['batches'] and settlements==expected['settlements']
        assert [x['candidate_id'] for x in accepted]==expected['accepted_candidates']
        assert sum(x['usable'] for x in accepted)==expected['usable']
        assert len({x['problem_id'] for x in accepted if x['usable']})==expected['covered']
        assert len(accepted)==expected['attempts'] and meta['parent_ids'][:policy.cursor]==expected['acquired_ids']
        out[cell]=dict(attempts=len(accepted),usable=expected['usable'],covered=expected['covered'],charge=float(spent))
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args()
    print(__import__('json').dumps(audit(a.root),indent=2))
