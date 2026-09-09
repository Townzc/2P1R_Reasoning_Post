"""CPU gates for relation transport; independent solver inspects exposed text."""
from collections import Counter
from copy import deepcopy
import hashlib
import json

from src.relation_transport import render_prompt, render_certificate, views
from src.relation_verifier import parse_prompt, solve, simple_paths, check_certificate, orbit_key, adjacency
from src.sft_data import prefix


def sha_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def tokenize_exact(prompt, responses, tokenizer, max_length):
    """Batch full-text offsets; explicit EOS/prompt boundary checks, no truncation."""
    pre = prefix(prompt)
    prompt_ids = tokenizer(pre, add_special_tokens=False)['input_ids']
    full = tokenizer([pre+r for r in responses], add_special_tokens=False, return_offsets_mapping=True)
    receipts = []
    for response, ids, offsets in zip(responses, full['input_ids'], full['offset_mapping']):
        boundary = len(pre)
        if any(a < boundary < b for a,b in offsets):
            raise ValueError('Token crosses prompt/response boundary')
        supervised = [i for i,(a,b) in enumerate(offsets) if a >= boundary and b > a]
        if not supervised or supervised != list(range(len(prompt_ids),len(ids))):
            raise ValueError('Noncontiguous response mask')
        if ids[:len(prompt_ids)] != prompt_ids:
            raise ValueError('Training/inference prompt differs')
        if tokenizer.eos_token_id is None or tokenizer.eos_token_id in ids:
            raise ValueError('Missing or embedded EOS')
        if len(ids)+1 > max_length:
            raise ValueError('Sequence exceeds bound; truncation prohibited')
        receipts.append({'n_prompt':len(prompt_ids), 'n_supervised':len(supervised)+1,
                         'n_processed':len(ids)+1, 'response_sha256':sha_text(response),
                         'input_with_eos_sha256': sha_text(json.dumps(ids+[tokenizer.eos_token_id]))})
    return receipts


def independent_response(q, path):
    node, state = q['source'], q['state']
    lines = []
    for u,v,e in path:
        if u != node: raise ValueError('Invalid enumerated path')
        if u == e['u']: nxt = e['table'][state]
        else: nxt = next(a for a,b in enumerate(e['table']) if b == state)
        lines.append(f"E {e['id']} : N {u} = {state} > N {v} = {nxt}")
        state,node = nxt,v
    return '\n'.join(lines) + f'\nAnswer : {state}'


def audit_world(world, tokenizer, max_length, *, metamorphic=False):
    checks, failures = Counter(), []
    def require(condition, label):
        checks[label] += 1
        if not condition: failures.append(label)
    require(world['prompt'] == render_prompt(world['question']), 'prompt_matches_exposed_record')
    q = parse_prompt(world['prompt'])
    p = simple_paths(q)
    require(len(p)==4 and {len(x) for x in p}=={4}, 'four_equal_shortest_paths')
    internal = [{v for _,v,_ in path[:-1]} for path in p]
    require(all(not (a&b) for i,a in enumerate(internal) for b in internal[i+1:]), 'internally_disjoint')
    parsed_support = {tuple(e['id'] for _,_,e in path) for path in p}
    require(parsed_support == {tuple(x) for x in world['task_paths']}, 'stored_support_complete')
    require(len({e['id'] for path in p for _,_,e in path})==16, 'edge_disjoint')
    require(len(q['edges'])==32 and len(adjacency(q))==34, 'fixed_topology_size')
    clean_tokens = tokenize_exact(world['prompt'], world['responses'], tokenizer, max_length)
    require(len({(x['n_supervised'],x['n_processed']) for x in clean_tokens})==1, 'all_paths_equal_tokens')
    for response in world['responses']:
        require(check_certificate(world['prompt'], response)['valid'], 'all_gold_traces_valid')
    view_results = {}
    for name,(vq,expected) in views(world).items():
        prompt = render_prompt(vq); parsed = parse_prompt(prompt)
        ans, paths = solve(parsed), simple_paths(parsed)
        require(ans==[expected], name+'_unique_answer')
        require(len(paths)==(1 if name=='useful_delete' else 4), name+'_path_count')
        require({len(x) for x in paths}=={4}, name+'_path_length')
        for path in paths:
            response = independent_response(parsed,path)
            require(check_certificate(prompt,response)['valid'], name+'_independent_traces')
        response = independent_response(parsed,paths[0])
        tokens = tokenize_exact(prompt,[response],tokenizer,max_length)[0]
        view_results[name] = {'answer':expected,'n_paths':len(paths),'prompt_sha256':sha_text(prompt),**tokens}
        if name=='useful_delete':
            old = [check_certificate(prompt,r) for r in world['responses']]
            require(sum(x['valid'] for x in old)==1 and sum(x['reason']=='absent_edge' for x in old)==3,
                    'removed_gold_traces_rejected')
        if name in ('source_change','target_change'):
            require(expected!=world['answer'], name+'_changes_answer')
    require(view_results['useful_delete']['n_prompt']==view_results['irrelevant_delete']['n_prompt'],
            'deletion_view_token_equality')
    require(len(set(world['intervention']['useful_delete']))==3 and
            len(set(world['intervention']['irrelevant_delete']))==3,'exactly_three_deletions')
    # Negative fixtures use all four routes, not just the three treatment edits.
    bad = deepcopy(q); remove={path[1] for path in world['task_paths']}
    bad['edges']=[e for e in bad['edges'] if e['id'] not in remove]
    require(solve(parse_prompt(render_prompt(bad)))==[], 'disconnected_negative')
    bad=deepcopy(q); e=next(e for e in bad['edges'] if e['id']==world['task_paths'][0][-1])
    e['table']=[(x+1)%5 for x in e['table']]
    require(len(solve(parse_prompt(render_prompt(bad))))>1, 'inconsistent_negative')
    partial=deepcopy(q)
    partial['edges']=[e for e in partial['edges'] if q['source'] in (e['u'],e['v']) or q['target'] in (e['u'],e['v'])]
    require(solve(partial)==[], 'radius_one_disconnected')
    canonical=orbit_key(q)
    if metamorphic:
        transformed=deepcopy(q); g=(2,4,1,0,3)
        for e in transformed['edges']:
            e['u'],e['v']=233-e['v'],233-e['u']; e['id']=431-e['id']
            table=[0]*5
            for a,b in enumerate(e['table']):table[g[a]]=g[b]
            e['table']=[table.index(a) for a in range(5)]
        transformed['source'],transformed['target']=233-q['source'],233-q['target']
        transformed['state']=g[q['state']]; transformed['edges'].reverse()
        text=render_prompt(transformed); parsed=parse_prompt(text)
        require(solve(parsed)==[g[world['answer']]], 'metamorphic_answer')
        require(orbit_key(parsed)==canonical, 'metamorphic_orbit')
        require(orbit_key(views(world)['target_change'][0])==canonical, 'endpoint_family_grouped')
    positions={e['id']:i for i,e in enumerate(q['edges'])}
    return {'checks':dict(checks),'failures':failures,'tokens':clean_tokens,'views':view_results,
            'orbit':canonical,'deletion_positions':{
                name:[positions[e] for e in world['intervention'][name]]
                for name in ('useful_delete','irrelevant_delete')}}


def exposure_features(world, route):
    q=parse_prompt(world['prompt'])
    edge_ids=world['task_paths'][route]
    edges={e['id']:e for e in q['edges']}
    node,state=q['source'],q['state']
    states=Counter(); transitions=Counter(); tables=Counter(); neutral=0; identities=0
    for edge_id in edge_ids:
        e=edges[edge_id]
        if node!=e['u']: raise ValueError('Initial gold route must be forward')
        nxt=e['table'][state]
        states[str(nxt)]+=1; transitions[f'{state}>{nxt}']+=1
        tables[''.join(map(str,e['table']))]+=1
        neutral+=int(state==nxt); identities+=int(tuple(e['table'])==tuple(range(5)))
        node,state=e['v'],nxt
    return {'states':states,'transitions':transitions,'tables':tables,
            'neutral':neutral,'identity_tables':identities}


def audit_schedule(worlds, schedule):
    data={w['world_id']:w for w in worlds}
    counters={arm:{'states':Counter(),'transitions':Counter(),'tables':Counter(),
                   'neutral':0,'identity_tables':0,'supervised':0,'processed':0,'padding':0}
              for arm in ('multi','repeat')}
    exposure={arm:Counter() for arm in counters}; update_residuals=Counter(); failures=[]
    feature_cache={(w['world_id'],r):exposure_features(w,r) for w in worlds for r in range(4)}
    per_question={w['world_id']:{arm:Counter() for arm in counters} for w in worlds}
    for i,update in enumerate(schedule['updates']):
        stats={}
        for arm in counters:
            if sorted(update[arm])!=list(range(4)):failures.append(f'update_{i}_slots')
            c={'states':Counter(),'transitions':Counter(),'tables':Counter(),'neutral':0,'identity_tables':0}
            token_rows=[]
            for wid,r in zip(update['world_ids'],update[arm]):
                exposure[arm][(wid,r)]+=1
                f=feature_cache[(wid,r)]; token_rows.append(data[wid]['audit']['tokens'][r])
                for k in ('states','transitions','tables'):c[k].update(f[k])
                for k in ('neutral','identity_tables'):c[k]+=f[k];per_question[wid][arm][k]+=f[k]
            c['supervised']=sum(t['n_supervised'] for t in token_rows)
            c['processed']=sum(t['n_processed'] for t in token_rows)
            c['padding']=sum(max(t['n_processed'] for t in token_rows[j:j+2])*len(token_rows[j:j+2])-
                             sum(t['n_processed'] for t in token_rows[j:j+2]) for j in (0,2))
            stats[arm]=c
            for k,v in c.items():
                if isinstance(v,Counter):counters[arm][k].update(v)
                else:counters[arm][k]+=v
        for k in stats['multi']:
            if stats['multi'][k]!=stats['repeat'][k]:update_residuals[k]+=1
        if any(stats['multi'][k]!=stats['repeat'][k] for k in ('supervised','processed','padding')):
            failures.append(f'update_{i}_tokens')
    for wid in data:
        if [exposure['multi'][(wid,r)] for r in range(4)] != [1,1,1,1]: failures.append(wid+'_multi_dose')
        if sorted(exposure['repeat'][(wid,r)] for r in range(4)) != [0,0,0,4]: failures.append(wid+'_repeat_dose')
    return {'accounting_only_not_a_training_recipe':True,'worlds':len(data),
            'updates':len(schedule['updates']),'presentations_per_arm':4*len(data),
            'arms':counters,'updates_with_residual':dict(update_residuals),
            'questions_with_neutral_residual':sum(v['multi']['neutral']!=v['repeat']['neutral'] for v in per_question.values()),
            'failures':failures}
