"""Create-only three complete exploratory endpoint publication; no re-score/statistical search."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,gzip,tarfile,json,shutil
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest,verify
ROOT=Path('.local/exploratory_20261014/r1/continuation_r1')
PUB=Path('reports/exploratory_20261014/completed_endpoints_v1')
SPEC=Path('reports/exploratory_20261014/continuation_admission_v1/ADMISSION.json')

def main(billing):
    spec=read(SPEC);plan=spec['plan'];allrows=[];evidence={}
    for run,cfg in spec['configs'].items():
        e=ROOT/'exports'/run/'evidence';audit=read(e/'LOCAL_ORACLE_AUDIT.json');result=read(e/'result.json')
        env=read(ROOT/'runs'/run/'result.json');col=ROOT/'closeouts'/run;provider=read(col/'provider.json')
        if (audit['passed'] is not True or audit['technical_unknown']!=0 or audit['endpoint']['n']!=1319 or
                audit['spec_sha256']!=digest(spec) or audit['source_sha256']!=digest(spec['source_files']) or
                audit['endpoint']!=result['endpoint'] or result!=env['result'] or
                read(col/'COMPLETED.json')['passed'] is not True or provider['owned_containers'] or
                any(x['lifecycle']['state']!='stopped' for x in provider['apps'])):
            raise ValueError('Every complete actual oracle/STOPPED0 required before publication')
        verify(e,env['artifact_manifest']);end=audit['endpoint']
        allrows.append(dict(role=cfg['logical_run'],physical_run=run,n=1319,correct=end['correct'],
                           accuracy_percent=100*end['correct']/1319,parsed=end['parsed'],
                           length_caps=end['stop_reasons'].get('length_cap',0),saved_prefix=cfg['offset'],
                           new_rows=1319-cfg['offset'],new_training_updates=0,technical_unknown=0))
        evidence[run]=(e,audit,env,provider)
    if PUB.exists():raise ValueError('Existing/partial immutable publication; do not rerun')
    PUB.mkdir()
    for run,(e,audit,env,provider) in evidence.items():
        d=PUB/run;d.mkdir()
        # Original compact files except the private intent/release are published
        # byte-for-byte in a disclosed projection, never called the original tar.
        source_manifest=read(e/'artifact_manifest.json')
        selected={n:v for n,v in source_manifest.items() if n not in
                  {'intent.json','compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json'} and not n.endswith('.pt')}
        with (d/'saved_suffix_evidence.tar.gz').open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z,tarfile.open(fileobj=z,mode='w') as t:
            for n in sorted(selected):
                info=t.gettarinfo(str(e/n),arcname=n);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with (e/n).open('rb') as member:t.addfile(info,member)
        with tarfile.open(d/'saved_suffix_evidence.tar.gz','r:gz') as t:
            observed={}
            import hashlib
            for m in t.getmembers():
                if not m.isfile() or m.name not in selected:raise ValueError('Unsafe or extra archive member')
                raw=t.extractfile(m).read();observed[m.name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            if observed!=selected:raise ValueError('Public archive readback differs')
        dump(d/'ARCHIVE_MANIFEST.json',selected)
        dump(d/'ARCHIVE_PROVENANCE.json',dict(archive_kind='disclosed original-byte suffix projection',
             omitted_private_intent=True,original_artifact_manifest_sha256=sha(e/'artifact_manifest.json'),
             original_compact_tar_sha256=sha(e/'compact_evidence.tar.gz'),public_tar_sha256=sha(d/'saved_suffix_evidence.tar.gz'),
             members=len(selected),new_generation=0))
        for n in ('LOCAL_ORACLE_AUDIT.json','result.json','environment.json','recipe.json','PARENT_SUFFIX_CLAIM.json','artifact_manifest.json'):
            shutil.copyfile(e/n,d/n)
        if (e/'CHECKPOINT_RESTORED.json').exists():shutil.copyfile(e/'CHECKPOINT_RESTORED.json',d/'CHECKPOINT_RESTORED.json')
        dump(d/'ENVELOPE.json',env);shutil.copyfile(ROOT/'closeouts'/run/'ledger.json',d/'LEDGER.json')
        dump(d/'PROVIDER.json',dict(original_private_sha256=sha(ROOT/'closeouts'/run/'provider.json'),
            read_at_utc=provider['utc'],owned_containers=[],projection='actor identity and unrelated workspace rows omitted',
            apps=[dict(app_id=x['app_id'],lifecycle={k:x['lifecycle'][k] for k in ('state','created_at','stopped_at')}) for x in provider['apps']]))
        sent=read(e/'intent.json');dump(d/'SOURCE_BINDING.json',dict(commit=sent['release']['commit'],source_files=sent['release']['source_files'],
            spec_sha256=digest(spec),review_commit=sent['release']['acceptance']['review_commit'],
            report_sha256=sent['release']['acceptance']['report_sha256'],original_intent_file_sha256=sha(e/'intent.json')))
    dump(PUB/'RESULTS.json',dict(rows=allrows,exploratory=True,preregistered=False,partial_endpoint=False,
          prefix_packet_commit='bdf2ffd36ffe07ac94b7cd5c03290f0a20092c1d',prefix_proofs_sha256=digest(spec['prefix_proofs']),
          original_checkpoint_manifest=spec['checkpoint_verified']['manifest'],actual_result_external_review='PENDING'))
    with (PUB/'RESULTS.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]),lineterminator='\n');w.writeheader();w.writerows(allrows)
    shutil.copyfile(billing,PUB/'LATEST_BILLING.json');shutil.copyfile(__file__,PUB/'publish_results.py')
    lines=['# Completed exploratory evaluations (non-preregistered)','',
      'All three endpoints contain the same 1,319 frozen questions. Independent local raw/dose/source oracles passed; actual-result external review is pending. Original failed parents and all496 saved outputs, including48 unacknowledged parent rows, are retained. No original output was generated again; no student retraining occurred.','',
      '|Evaluation|Correct / 1,319|Accuracy|Length caps|','|---|---:|---:|---:|']
    for x in allrows:lines.append(f"|{x['role']}|{x['correct']}|{x['accuracy_percent']:.2f}%|{x['length_caps']}|")
    lines+=['','Existing frozen references: base0-shot638/1319 (48.37%); correct-answer breadthT1 student969/1319 (73.46%); correct-answer depthT1 student965/1319 (73.16%). These are reused observed references, not newly evaluated models.','']
    for x in allrows:
        lines.append(f"- {x['role']}: descriptive difference from969reference = {100*(x['correct']-969)/1319:+.2f}percentagepoints.")
    lines+=['','The wrong-teacher student inherits the original256steps/524,287targets/seed17/LoRA/frozenLR checkpoint; all new child training updates are zero. The natural-wrong set contains429answers from101parents, not429independentquestions. Parent coverage, answer length, exposure and label ambiguity differ from the correct-answer arms; scores do not identify a causal effect of answer correctness. Reference969 is the requested breadth control;965depth is descriptive context.','',
      'Base4-shot exemplars were fixed from reserved dev only. Four-shot prompting changes content/context as well as format. General Qwen2.5-1.5B-Instruct uses its own chat template and the disclosed Math-style system prompt; it is a reference, not a proven capability ceiling or a reproduction of official leaderboard protocol.','',
      'Greedy512/context2048/batch16 and marked_answer_v1 remain frozen. Length-capped outputs count incorrect. The test has been seen previously, so these are exploratory outcomes, not fresh confirmatory evidence. No new bootstrap, statistical selection or equivalence claim is made here. Reviewer prior prefix-only analyses are not substituted for these full endpoints. The reviewer viewed and scored the preserved prefixes after continuation authorization but before suffix completion; this earlier result exposure is disclosed, and it did not change the frozen roster, inputs, arms, training dose or stopping rules.','',
      'Spending: original failures/setup/build/download/storage plus new suffix calls belong to the same experimental budget. LATEST_BILLING is delayed metering, not invoice/final cost/balance. Original historical reservations remain in the ledger.','',
      'The original P008 registered results and21PDT material freeze remain unchanged; these exploratory results are a separate dated addendum.']
    (PUB/'README.md').write_text('\n'.join(lines)+'\n')
    (PUB/'REVIEW_REQUEST.md').write_text('Review full three1319 endpoints, public suffix rawprojection plus original496prefix archive, failed-parent/child lineage, actual restoredcheckpoint proof and zero retraining, fixedparser/caps/prompts, costs and limited descriptive interpretation. Publicproof of the retained checkpoint is not independent reviewer binary access. Actual result scope exploratory-completed-three-endpoints-g3.\n')
    dump(PUB/'MANIFEST.json',manifest(PUB));print('Published locally all three complete endpoints; external G3 pending.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--billing-snapshot',required=True);main(p.parse_args().billing_snapshot)
