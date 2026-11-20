import json,sys,re,glob
sys.path.insert(0,'/tmp/claude-0/s1r')
import experiments.learning_regime_p009.math_scoring as ms
gold={json.loads(l)['problem_id']:json.loads(l)['answer'] for l in open('/tmp/claude-0/s0a2/inputs/math500.jsonl')}
R={}
for run in ('s1_s17_n400','s1_s17_n3200'):
    B='/tmp/claude-0/fp/'+run+'/'
    o=json.load(open(B+'sc/LOCAL_ORACLE_AUDIT.json'))['question_correct']
    s={d['problem_id']:d for d in json.load(open(B+'orc/SCORING_ROWS.json'))}
    R[run]={p:(o[p],ms.last_box(s[p]['answer_segment']).get('answer'),s[p]['stop_reason']) for p in o}
def norm(x):
    if x is None: return None
    x=re.sub(r'\\text\{([^}]*)\}',r'\1',x); x=re.sub(r'\\(left|right|,|!|;|\$|dfrac)','',x).replace('dfrac','frac')
    x=re.sub(r'\^\\circ|\^\{\\circ\}|\\%|°','',x); return re.sub(r'[\s{}$]','',x)
n=0
for p in gold:
    a,b=R['s1_s17_n400'][p],R['s1_s17_n3200'][p]
    if a[0]!=b[0]:
        wrong=a if not a[0] else b; right=b if not a[0] else a
        sus = wrong[1] is not None and (norm(wrong[1])==norm(gold[p]) or norm(wrong[1])==norm(right[1]))
        if sus:
            n+=1; print('SUSPECT',p,'| gold',gold[p],'| wrong-run ans',wrong[1],wrong[2],'| right-run ans',right[1],'| wrong side', 'n400' if not a[0] else 'n3200')
print('suspect false-negative discordants',n)
c=sum(1 for p in gold if R['s1_s17_n400'][p][0]!=R['s1_s17_n3200'][p][0]); print('discordant',c)
print('only n3200 right',sum(1 for p in gold if R['s1_s17_n3200'][p][0] and not R['s1_s17_n400'][p][0]),'only n400 right',sum(1 for p in gold if R['s1_s17_n400'][p][0] and not R['s1_s17_n3200'][p][0]))
