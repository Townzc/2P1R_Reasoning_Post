"""Independent A1 of P011 C1 actual inputs (Claude). Usage: python3 -I a1_c1.py X BINDING OUT"""
import sys, json, hashlib, collections, os
X, BIND, OUT = sys.argv[1:4]
shaf = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
dig = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
R = {}
man = json.load(open(f'{X}/MANIFEST.json'))
R['manifest_members'] = len(man)
R['manifest_bad'] = [n for n, v in man.items() if shaf(f'{X}/{n}') != v['sha256'] or os.path.getsize(f'{X}/{n}') != v['bytes']]
binding = json.load(open(BIND)); R['binding_sha'] = shaf(BIND)
R['binding_equals_copied'] = json.load(open(f'{X}/ORIGINAL_GROUP_BINDING.json')) == binding
# exact original-byte reuse: each copied file sha/bytes == binding's original file record
reuse_bad = []
for g, b in binding.items():
    for kind, old in b['filenames'].items():
        p = f'{X}/{g}/{kind}.json'
        if {'sha256': shaf(p), 'bytes': os.path.getsize(p)} != b['files'][old]: reuse_bad.append(p)
R['copied_vs_original_bad'] = reuse_bad
groups = {g: {k: json.load(open(f'{X}/{g}/{k}.json')) for k in ('config', 'rows', 'encoded')} for g in binding}
EOS = 151643
uniq = {}; mem = {}; bad = collections.Counter(); per = {}
for g in sorted(groups):
    G = groups[g]; c, rows, enc = G['config'], G['rows'], G['encoded']; teacher, n = g.split('_n'); n = int(n)
    per[g] = dict(n=len(rows), cfg_n=c['n'], seed=c['seed'], updates=c['updates'], targets=c['targets'], model=c['model'],
                  enc_sha_ok=c['encoded_rows_sha256'] == dig(enc), rows_sha_ok=c['training_rows_sha256'] == dig(rows),
                  unique_problems=len({r['problem_id'] for r in rows}),
                  fallback=sum(bool(r.get('unverified_fallback')) for r in rows),
                  attempts=dict(collections.Counter(r.get('attempt') for r in rows)),
                  teachers=dict(collections.Counter(r.get('teacher') for r in rows)))
    ms = []
    for r, e in zip(rows, enc):
        ids, lab = e['input_ids'], e['labels']; P = e['n_prompt']
        ok = (len(ids) == len(lab) == e['n_processed'] <= 2048 and 1 <= P < len(ids) and e['n_supervised'] == len(ids) - P
              and lab[:P] == [-100] * P and lab[P:] == ids[P:] and ids[-1] == EOS and ids[P:].count(EOS) == 1
              and all(type(x) is int and 0 <= x < 151936 for x in ids) and r['path_id'] == e['path_id'] and r['problem_id'] == e['problem_id'])
        bad[g] += not ok
        k = dig({'input_ids': ids, 'labels': lab})
        t = {'input_ids': ids, 'labels': lab, 'sequence_sha256': k, 'target_positions': list(range(P, len(ids))), 'supervised_tokens': len(ids) - P}
        if k in uniq and uniq[k] != t: bad['collision'] += 1
        uniq.setdefault(k, t)
        fb = False if teacher == 't15' else r['unverified_fallback']
        ms.append({'path_id': r['path_id'], 'problem_id': r['problem_id'], 'sequence_sha256': k, 'unverified_fallback': fb,
                   'original_row_sha256': dig(r), 'original_encoded_row_sha256': dig(e)})
    mem[g] = ms
R['groups'] = per; R['structure_bad'] = dict(bad)
R['nested_prefix'] = {t: mem[t + '_n3200'][:400] == mem[t + '_n400'] for t in ('t15', 't7', 't72')}
R['same_problem_set_and_order'] = [m['problem_id'] for m in mem['t7_n3200']] == [m['problem_id'] for m in mem['t72_n3200']], \
    set(m['problem_id'] for m in mem['t15_n3200']) == set(m['problem_id'] for m in mem['t7_n3200'])
R['t15_vs_t7_order_equal'] = [m['problem_id'] for m in mem['t15_n3200']] == [m['problem_id'] for m in mem['t7_n3200']]
# duplicates across teachers
owners = collections.defaultdict(set)
for g in ('t15_n3200', 't7_n3200', 't72_n3200'):
    for m in mem[g]: owners[m['sequence_sha256']].add(g.split('_')[0])
R['cross_teacher_shared_sequences'] = dict(collections.Counter('+'.join(sorted(v)) for v in owners.values() if len(v) > 1))
inv = dict(unique_sequences=len(uniq), members_per_group={k: len(v) for k, v in mem.items()},
           unique_input_tokens=sum(len(x['input_ids']) for x in uniq.values()),
           unique_supervised_tokens=sum(x['supervised_tokens'] for x in uniq.values()),
           max_sequence_length=max(len(x['input_ids']) for x in uniq.values()),
           tasks_sha256=dig(uniq), memberships_sha256=dig(mem), journal_chunks=(len(uniq) + 31) // 32)
R['inventory_recomputed'] = inv
saved = json.load(open(f'{X}/TASK_INVENTORY.json'))
R['inventory_matches_saved'] = {k: saved[k] == v for k, v in inv.items()}
# fallback overlap and selection details
R['fallback_overlap_t7_t72'] = len({m['problem_id'] for m in mem['t7_n3200'] if m['unverified_fallback']} & {m['problem_id'] for m in mem['t72_n3200'] if m['unverified_fallback']})
R['supervised_tokens_per_group'] = {g: sum(uniq[m['sequence_sha256']]['supervised_tokens'] for m in v) for g, v in mem.items()}
R['prompt_prefix_same_across_teachers'] = sum(
    uniq[a['sequence_sha256']]['input_ids'][:len(uniq[a['sequence_sha256']]['input_ids']) - uniq[a['sequence_sha256']]['supervised_tokens']] ==
    uniq[b['sequence_sha256']]['input_ids'][:len(uniq[b['sequence_sha256']]['input_ids']) - uniq[b['sequence_sha256']]['supervised_tokens']]
    for a, b in zip(mem['t7_n3200'], mem['t72_n3200']))
json.dump(R, open(OUT, 'w'), indent=1); print(json.dumps(R, indent=1))
