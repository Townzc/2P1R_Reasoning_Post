"""One reviewed read-only completeness diagnosis; never changes P011 inputs.

Original rules.complete is called for descriptive counts, not a new production
selection. No tokenizer, encoding, symbolic scoring, model, or source DB write.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import random
import signal
import sqlite3
import time

from experiments.p011 import data_contract as rules
from experiments.sft_allocation_midpoint.common import sha, dump

ROOT = Path('.local/p011_20261020/r1')
SOURCE = ROOT/'ot3_inputs_r1'
OUTPUT = ROOT/'ot3_completeness_diagnostic_r1'
FENCE = ROOT/'OT3_COMPLETENESS_DIAGNOSTIC_ATTEMPT.json'
SCOPE = 'p011-OT3-readonly-completeness-diagnostic-CR'
SOURCES = ('experiments/p011/__init__.py','experiments/p011/data_contract.py',
           'experiments/sft_allocation_midpoint/common.py',
           'scripts/diagnose_p011_ot3_completeness.py')
REQUEST_SHA = '4e8157658c1e521dae9a42323d25226859381dd0a283b7bd38c2a5606567e3a6'
OWNER_SHA = 'e47594cd3acb095750d9db4658f4c457f416b4ef77dd1f3ff1b69c4562198c67'
PRESERVATION_SHA = '662d42e2b68f207e0a2946a4d9b11d21df25784dd0b91a51f4f010c0c6c89849'
FLAGS = ('original_complete_function_called','readonly_immutable_database',
         'all_cardinality16_responses_included','original_length_unknown_retained',
         'no_tokenizer_selection_generation_or_scoring','deterministic_samples_and_quantiles_accepted',
         'reporting_threshold_semantics_accepted')


def utc():
    return datetime.now(timezone.utc).isoformat()


def describe(text):
    if type(text) is not str:raise ValueError('Literal original response required')
    t=text.count('</think>');boxed='\\boxed{' in text
    after=('\\boxed{' in text.rsplit('</think>',1)[1]) if t else None
    last='\\boxed{' in text[-2000:]
    complete=rules.complete(text)  # actual frozen function, never reimplemented
    category='complete'
    if not complete:
        if t==0 and not boxed:category='N1'
        elif t==0 and boxed and not last:category='N2'
        elif t>=1 and not after and '\\boxed{' in text.rsplit('</think>',1)[0]:category='N3'
        elif t>=1 and not boxed:category='N4'
        else:category='N5'
    return {'t':t,'starts_with_think':text.startswith('<think>'),
            'boxed_any':boxed,'boxed_after_last_think':after,'boxed_last2000':last,
            'complete':complete,'characters':len(text),'category':category,
            'Rprime_complete':after if t else boxed}


def quantiles(values):
    """Exact descriptive linear interpolation at (n-1)*p, no resampling."""
    values=sorted(values)
    if not values:return {str(p):None for p in (10,50,90,99)}
    result={}
    for p in (10,50,90,99):
        x=(len(values)-1)*p/100;lo=math.floor(x);hi=math.ceil(x)
        result[str(p)]=values[lo]+(values[hi]-values[lo])*(x-lo)
    return result


class Summary:
    def __init__(self):
        self.counts=Counter();self.t=Counter();self.hist=Counter();self.parents=0
        self.lengths={k:[] for k in ('complete','N1','N2','N3','N4','N5')}
        self.samples={k:[] for k in ('N1','N2','N3','N4','N5')}
        # Independent fixed reservoir per category; ordered source rows below.
        self.rng={k:random.Random(20261021) for k in self.samples}
        self.counterfactual=Counter()

    def row(self,path,text):
        d=describe(text);cat=d['category'];self.counts[cat]+=1
        self.counts['total']+=1;self.counts['starts_with_think']+=int(d['starts_with_think'])
        self.t[d['t']]+=1;self.lengths[cat].append(d['characters'])
        if cat!='complete':
            n=self.counts[cat];item={'path_id':path,'last400':text[-400:],**d}
            if len(self.samples[cat])<5:self.samples[cat].append(item)
            else:
                j=self.rng[cat].randrange(n)
                if j<5:self.samples[cat][j]=item
        return d

    def parent(self,rows,disposition):
        if len(rows)!=16:raise ValueError('Only complete cardinality16 parent inventory')
        old=sum(x['complete'] for x in rows);rp=all(x['Rprime_complete'] for x in rows)
        flags=disposition['flags'];leaked=flags['decontamination_hit'];length=flags['any_overlength']
        if (type(leaked) is not bool or length is not None and type(length) is not bool
                or flags['incomplete'] is not (old<16)
                or disposition['eligible'] is not (old==16 and not leaked and length is False)):
            raise ValueError('Original saved disposition and unchanged completeness disagree')
        self.parents+=1;self.hist[old]+=1
        if rp:
            self.counterfactual['all16_complete_before_length_decontamination']+=1
            if leaked:self.counterfactual['decontamination_excluded']+=1
            elif length is True:self.counterfactual['known_overlength_excluded']+=1
            elif length is False:self.counterfactual['known_length_pass_and_decontamination_pass']+=1
            else:self.counterfactual['length_unknown_and_decontamination_pass']+=1
        return {'original_complete_count':old,'Rprime_all16_complete':rp,
                'original_decontamination_hit':leaked,'original_any_overlength':length,
                'length_not_retokenized':True}

    def finish(self):
        total=self.counts['total'];bad=total-self.counts['complete'];cf=self.counterfactual
        all16=cf['all16_complete_before_length_decontamination']
        known=cf['known_length_pass_and_decontamination_pass'];possible=known+cf['length_unknown_and_decontamination_pass']
        n2=bad>0 and self.counts['N2']*10>=bad
        trigger=n2 or all16>=8076
        return {'parents':self.parents,'responses':total,'complete':self.counts['complete'],
          'incomplete':bad,'incomplete_categories':{k:self.counts[k] for k in self.samples},
          't_distribution':dict(sorted(self.t.items())),
          'starts_with_think_count':self.counts['starts_with_think'],
          'starts_with_think_fraction':self.counts['starts_with_think']/total if total else None,
          'character_length_quantiles':{k:quantiles(v) for k,v in self.lengths.items()},
          'quantile_method':'linear at (n-1)*p; characters, not tokens',
          'parent_original_complete_count_histogram':{str(i):self.hist[i] for i in range(17)},
          'Rprime_counts':dict(cf),'Rprime_known_eligible_count':known,
          'Rprime_possible_eligible_upper_count':possible,
          'Rprime_eligible_8076_threshold':'MET' if known>=8076 else ('NOT_MET' if possible<8076 else 'UNKNOWN_DUE_TO_UNMEASURED_LENGTH'),
          'request_reporting_threshold':{'N2_at_least_10percent_incomplete':n2,
            'Rprime_all16_complete_at_least_8076':all16>=8076,'report_owner_for_possible_rule_change':trigger,
            'raw_completeness_count_is_not_new_eligible_population':True,
            'decision_rule_change_or_reselection_authorized':False},
          'interpretation_limit':'Categories describe strings, not verified truncation causes or answer correctness. N3/N4 are request-defined format exclusions. No model effect inferred.',
          'sample_method':'Independent Random(20261021) reservoir5 per category over parent/source_file/row_index lexical order; fewer if category has fewer than5.',
          'samples':self.samples,'actual_A1_or_training_admitted':False}


def admitted(args):
    def read(p):return json.loads(Path(p).read_text())
    if sha(args.request)!=REQUEST_SHA or sha(args.owner_record)!=OWNER_SHA or sha(args.preservation)!=PRESERVATION_SHA:
        raise ValueError('Exact independent request/owner-report/original preservation required')
    binding={'source_files':{p:sha(p) for p in SOURCES},'request_sha256':REQUEST_SHA,
             'owner_reported_decision_sha256':OWNER_SHA,'preservation_sha256':PRESERVATION_SHA,
             'plan_sha256':rules.PLAN_SHA256,'expected_parents':53107,'expected_responses':849712,
             'local_hard_seconds':3600,'output':str(OUTPUT),'no_new_eligibility_selection':True}
    review=read(args.review)
    if (review.get('scope')!=SCOPE or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or len(review.get('target_commit',''))!=40
            or any(review.get(k)!=v for k,v in binding.items())
            or any(review.get(k) is not True for k in FLAGS)
            or sha(review['local_report_path'])!=review['report_sha256']):
        raise ValueError('Real exact short diagnostic CR required before original data read')
    return binding,read(args.preservation)


def diagnose(db,dispositions,out,check):
    """Read-only supplied connection. Actual driver uses immutable/query_only URI."""
    summary=Summary();seen=set()
    keys=db.execute("SELECT parent,COUNT(*) FROM rows WHERE dataset='ot3' GROUP BY parent ORDER BY parent").fetchall()
    with gzip.open(out/'RESPONSE_DIAGNOSTICS.jsonl.gz','xt',encoding='utf-8') as response_file, \
            (out/'PARENT_DIAGNOSTICS.jsonl').open('x') as parent_file:
        for key,n in keys:
            check()
            if n!=16:continue
            parent=rules.identity(key)
            if parent in seen or parent not in dispositions:raise ValueError('Parent disposition missing/duplicate')
            seen.add(parent);rows=[]
            for source,index,text in db.execute("SELECT source_file,row_index,response FROM rows WHERE dataset='ot3' AND parent=? ORDER BY source_file,row_index",(key,)):
                check();path=f'ot3:{source}:{index}';d=summary.row(path,text);rows.append(d)
                response_file.write(json.dumps({'parent_sha256':parent,'path_id':path,**d})+'\n')
            parent_file.write(json.dumps({'parent_sha256':parent,**summary.parent(rows,dispositions[parent])})+'\n')
    if seen!=set(dispositions):raise ValueError('Original complete exhausted parent inventory differs')
    return summary.finish()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('request','owner-record','preservation','review'):parser.add_argument('--'+n,required=True)
    args=parser.parse_args();binding,proof=admitted(args)
    if OUTPUT.exists() or FENCE.exists():raise ValueError('Diagnostic already attempted; retain, no retry')
    dump(FENCE,{'utc':utc(),**binding});OUTPUT.mkdir();started=time.monotonic();db=None
    def check():
        if time.monotonic()-started>=3600 or time.time()>=1792645200:
            raise TimeoutError('Original diagnostic local/full-P011 cutoff reached')
    def timeout(*_):raise TimeoutError('Original bounded diagnostic limit reached')
    previous=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,3600)
    try:
        dump(OUTPUT/'INTENT.json',{'utc':utc(),**binding,'partial_is_not_final':True})
        for name in ('RAW_INDEX.sqlite','PARENT_DISPOSITIONS.jsonl'):
            p=SOURCE/name;v=proof['files'][name]
            if p.is_symlink() or p.stat().st_size!=v['bytes'] or sha(p)!=v['sha256']:
                raise ValueError('Original preserved diagnostic input bytes changed')
        check();dispositions={}
        with (SOURCE/'PARENT_DISPOSITIONS.jsonl').open() as f:
            for line in f:
                d=json.loads(line);key=d['parent_sha256']
                if d['row_count']!=16 or key in dispositions:raise ValueError('Original disposition cardinality differs')
                dispositions[key]=d
        if len(dispositions)!=53107:raise ValueError('Full original exhausted inventory required')
        db=sqlite3.connect((SOURCE/'RAW_INDEX.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        db.execute('PRAGMA query_only=ON')
        if db.execute('PRAGMA query_only').fetchone()[0]!=1:raise ValueError('Read-only database required')
        result=diagnose(db,dispositions,OUTPUT,check)
        if result['parents']!=53107 or result['responses']!=849712:raise ValueError('Full diagnostic denominator differs')
        check();dump(OUTPUT/'SUMMARY.json',result)
        dump(OUTPUT/'COMPLETED.json',{'utc':utc(),'elapsed_seconds':time.monotonic()-started,
             'original_database_write':False,'selection_changed':False,'new_tokenization':False,
             'new_model_or_symbolic_calls':0,'result_review_pending':True})
        dump(OUTPUT/'MANIFEST.json',{p.name:{'sha256':sha(p),'bytes':p.stat().st_size}
             for p in sorted(OUTPUT.iterdir()) if p.is_file()})
    except BaseException as e:
        dump(OUTPUT/'FAILED.json',{'utc':utc(),'type':type(e).__name__,'message':str(e),'automatic_retry_allowed':False})
        raise
    finally:
        if db is not None:db.close()
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


if __name__=='__main__':main()
