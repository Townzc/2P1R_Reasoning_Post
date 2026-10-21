"""Prepared common-support C2 inputs, reusing every located original encoding.

No entry/admission. The future complete C2 driver must bind fixed original
raw/encoded files, saved verdicts, full source review and result proofs before
calling this constructor. It creates new plans, never old model/scorer outputs.
"""
from pathlib import Path
import hashlib
from experiments.p010.common import digest, dump, manifest
from experiments.p010.multi_answer_plan import make_plan
from experiments.learning_regime_p009.training_plan import UPDATES, TARGETS, LR_VECTOR_SHA256
from experiments.learning_regime_p009.stage0_generation_contract_v2 import MODELS
from experiments.p011.short_generation import c2_prefix
from experiments.p011.c2_student_training import checked_recipe
from src.sft_data import encode_row


def encoding_key(row):
    return digest({k: row[k] for k in ('problem_id', 'path_id', 'prompt', 'response')})


def checked_encoding(row, encoded):
    ids=encoded['input_ids'];labels=encoded['labels'];n=encoded['n_prompt']
    if (encoded['problem_id']!=row['problem_id'] or encoded['path_id']!=row['path_id']
            or encoded['response_hash']!=hashlib.sha256(row['response'].encode()).hexdigest()
            or not 0<n<len(ids)<=2048 or len(ids)!=len(labels)
            or ids[-1]!=151643 or labels[-1]!=151643 or 151643 in ids[:-1]
            or any(type(x) is not int or not 0<=x<151936 for x in ids)
            or labels[:n]!=[-100]*n or labels[n:]!=ids[n:]
            or encoded['n_processed']!=len(ids)
            or encoded['n_supervised']!=sum(x!=-100 for x in labels[1:])):
        raise ValueError('Original whole-answer encoding/raw identity differs')
    return encoded


def original_catalog(pairs):
    """Metadata/byte-structure matching only, no tokenizer or original plan run."""
    catalog={};sources={}
    for label,rows,encoded in pairs:
        if len(rows)!=len(encoded) or not label:raise ValueError('Original paired rows required')
        for row,item in zip(rows,encoded):
            checked_encoding(row,item);key=encoding_key(row)
            if key in catalog and catalog[key]!=item:
                raise ValueError('Conflicting confirmed original encoding; no overwrite')
            catalog[key]=item;sources.setdefault(key,[]).append(label)
    return catalog,sources


def selected_rows(ordered,t72,t15,s1_ids,source):
    selection=c2_prefix(ordered,t72,t15,set(s1_ids))
    if selection.get('complete') is not True or len(selection['selected'])!=400:
        raise ValueError('First400 complete common-support parents required')
    rows={}
    for run,teacher,records in (('C2a','t15',t15),('C2b','t72',t72)):
        chosen=[]
        for parent in selection['selected']:
            pid=parent['problem_id'];cid=parent[teacher];rec=records[cid]
            if rec['problem_id']!=pid or rec['usable'] is not True or not 1<=rec['attempt']<=4:
                raise ValueError('Actual first usable saved verdict required')
            chosen.append({'problem_id':pid,'path_id':cid,'prompt':source[pid]['problem'],
                'response':rec['answer_text'],'teacher':teacher,'temperature':.8,
                'attempt':rec['attempt'],'saved_record_sha256':digest(rec),
                'unverified_fallback':False})
        rows[run]=chosen
    return selection,rows


def construct(out,rows,selection,catalog,sources,tokenizer,binding,check,
              encoder=encode_row,planner=make_plan):
    """Create once after the complete outer driver's permanent attempt fence."""
    out=Path(out);check()
    if (out.exists() or tokenizer.eos_token_id!=151643
            or set(rows)!=set(('C2a','C2b')) or selection.get('complete') is not True
            or binding.get('complete_original_and_new_saved_verdicts') is not True
            or binding.get('selection_sha256')!=digest(selection)
            or not binding.get('original_encoded_pair_files')
            or set(catalog)!=set(sources)):
        raise ValueError('Exact common-support selection/confirmed encoding provenance required')
    expected=[p['problem_id'] for p in selection['selected']]
    if len(expected)!=400 or len(set(expected))!=400:
        raise ValueError('Exact common400 order required')
    for run,chosen in rows.items():
        teacher='t15' if run=='C2a' else 't72'
        if (len(chosen)!=400 or [x['problem_id'] for x in chosen]!=expected
                or [x['path_id'] for x in chosen]!=[x[teacher] for x in selection['selected']]
                or any(x['unverified_fallback'] is not False or x['teacher']!=teacher for x in chosen)):
            raise ValueError('Same complete first-common support and teacher identity required')
    out.mkdir();confirmed={};proof={};new_count=0
    try:
        dump(out/'SELECTION.json',selection);dump(out/'INPUT_BINDING.json',binding)
        for chosen in rows.values():
            for row in chosen:
                check();key=encoding_key(row)
                if key in confirmed:continue
                if key in catalog:
                    item=checked_encoding(row,catalog[key]);origin='original_encoded_bytes'
                    locations=sources[key]
                else:
                    item=checked_encoding(row,encoder(row,tokenizer,2048))
                    origin='first_new_selected_encoding';locations=[];new_count+=1
                confirmed[key]=item;proof[key]={'origin':origin,'original_sources':locations,
                    'encoded_sha256':digest(item),'row_sha256':digest(row)}
                dump(out/'unique_encoded'/(str(len(confirmed)-1).zfill(5)+'.json'),
                    {'encoding_key':key,'encoded':item,'provenance':proof[key]})
        for run,chosen in rows.items():
            check();items=[confirmed[encoding_key(row)] for row in chosen]
            plan=planner(items,17,151643)
            config={'experiment':'P011','category':'C','run_id':run,
                'teacher':'t15' if run=='C2a' else 't72','temperature':.8,'seed':17,
                'P':400,'K':1,'n':400,'P_cov':400,'model':MODELS['qwen'],
                'common_ordered400':expected,'first_common_usable_prefix':True,
                'S1_overlap':selection['S1_overlap'],'unverified_fallback_questions':[],
                'selection_sha256':digest(selection),'selected_ids':[r['path_id'] for r in chosen],
                'updates':UPDATES,'targets':TARGETS,'lr_vector_sha256':LR_VECTOR_SHA256,
                'training_rows_sha256':digest(chosen),'encoded_rows_sha256':digest(items),
                'plan_sha256':digest(plan),'model_admitted':False}
            checked_recipe(config,items,plan)
            for name,value in (('rows',chosen),('encoded',items),('plan',plan),('config',config)):
                dump(out/run/(name+'.json'),value)
        dump(out/'ENCODING_REUSE.json',proof)
        dump(out/'COMPLETED.json',{'common_parents':400,'student_cells':['C2a','C2b'],
            'unique_selected_encodings':len(confirmed),'first_new_encodings':new_count,
            'reused_original_encodings':len(confirmed)-new_count,'old_encoding_reruns':0,
            'old_score_reruns':0,'new_training_calls':0,'S1_overlap':selection['S1_overlap'],
            'actual_input_A1_accepted':False})
        dump(out/'MANIFEST.json',manifest(out));return out
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'error':str(exc),
            'confirmed_unique_encodings':len(confirmed),'first_new_encodings':new_count,
            'partial_must_be_retained':True,'automatic_retry':False});raise
