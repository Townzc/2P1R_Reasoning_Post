import json, re, hashlib, sys, random
sys.path.insert(0, '/home/claude/2p1r_reasoning_post')
from experiments.p012.vendor.li_math import is_equiv, last_boxed_only_string, remove_boxed
from math_verify import parse, verify, LatexExtractionConfig

def sha(p):
    h=hashlib.sha256(); h.update(open(p,'rb').read()); return h.hexdigest()

def my_last_boxed(t):
    i=max(t.rfind('\\boxed'), t.rfind('\\fbox'))
    if i<0: return None
    j=t.find('{',i)
    if j<0: return None
    d=0
    for k in range(j,len(t)):
        if t[k]=='{': d+=1
        elif t[k]=='}':
            d-=1
            if d==0: return t[j+1:k]
    return None

def mv(a,g):
    try:
        kw=dict(extraction_config=[LatexExtractionConfig()], fallback_mode='no_fallback')
        pa=parse('$'+a+'$',**kw); pg=parse('$'+g+'$',**kw)
        return bool(pa and pg and verify(pg,pa))
    except Exception: return False

def gsm_flex(t):
    m=re.findall(r"(-?[$0-9.,]{2,})|(-?[0-9]+)", t)
    if not m: return None
    return next((x for x in m[-1] if x), None)
def gsm_clean(v):
    for p in (",", r"\$", r"(?s).*#### ", r"\.$"): v=re.sub(p,"",v)
    return v.lower()

def audit(name, gen, score, inputs, task):
    comp=json.load(open(f'{gen}/GENERATION_COMPLETE.json')); man=json.load(open(f'{gen}/MANIFEST.json'))
    assert sha(f'{gen}/raw.jsonl')==comp['raw_sha256'], 'raw sha'
    assert sha(inputs)==man['input_sha256'], 'input sha'
    rows={json.loads(l)['id']:json.loads(l) for l in open(inputs)}
    raw=[json.loads(l) for l in open(f'{gen}/raw.jsonl')]
    labels={(l['id'],l['draw']):l for l in map(json.loads, open(f'{score}/labels.jsonl'))}
    assert len(raw)==len(rows)==len(labels), (len(raw),len(rows),len(labels))
    cfg=man['config']
    n=len(raw); exact=0; mism=0; mvc=0; cap=0; term=0; sstop=0; noext=0; capped_correct_mv=0
    lens=[]
    for r in raw:
        g=rows[r['id']]['gold']; lab=labels[(r['id'],r['draw'])]
        lens.append(len(r['token_ids']))
        cap+=r['finish_reason']=='length'; term+=bool(r['stopped_on_terminator']); sstop+=bool(r['string_stop'])
        if task=='math':
            a=my_last_boxed(r['text'])
            lb=last_boxed_only_string(r['text']); a_li=remove_boxed(lb) if lb is not None else None
            c=a_li is not None and is_equiv(a_li,g)
            if c!=lab['correct'] or a_li!=lab['answer']: mism+=1
            exact+=c
            if a is None: noext+=1
            ok= a is not None and (mv(a,g) or c)
            mvc+=ok
            if ok and r['finish_reason']=='length': capped_correct_mv+=1
        else:
            a=gsm_flex(r['text']); c=a is not None and gsm_clean(a)==gsm_clean(g)
            if c!=lab['correct'] or a!=lab['answer']: mism+=1
            exact+=c
            # stricter independent view: last number in text equals gold number
            gnum=g.split('####')[-1].strip().replace(',','')
            nums=re.findall(r'-?\d[\d,]*\.?\d*', r['text'])
            last=nums[-1].replace(',','').rstrip('.') if nums else None
            try: ok= last is not None and abs(float(last)-float(gnum))<1e-6
            except: ok=False
            mvc+=ok
    lens.sort()
    print(f"{name}: n={n} exact={exact} ({100*exact/n:.2f}%) label_mismatch={mism} | independent={mvc} ({100*mvc/n:.2f}%) | term={term} cap={cap} strstop={sstop} noext={noext} cap&correct={capped_correct_mv} | tok median={lens[n//2]} mean={sum(lens)/n:.0f} | proto={cfg['protocol']} T={cfg['temperature']} max={cfg['max_tokens']} model={cfg['model']}@{cfg['revision'][:8]} stops={cfg['stop_strings']}")
    return raw, rows, labels

A=audit('qwen-I math500','g0_qwen_instruct_v1_math500_raw_and_score/generation/generation','g0_qwen_instruct_v1_math500_raw_and_score/score','g0_qwen_instruct_v1_math500_raw_and_score/generation/inputs.jsonl','math')
B=audit('qwen-I gsm8k','g0_qwen_instruct_v1_gsm8k_raw_and_score/generation/generation','g0_qwen_instruct_v1_gsm8k_raw_and_score/score','g0_qwen_instruct_v1_gsm8k_raw_and_score/generation/inputs.jsonl','gsm')
C=audit('uw-short math500','g0_uw_short_v1_math500_raw/generation','g0_uw_short_v1_math500_scores','g0_uw_short_v1_math500_raw/inputs.jsonl','math')
D=audit('uw-short gsm8k','g0_uw_short_v1_gsm8k_raw/generation','g0_uw_short_v1_gsm8k_scores','g0_uw_short_v1_gsm8k_raw/inputs.jsonl','gsm')
E=audit('uw-long math500','g0_uw_long_math_v1_math500_raw/generation','g0_uw_long_math_v1_math500_scores','g0_uw_long_math_v1_math500_raw/inputs.jsonl','math')
import pickle; pickle.dump((A,B,C,D,E), open('/tmp/g0/aud.pkl','wb'))
