"""Claude independent N2 recompute from published T1/base packets (not from MEASUREMENTS)."""
import json, subprocess, math
C='8e1b3463'; R='reports/p008_20261013'
def J(f): return json.loads(subprocess.check_output(['git','show',f'{C}:{f}'],cwd='/home/claude/2P1R_Reasoning_Post'))
M=J(R+'/t8_actual_timing_proposal_v1/MEASUREMENTS.json'); PR=J(R+'/t8_actual_timing_proposal_v1/PROPOSAL.json')
dirs={r:f'{R}/student_t1_eight_v1/{r}' for r in ['d1_b1_p4_breadth_t1','d1_b1_p4_depth_t1','d1_b8_p0_breadth_t1','d1_b8_p0_depth_t1','d2_b1_p0_breadth_t1','d2_b1_p0_depth_t1','d2_b1_p4_breadth_t1','d2_b1_p4_depth_t1']}
for n in ['d1_b1_p0_breadth_t1','d1_b1_p0_depth_t1']: dirs[n]=f'{R}/student_t1_replacements_v1/{n}_replacement_r1'
def ledger_rec(d,kind):
    L=J(d+'/LEDGER.json'); return [v for k,v in L.items() if f'/{kind}/' in k and k.split('/')[-1] in (d.split('/')[-1],)][0]
mine={}; diffs=[]
for r,d in dirs.items():
    tm=J(d+'/TIMING_READ_METADATA.json')['files']
    upd=[J(f'{d}/completed/update_{i:04d}.json') for i in range(1,257)]
    times=[tm[f'completed/update_{i:04d}.json']['mtime'] for i in range(1,257)]
    costs=[u['seconds'] for u in upd]; toks=[u['processed_tokens'] for u in upd]
    bj=J(d+'/block_journal_metrics.json')
    phys=d.split('/')[-1]
    L=J(d+'/LEDGER.json'); claim=[v for k,v in L.items() if k.endswith('/claim/'+phys)][0]; term=[v for k,v in L.items() if k.endswith('/terminal/'+phys)][0]
    intent=J(d+'/result.json') ; 
    wall=term['finished_epoch']-claim['claimed_epoch']
    s=dict(times=times,costs=costs,toks=toks,first_eval=tm['intents/endpoint1319_batch_0000.json']['mtime'],bb=bj['block_boundary_seconds'],lw=bj['local_step_write_seconds'],wall=wall)
    m=M[r]
    chk={'times':s['times']==m['completed_update_mtimes'],'costs':s['costs']==m['optimizer_seconds'],'toks':s['toks']==m['processed_tokens'],
         'first_eval':s['first_eval']==m['first_eval_intent_mtime'],'bb':s['bb']==m['block_boundary_seconds'],'lw':s['lw']==m['local_step_write_seconds'],
         'wall_claim_vs_M':round(m['worker_seconds_through_terminal']-wall,3)}
    if not all(v is True for k,v in chk.items() if k!='wall_claim_vs_M'): diffs.append((r,chk))
    # my own component derivation (same frozen formula, own code)
    W=m['worker_seconds_through_terminal']  # use larger-start definition reported; compare below
    span=times[-1]-times[0]; F=W-span+2; non=max((span-sum(costs[1:])+2)/255,(s['bb']+s['lw'])/256)
    mine[r]=dict(F=F,c=sum(costs)/sum(toks),u=sum(costs)/256,m=non,gap=s['first_eval']-times[-1]+2,wallclaim=wall,W=W)
    print(r,chk)
base=M['base']['worker_seconds_through_terminal']
Lb=J(R+'/base_v1/LEDGER.json'); kb='midpoint/p008-students-completion-20261013-r1/'
print('base W',base,'claim->finish',Lb[kb+'terminal/base']['finished_epoch']-Lb[kb+'claim/base']['claimed_epoch'])
F=max(base,*(x['F'] for x in mine.values())); c=max(x['c'] for x in mine.values()); u=max(x['u'] for x in mine.values()); mm=max(x['m'] for x in mine.values()); K=2*max(x['gap'] for x in mine.values())
print('maxima mine',dict(F=F,c=c,u=u,m=mm,K=K)); print('maxima proposal',PR.get('maxima'))
argF=max(mine,key=lambda r:mine[r]['F']); argu=max(mine,key=lambda r:mine[r]['u']); print('argmax F',argF,'u',argu, 'm',max(mine,key=lambda r:mine[r]['m']),'gap',max(mine,key=lambda r:mine[r]['gap']))
for n,p in PR['predictions'].items():
    P=p['compute_token_seconds']/PR['maxima']['c']
    pt=F+max(P*c,2048*u)+2048*mm+K
    print(n, round(pt,3), round(1.2*pt,3), 'prop',round(p['with_margin_seconds'],3), 'pass' if 1.2*pt<=9530 else 'FAIL')
print('point without margin max', max(F+max(p['compute_token_seconds']/PR['maxima']['c']*c,2048*u)+2048*mm+K for p in PR['predictions'].values()))
