import json,sys,collections,re,random
S=sys.argv[1];out=sys.argv[2]
rows=json.load(open(S+'/audit/SCORING_ROWS.json'));sc=json.load(open(S+'/score/owned_score/payload/ALL_SCORED_ROWS.json'))
assert [r['id'] for r in rows]==[x['id'] for x in sc]
def last_box(t):
    i=max(t.rfind('\\boxed{'),-1)
    if i<0:
        j=t.rfind('\\boxed ');return None if j<0 else t[j+7:].split('$')[0].strip()
    k=i+7;d=1;s=k
    while k<len(t) and d:
        d+= (t[k]=='{')-(t[k]=='}');k+=1
    return t[s:k-1] if d==0 else None
def norm(s):
    s=re.sub(r'\\left|\\right|\\!|\\,|\;|\\:|\s','',s);s=s.replace('dfrac','frac').replace('tfrac','frac').replace('^\\circ','').replace('^{\\circ}','').replace('$','')
    s=re.sub(r'\\text\{(.*?)\}',r'\1',s);return s.rstrip('.')
c=collections.Counter();flag=[];pairs_seen={}
for r,x in zip(rows,sc):
    s=x['score'];sr=r['stop_reason'];correct=s['correct']
    if sr!='native_eos':
        c['nonnative']+=1
        if correct: flag.append((r['id'],'nonnative correct'))
        if s.get('teacher_label_eligible'): flag.append((r['id'],'nonnative eligible'))
        continue
    mine=last_box(r['answer_segment'])
    if mine is None:
        c['no_box_mine']+=1
        if s.get('box_extracted') and correct: c['box_disagree_correct']+=1;flag.append((r['id'],'mine nobox, saved correct'))
        continue
    if s.get('extracted_answer') is not None and s['extracted_answer'].strip()!=mine.strip(): c['extract_diff']+=1;flag.append((r['id'],'extract',s['extracted_answer'][:60],mine[:60]))
    eq=norm(mine)==norm(r['gold'])
    if eq and not correct: c['string_eq_but_wrong']+=1;flag.append((r['id'],'streq wrong',mine,r['gold']))
    elif eq: c['string_eq_correct']+=1
    elif correct: c['symbolic_only_correct']+=1;pairs_seen.setdefault((mine,r['gold']),0);pairs_seen[(mine,r['gold'])]+=1
    else: c['incorrect_nonequal']+=1
    if correct!=bool(s.get('symbolic',{}).get('equivalent') or s.get('normalized_string_equal')): flag.append((r['id'],'verdict inconsistent'))
c['correct_total']=sum(x['score']['correct'] for x in sc)
random.seed(20261021);sample=random.sample(sorted(pairs_seen),min(40,len(pairs_seen)))
json.dump(dict(counts=c,flags=flag[:80],n_flags=len(flag),symbolic_only_pairs=len(pairs_seen),sample=sample),open(out,'w'),indent=1)
print(dict(c),len(flag),flag[:8]);print(len(pairs_seen))
for p in sample: print(repr(p[0])[:70],' || ',repr(p[1])[:70])
