"""Prepared only: publish new r2 evidence once; reference immutable original inputs."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import tarfile
from experiments.p011.forced_answer_relaunch import SPEC, SCOPE, LOCAL, admit
from experiments.p011.forced_answer import CELLS
from experiments.p011.owner_0205_common import create, read, sha, utc

OUT=Path('reports/p011_20261020/forced_answer_relaunch_actual_results_v1')
R=Path('.local/p011_20261020/r1')
PART=40*1024*1024


def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);a=p.parse_args()
    spec=admit(SPEC,a.review,SCOPE);cr=read(a.review)
    cli=read(LOCAL/'cli/CLI_EXIT.json')
    collected=read(LOCAL/'collect/COMPLETED.json')
    provider=read(LOCAL/'collect/PROVIDER_STOPPED0.json')
    if provider['state'].lower()!='stopped' or provider['owned_containers']!=0:
        raise ValueError('The original r2 app must be truly stopped with zero owned containers')
    dispatch=read(LOCAL/'dispatch/SUBMITTED.json');intent=read(LOCAL/'dispatch/INTENT.json')
    if provider['app_id']!=dispatch['app_id'] or intent['app_id']!=dispatch['app_id']:
        raise ValueError('Original r2 identity differs')
    result_file=LOCAL/'dispatch/RESULT.json'
    if not result_file.exists():result_file=LOCAL/'dispatch/RETURN_ERROR.json'
    worker=read(result_file)
    # Every generated complete cell must have terminal local closeout or an
    # explicitly preserved new failure, never silently disappear from a report.
    for cell,status in collected['cell_statuses'].items():
        if status!='completed':continue
        audit=LOCAL/'audit'/cell;score=LOCAL/'score'/cell
        if not (audit/'COMPLETE_PROOF.json').exists():
            if not (audit/'FAILED.json').exists():raise ValueError('Complete cell still awaits its first oracle: '+cell)
        elif not (score/'COMPLETED.json').exists() and not (score/'FAILED.json').exists():
            raise ValueError('Complete cell still awaits its first score: '+cell)
    analysis=read(LOCAL/'analysis/COMPLETED.json')
    if sha(LOCAL/'analysis/RESULTS.json')!=analysis['results_sha256']:
        raise ValueError('Original first analysis binding differs')
    OUT.mkdir(parents=True,exist_ok=False)
    create(OUT/'PUBLICATION_ATTEMPT.json',{'utc':utc(),'metadata_and_new_results_only':True,
           'original_input_encoding_primary_scores_and_archives_repeated':False})
    try:
        selected=[]
        for folder in ['collect/cells','audit','score','analysis']:
            base=LOCAL/folder
            if base.exists():selected.extend(p for p in sorted(base.rglob('*')) if p.is_file())
        for name in ['dispatch/SUBMITTED.json','cli/CLI_EXIT.json','cli/IMPORT_WATCHDOG_PASSED.json',
                     'cli/WATCHDOG_STOP.json','collect/COMPLETED.json','collect/PROVIDER_STOPPED0.json']:
            q=LOCAL/name
            if q.exists():selected.append(q)
        selected.append(result_file)
        if len(set(selected))!=len(selected):raise ValueError('Duplicate new evidence member')
        # Full monthly meter, global provider lists, ADMISSION/INTENT and raw
        # workspace-bearing CLI are private. Publish exact hashes and limited
        # per-attempt financial facts, not those original private payloads.
        costs={key:intent['budget_check'][key] for key in [
            'worker_hard_seconds','startup_seconds','platform_grace_seconds',
            'failed_first_compute_upper_usd','second_compute_upper_usd',
            'both_noncompute_allowances_usd','cumulative_task_upper_usd']}
        costs.update(failed_first_reported_tagged_usd=intent['budget']['failed_first_reported_tagged_usd'],
                     original_first_failure_cost_retained=True,final_invoice_claimed=False)
        create(OUT/'COST_PUBLIC_PROJECTION.json',costs)
        create(OUT/'ACTUAL_RESULT_BINDING.json',{'scope':'p011-forced-answer-relaunch-results-actual-A3',
            'source_review_target':cr['target_commit'],'source_spec_sha256':sha(SPEC),
            'source_review_sha256':sha(a.review),'report_sha256':cr['report_sha256'],
            'original_input_target':'2921c7b937c5d4d02120013ef710ecd2a55db31a',
            'original_input_manifest_sha256':intent['input_manifest_sha256'],
            'original_failed_attempt_target':'10b74e99bb4b544fac7752d82c51b27a7125b9b8',
            'original_failed_attempt_app':intent['parent_app_id'],'r2_app':dispatch['app_id'],
            'r2_call':dispatch['call_id'],'worker_terminal_file':str(result_file),
            'worker_terminal':worker,'cli_exit':cli,'collected_cell_statuses':collected['cell_statuses'],
            'analysis_completed_sha256':sha(LOCAL/'analysis/COMPLETED.json'),
            'private_intent_sha256':sha(LOCAL/'dispatch/INTENT.json'),
            'private_original_cli_sha256':sha(LOCAL/'cli/ORIGINAL_RUN.log'),
            'partial_cells_not_scored_or_zero':True,'actual_A3_accepted':False})
        inventory={str(q.relative_to(LOCAL)):{'bytes':q.stat().st_size,'sha256':sha(q)} for q in selected}
        create(OUT/'MEMBERS.json',inventory)
        scratch=R/'FORCED_RELAUNCH_NEW_RESULTS.tar.gz'
        with scratch.open('xb') as raw:
            with tarfile.open(fileobj=raw,mode='w:gz') as tar:
                for q in selected:tar.add(q,arcname=str(q.relative_to(LOCAL)),recursive=False)
        observed={}
        with tarfile.open(scratch,'r:gz') as tar:
            for member in tar:
                if not member.isfile() or member.name in observed:raise ValueError('Invalid new archive member')
                stream=tar.extractfile(member);h=hashlib.sha256();n=0
                for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block);n+=len(block)
                observed[member.name]={'bytes':n,'sha256':h.hexdigest()}
        if observed!=inventory:raise ValueError('New results archive readback differs')
        parts=[]
        with scratch.open('rb') as stream:
            i=0
            while True:
                block=stream.read(PART)
                if not block:break
                name=f'NEW_RESULTS.tar.gz.part{i:03d}'
                with (OUT/name).open('xb') as output:output.write(block)
                parts.append({'name':name,'bytes':len(block),'sha256':hashlib.sha256(block).hexdigest()});i+=1
        create(OUT/'ARCHIVE.json',{'parts':parts,'original_new_members':len(inventory),
            'total_uncompressed_bytes':sum(x['bytes'] for x in inventory.values()),
            'complete_new_archive_readback_done_once':True,'original_scientific_archives_rebuilt':False})
        (OUT/'README.md').write_text('''# Forced-answer delegated relaunch actual evidence

The original import failure and its costs remain retained. This is the single
explicitly delegated extra attempt. Only complete new cells receive original
v3 native64 decoding and frozen scoring; partial cells stay raw and unavailable.
Natural original labels are reused and primary scientific results are unchanged.
Fixed suffix, posthoc selection, single training seed and descriptive looping
heuristic limit interpretation; improvements cannot establish a unique cause.
Original inputs and private model bytes are referenced, not republished or
claimed independently examined. The financial projection is not a final invoice.
Independent actual A3 of new native tokens, correctness and scopes is pending.
''')
        (OUT/'PUBLICATION_PRODUCER.py').write_bytes(Path(__file__).read_bytes())
        manifest={'files':{q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in sorted(OUT.iterdir()) if q.is_file()}}
        create(OUT/'MANIFEST.json',manifest)
        create(R/'FORCED_RELAUNCH_ACTUAL_PUBLICATION_DONE.json',{'utc':utc(),'packet':str(OUT),
            'manifest_sha256':sha(OUT/'MANIFEST.json'),'members':len(inventory),'actual_A3_accepted':False})
        print(OUT,flush=True)
    except BaseException as exc:
        create(OUT/'PUBLICATION_FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()
