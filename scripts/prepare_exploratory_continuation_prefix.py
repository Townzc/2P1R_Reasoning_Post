"""First independent decoding/scoring of all 496 saved parent outputs; zero models."""
import argparse, datetime, time
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,verify
from experiments.sft_exploratory_20261014.continuation_prefix import COUNTS,inspect_prefix
from experiments.sft_exploratory_20261014.cached_audit import audit_batch
from src.sft_data import read_jsonl


def main(root, out):
    from transformers import AutoTokenizer
    root, out = Path(root),Path(out);out.mkdir(exist_ok=False)
    dump(out/'INTENT.json',dict(started_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         source_sha256=sha(__file__),operation='first_all_saved_prefix_independent_raw_oracle',new_model_calls=0))
    try:
        inputs=root/'inputs';spec=read('reports/exploratory_20261014/admission_v1/ADMISSION.json')
        if sha(inputs/'manifest.json')!=spec['input_manifest_sha256']:raise ValueError('Inputs differ')
        verify(inputs,read(inputs/'manifest.json')['files'])
        ledger=read(root/'interrupted_preservation_r1/ledger.json')
        rows=read_jsonl(inputs/'gsm8k_test1319.jsonl');proofs={}
        for logical in COUNTS:
            parent=root/'interrupted_preservation_r1'/logical/'evidence'
            binding,_=inspect_prefix(parent,inputs,ledger,logical,spec)
            tokenizer=(inputs/'instruct_model' if logical=='instruct_0shot' else
                       Path('.local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer'))
            tok=AutoTokenizer.from_pretrained(tokenizer,local_files_only=True)
            eos=[151645,151643] if logical=='instruct_0shot' else [tok.eos_token_id]
            prompts=read(inputs/(logical+'_prompts.json'));timings=[]
            for b in binding['batches']:
                start=b['start'];tick=time.monotonic()
                audit_batch(read(parent/b['raw_file']),read_jsonl(parent/b['scored_file']),
                            rows[start:start+16],prompts[start:start+16],tok,eos)
                timings.append(dict(start=start,seconds=time.monotonic()-tick))
            proof=dict(passed=True,binding=binding,all_saved_raw_independently_decoded=True,
                       endpoint_complete=False,partial_accuracy_reported=False,
                       local_cached_audit_timings=timings,cloud_speed_measured=False,
                       original_ledger_file_sha256=sha(root/'interrupted_preservation_r1/ledger.json'))
            dump(out/(logical+'.json'),proof);proofs[logical]=sha(out/(logical+'.json'))
        dump(out/'VERIFIED.json',dict(passed=True,saved_outputs=496,unacknowledged_original_rows=48,
             proofs=proofs,new_generation=0,new_training=0,
             checkpoint_verification=read(root/'interrupted_reconciliation_r1/STUDENT_CHECKPOINT_VERIFIED.json'),
             finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        print('All 496 saved raw outputs independently verified; no generation/training.',flush=True)
    except BaseException as exc:
        dump(out/'FAILURE.json',dict(type=type(exc).__name__,error=str(exc),partial_retained=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();main(a.root,a.out)
