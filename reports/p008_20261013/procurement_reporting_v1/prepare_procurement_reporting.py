"""Once-only reporting aggregates from previously audited saved score/event files.

No raw decoding/scoring, procurement replay, tokenizer, model or network.
"""
from pathlib import Path
import csv, datetime, hashlib, json, shutil
from experiments.sft_allocation_midpoint.common import read, dump, sha, manifest
from scripts.p008_procurement_reporting import wallet_row, overlap_row, render_appendix

r = Path(__file__).resolve().parent
out = r/'procurement_reporting_r1'
assert not out.exists(), 'Existing reporting attempt; preserve and reconcile'
out.mkdir(exist_ok=False)
dump(out/'READ_INTENT.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
     scope='Saved scored-field/payment aggregation only; no raw oracle, model or remote reads'))
pub = Path('reports/p008_20261013')
packets = {'pool_d1_v1':'7973161bb3d46dd02a8db088ef11274fdf4d8654',
           'pool_d2_reconciliation_v1':'19bdf37b65e879776f37bbdbb692f5ea0c63dbb5',
           'pool_d2_merged_v1':'eb398fb1fec5306ab654ffec19e7b96e2005fdad'}
indices = {name:read(pub/name/'MANIFEST.json') for name in packets}
sources = {}
def saved(name, relative):
    path=pub/name/relative
    payload=path.read_bytes(); record=indices[name][relative]
    assert len(payload)==record['bytes'] and hashlib.sha256(payload).hexdigest()==record['sha256']
    sources[str(path)]=record
    return json.loads(payload)

wallets=[]; physical=[]; sets=[]
for draw in (1,2):
    name='pool_d1_v1' if draw==1 else 'pool_d2_merged_v1'
    summary=saved(name,'SUMMARY.json'); oracle=saved(name,'LOCAL_ORACLE_AUDIT.json')
    assert oracle['passed'] and oracle['all_raw_redecoded'] and oracle['all_wallets_replayed']
    order=saved(name,'frozen_wallets.json')['parent_order']
    assert len(order)==len(set(order))==6973
    sets.append(set(order))
    candidates={}
    folders=[('pool_d1_v1','physical_batches')] if draw==1 else [
        ('pool_d2_reconciliation_v1','physical_batches'),('pool_d2_merged_v1','child_physical_batches')]
    folder_counts=[]
    for source_name,folder in folders:
        count=0
        for path in sorted((pub/source_name/folder).glob('*_scored.json')):
            rows=saved(source_name,str(path.relative_to(pub/source_name)))
            for row in rows:
                cid=row['candidate_id']; assert cid not in candidates
                candidates[cid]={k:row[k] for k in ('candidate_id','problem_id','prompt_tokens',
                    'completion_tokens','usable','duplicate_of','usable_duplicate_of')}
                candidates[cid].update(clean_correct=row['score']['clean_correct'],truncated=row['stop']['truncated'])
            count+=len(rows)
        folder_counts.append(count)
    assert folder_counts==([7420] if draw==1 else [3992,3424])
    p=dict(draw=draw,physical_outputs=len(candidates),
           prompt_tokens=sum(x['prompt_tokens'] for x in candidates.values()),
           returned_tokens=sum(x['completion_tokens'] for x in candidates.values()))
    assert p['physical_outputs']==summary['physical_outputs']==oracle['physical_outputs']
    assert p['returned_tokens']==summary['physical_returned_tokens']==oracle['returned_tokens']
    if draw==2:p.update(parent_outputs=folder_counts[0],child_outputs=folder_counts[1])
    physical.append(p)
    wallet_folder='wallets' if draw==1 else 'complete_wallets'
    assert len(summary['wallets'])==8
    for key in sorted(summary['wallets']):
        s=saved(name,f'{wallet_folder}/{key}_summary.json')
        assert s==summary['wallets'][key]==oracle['wallets'][key]
        e=saved(name,f'{wallet_folder}/{key}_events.json')
        wallets.append(wallet_row(s,e,candidates))
assert sets[0]==sets[1]
lookup={x['wallet']:x for x in wallets}
overlaps=[overlap_row(lookup[f'd1_b8_p{price}_{policy}'],lookup[f'd2_b8_p{price}_{policy}'],field)
          for price in (0,4) for policy in ('breadth','depth')
          for field in ('purchased_problem_ids','usable_problem_ids')]
data=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wallets=wallets,
          high_budget_overlap=overlaps,physical_draws=physical,eligible_problem_count=6973,
          external_review='pending',score_rule_unchanged=True,new_raw_oracle_calls=0,new_model_calls=0,
          new_remote_calls=0,source_packets=packets,source_files=sources,
          source_manifest_sha256={name:sha(pub/name/'MANIFEST.json') for name in packets},
          limitations=['Saved primary labels aggregated; no new reasoning or parser validation',
                       'Virtual charges are hypothetical units, not actual platform dollars',
                       'Billing snapshot delayed; final complete-run cost remains pending'])
dump(out/'ACCOUNTING.json',data)
billing=pub/'BILLING_UPDATE_1824.json'
shutil.copyfile(billing,out/'BILLING_SNAPSHOT.json')
(out/'ACCOUNTING.md').write_text(render_appendix(data,read(billing)))
fields=[k for k,v in wallets[0].items() if not isinstance(v,list)]
with (out/'WALLETS.csv').open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    w.writerows({k:json.dumps(row[k],sort_keys=True) if isinstance(row[k],dict) else row[k] for k in fields} for row in wallets)
with (out/'HIGH_B_OVERLAP.csv').open('x',newline='') as f:
    fields=[k for k in overlaps[0] if k!='shared_problem_ids']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:row[k] for k in fields} for row in overlaps)
shutil.copyfile(__file__,out/'prepare_procurement_reporting.py')
shutil.copyfile('scripts/p008_procurement_reporting.py',out/'p008_procurement_reporting.py')
dump(out/'MANIFEST.json',manifest(out))
print(json.dumps(dict(out=str(out),wallets=len(wallets),overlap_rows=len(overlaps),
     physical_outputs=sum(x['physical_outputs'] for x in physical),
     pool_exhausted=sum(x['pool_exhausted'] for x in wallets),
     unused_percent_min=min(x['unused_percent'] for x in wallets),
     unused_percent_max=max(x['unused_percent'] for x in wallets),
     external_review='pending',new_model_calls=0,new_raw_oracle_calls=0)))
