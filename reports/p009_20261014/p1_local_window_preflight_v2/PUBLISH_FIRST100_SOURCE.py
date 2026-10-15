"""Prepare original P1 first100 evidence for numerical review; never score or admit."""
from datetime import datetime,timezone
import gzip,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,'.')
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
from experiments.learning_regime_p009.p1_input_binding_extended import SOURCE_PATHS,GENERATION_TARGET,GENERATION_SPEC_SHA
from scripts.p009_p1_driver_extended import accepted

R=Path('.local/p009_20261014/r1');ROOT=R/'p1_actual_r1'
OUT=Path('reports/p009_20261014/p1_first100_actual_v1')

def main():
    review=accepted(R/'MATH_P1_DRIVER_EXTENDED_CODE_ACCEPTED.json')
    if OUT.exists():raise FileExistsError('Original or partial publication exists; reconcile, never rebuild')
    frozen=read(ROOT/'FROZEN.json');proposal=read(ROOT/'FIRST100_PROPOSAL.json')
    done=read(ROOT/'FIRST100_COMPLETED.json');basis=read(ROOT/'journal/BASIS.json')
    chunk=ROOT/'journal/chunks/00000';proof=read(chunk/'COMPLETED.json');intent=read(chunk/'INTENT.json')
    if (any((ROOT/n).exists() for n in ('FIRST100_FAILURE.json','REMAINDER_STARTED.json','REMAINDER_FAILURE.json'))
        or sorted(p.name for p in (ROOT/'journal/chunks').iterdir())!=['00000']
        or frozen['rows_sha256']!=sha(ROOT/'ROWS.json')
        or frozen['binding_sha256']!=sha(ROOT/'INPUT_BINDING.json')
        or frozen['exclusions_sha256']!=sha(ROOT/'UNSUPPORTED_GOLD.json')
        or proposal['basis_sha256']!=digest(basis)
        or proposal['first100_result_sha256']!=sha(chunk/'RESULT.json')
        or proposal['driver_source_files']!=review['source_files']
        or proof['intent_sha256']!=sha(chunk/'INTENT.json')
        or proof['result_sha256']!=sha(chunk/'RESULT.json')
        or proof['confirmed_rows']!=100 or proof['technical_unknown']!=0
        or intent['start']!=0 or intent['end']!=100
        or done['model_calls']!=0 or not 0<done['total_command_seconds']<=1200):
        raise ValueError('Real committed first100/source/input binding differs')
    sources={n:sha(n) for n in SOURCE_PATHS}
    if sources!=review['source_files']:raise ValueError('Accepted source set changed')
    OUT.mkdir(parents=True,exist_ok=False)
    copied={}
    names=['FROZEN.json','INPUT_BINDING.json','INPUT_SUMMARY.json','UNSUPPORTED_GOLD.json',
        'FIRST100_STARTED.json','FIRST100_COMPLETED.json','FIRST100_PROPOSAL.json',
        'journal/BASIS.json','journal/chunks/00000/INTENT.json','journal/chunks/00000/RESULT.json',
        'journal/chunks/00000/COMPLETED.json','journal/chunks/00000/TIMING.json']
    names += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'journal/pairs').glob('*.json'))]
    for name in names:
        src=ROOT/name;dst=OUT/'original'/name;dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb') as f:f.write(src.read_bytes())
        if sha(dst)!=sha(src):raise ValueError('Original evidence readback differs')
        copied[name]=dict(bytes=src.stat().st_size,sha256=sha(src))
    raw=(ROOT/'ROWS.json').read_bytes()
    with (OUT/'ROWS.json.gz').open('xb') as f:f.write(gzip.compress(raw,mtime=0))
    if gzip.decompress((OUT/'ROWS.json.gz').read_bytes())!=raw:raise ValueError('Lossless roster readback differs')
    for name,h in sources.items():
        dst=OUT/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb') as f:f.write(Path(name).read_bytes())
        if sha(dst)!=h:raise ValueError('Exact source copy differs')
    dump(OUT/'SOURCE_BINDING.json',dict(source_files=sources,generation_target_commit=GENERATION_TARGET,
        generation_spec_sha256=GENERATION_SPEC_SHA,actual_driver_review={k:v for k,v in review.items() if k!='local_report_path'},
        publisher_source_sha256=sha(__file__),actual_first100_report_pending=True))
    dump(OUT/'ORIGINAL_BYTES.json',dict(original_files=copied,rows_file_sha256=hashlib.sha256(raw).hexdigest(),
        rows_bytes=len(raw),rows_encoding='lossless gzip; decompress to exact original JSON bytes'))
    (OUT/'README.md').write_text('''# Actual MATH P1 first100 — numerical review requested

The first100 original ordered rows were scored once by the accepted pinned local
journal/pool. This packet copies original rows, pairs, results, timing, bindings
and code; it performs no symbolic call, raw decoding or new score calculation.
The complete frozen remaining roster is losslessly gzipped for independent
unique-pair and timing reconstruction. No remainder has run and no eligibility,
G0 or Stage1 admission follows from publication.

The original serial maximum-new-pair scenario adds an uncalibrated300-second
allowance and20% margin. It assumes no two-worker speedup and is not a runtime
upper bound or a calibrated probability. First command time includes setup and
proof writes except its final timing record as disclosed. Completed cache pairs,
including timeouts, are reused; partial or unconfirmed work may not be retried.
Actual disagreement/fallback samples and pool timeout flags still require the
later complete P1 audit before any teacher eligibility or mathematical G0 use.
''')
    (OUT/'REVIEW_REQUEST.md').write_text('''# Exact first100 throughput review

Request p009-math-p1-first100-throughput-r1.
Scope p009-math-p1-first100-throughput.
Independently inspect original first100 results and pair observations, the full
frozen input roster and exact10-source driver/journal/scorer binding. Recompute
the registered serial scenario using all observed new-pair times, remaining
distinct pairs,20% and300-second allowance without favorable timing selection.
Verify original failed/timeout results remain cached and no primary labels or
eligibility have been admitted. Explicitly retain proxy/warm-local limitations.
If acceptable, bind the actual FIRST100_PROPOSAL file SHA, basis_sha256, local_window_amendment_sha256,
first100_result_sha256, driver_source_files and approved_total_wall_seconds
(integer <=129600, >= actual scenario). The driver subtracts original first
command elapsed time from that total before the sole remainder invocation.
Return real fixed report/target/scope/decision; this is no G0 or final P1 PASS.
''')
    dump(OUT/'MANIFEST.json',manifest(OUT))
    dump(R/'P1_FIRST100_PUBLICATION_CREATED.json',dict(utc=datetime.now(timezone.utc).isoformat(),path=str(OUT),
        proposal_sha256=sha(ROOT/'FIRST100_PROPOSAL.json'),new_symbolic_calls=0,new_model_calls=0))
    print(OUT)

if __name__=='__main__':main()
