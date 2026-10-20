"""Create-only deterministic copy/archive for the two finished original builders.
No source import, dataset construction, tokenization, scoring or model call.
"""
from pathlib import Path
import datetime
import gzip
import hashlib
import io
import json
import tarfile

R = Path('.local/p011_20261020/r1')
OUT = Path('reports/p011_20261020/am_inputs_actual_v1')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(8*1024*1024): h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    with path.open('x') as f: json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2); f.write('\n')


class Split(io.RawIOBase):
    def __init__(self, root):
        self.root, self.stream, self.size, self.parts = root, None, 0, []
    def writable(self): return True
    def write(self, data):
        data = memoryview(data); original = len(data)
        while data:
            if self.stream is None or self.size == 40*1024*1024:
                if self.stream: self.stream.close()
                path = self.root / f'original_artifacts.tar.gz.part{len(self.parts):03d}'
                self.parts.append(path); self.stream = path.open('xb'); self.size = 0
            n = min(len(data), 40*1024*1024-self.size)
            self.stream.write(data[:n]); self.size += n; data = data[n:]
        return original
    def finish(self):
        if self.stream: self.stream.close()


class Joined(io.RawIOBase):
    def __init__(self, paths): self.paths, self.index, self.f = paths, 0, None
    def readable(self): return True
    def read(self, n=-1):
        if n < 0: raise ValueError('Use bounded archive streaming')
        pieces = []
        while n and self.index < len(self.paths):
            if self.f is None: self.f = self.paths[self.index].open('rb')
            data = self.f.read(n)
            if data: pieces.append(data); n -= len(data)
            else: self.f.close(); self.f = None; self.index += 1
        return b''.join(pieces)
    def close(self):
        if self.f: self.f.close()
        super().close()


def main():
    completed = {}
    for mode in ('am',):
        source = R / (mode + '_inputs_r1')
        if (source/'FAILED.json').exists(): raise ValueError('Original builder failure retained; no complete packet')
        done = json.loads((source/'CONSTRUCTION_COMPLETED.json').read_text())
        if done['planning_failures']: raise ValueError('Actual whole-answer planning failure must be reported')
        completed[mode] = done
        json.loads((source/'MANIFEST.json').read_text())
    OUT.mkdir()
    with (OUT/'COPY_SCRIPT.py').open('xb') as f: f.write(Path(__file__).read_bytes())
    summary = {'written_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'actual_A1_accepted':False,'training_admitted':False,'model_calls':0,
        'construction_source_commit':'df4d590485a2bb6b8cb2eeb02e8688f64ebd03db',
        'construction_review_commit':'5c91d0d1c65f92d7fbaed123f2bad9485c8d33b4','modes':{}}
    for mode in ('am',):
        source, dest = R/(mode+'_inputs_r1'), OUT/mode
        dest.mkdir()
        manifest = json.loads((source/'MANIFEST.json').read_text())
        expected = {k:v for k,v in manifest['files'].items() if k!='RAW_INDEX.sqlite'}
        expected['MANIFEST.json'] = {'bytes':(source/'MANIFEST.json').stat().st_size,'sha256':sha(source/'MANIFEST.json')}
        if any('/' in k or k.startswith('.') for k in expected): raise ValueError('Unexpected original artifact name')
        sink = Split(dest)
        with gzip.GzipFile(fileobj=sink, mode='wb', compresslevel=1, mtime=0, filename='') as gz:
            with tarfile.open(fileobj=gz, mode='w|') as tar:
                for name in sorted(expected):
                    info = tarfile.TarInfo(name); info.size=expected[name]['bytes'];info.mode=0o644;info.mtime=0
                    with (source/name).open('rb') as f: tar.addfile(info,f)
        sink.finish()
        observed={}
        joined=Joined(sink.parts)
        with tarfile.open(fileobj=joined,mode='r|gz') as tar:
            for member in tar:
                if not member.isfile() or member.name not in expected or member.name in observed: raise ValueError('Archive member mismatch')
                h=hashlib.sha256();size=0
                with tar.extractfile(member) as f:
                    while chunk:=f.read(8*1024*1024): h.update(chunk);size+=len(chunk)
                observed[member.name]={'bytes':size,'sha256':h.hexdigest()}
        joined.close()
        if observed!=expected: raise ValueError('Original byte readback mismatch; retain partial packet, no whole retry')
        for name in sorted(expected):
            if name.endswith('.json'):
                with (dest/name).open('xb') as f:f.write((source/name).read_bytes())
        proof={'parts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sink.parts},
            'original_members':observed,'all_readback_equal':True,
            'omitted_original_files':{'RAW_INDEX.sqlite':manifest['files']['RAW_INDEX.sqlite']},
            'omission_reason':'Original derived SQLite index stays private and unmodified; selected raw, encoded tokens, plans and dispositions are lossless in archive.'}
        dump(dest/'ARCHIVE_READBACK.json',proof)
        counts=json.loads((source/'FILTER_COUNTS.json').read_text())
        summary['modes'][mode]={'completed':completed[mode],
            'dose':json.loads((source/'FROZEN_DOSE.json').read_text()),'counts':counts['counts'],
            'source_agreement':counts.get('source_agreement'),
            'original_manifest_sha256':expected['MANIFEST.json']['sha256'],
            'archive_readback_sha256':sha(dest/'ARCHIVE_READBACK.json')}
        print(json.dumps({'mode':mode,'archive_parts':len(sink.parts),'readback_members':len(observed)}),flush=True)
    dump(OUT/'SUMMARY.json',summary)
    bindings=json.loads(Path('reports/p011_20261020/long_data_preflight_v2/SOURCE_BINDING.json').read_text())
    dump(OUT/'SOURCE_BINDING.json',{'original_data_code_binding':bindings,
        'owner_amendment_file_sha256':sha(R/'OWNER_LONG_DATA_AMENDMENT.json'),
        'exact_CR_acceptance_file_sha256':sha(R/'LONG_DATA_CR_ACCEPTED.json'),
        'CR_public_packet':'reports/p011_20261020/review_5c91d0d1_data_CR_accepted_v1',
        'copy_script_sha256':sha(__file__), 'no_scientific_operations_reexecuted':True})
    (OUT/'README.md').write_text('''# Actual AM construction — A1 pending

The original AM builder ran once after real revised CR. The separate OT3 attempt failed its4038/4096 parent-count gate and is preserved in ot3_insufficient_parents_v1. No model, training,
generation, symbolic scoring or previous construction was repeated. SUMMARY
copies saved counts, dose and completion records without recomputing selections.
The direct owner adopted R1/R3 before construction; original plan and first
CHANGES-REQUIRED candidate remain in history. Construction source df4d5904 and
real code review5c91d0d1 bind the complete source/owner/input chain.

Each mode's gzip archive is split into numbered parts, concatenate in lexical
order to decompress. It contains every original artifact except RAW_INDEX.sqlite,
including selected literal raw answers, exact input_ids/labels, full native masks,
cell identities, all full-answer plans, benchmark gold, parent dispositions,
filter/exclusion counts, original intent and manifest. Single streaming readback
matched every archived byte to the original constructor manifest. No reencoding,
new filtering or label validation was performed by this publisher.

The full derived SQLite indices stay private, with their original size/SHA in
the original MANIFEST and ARCHIVE_READBACK omissions. A public hash does not mean
the reviewer read their bytes. Original raw dataset revisions/paths are pinned
in long_data_preflight_v1/SOURCE_LOCK.json. Full-pool parent restoration and
stopped-prefix selection checks should disclose any inaccessible source limits.
OT3 answers are unverified for correctness. AM author verification metadata and
the full common-pool source-agreement diagnostic retain all exceptions; these
are not independent answer validation. Historic author-generation cost unknown.

Code acceptance is not actual A1 or runtime admission. Request an independent
check of count/nesting/16-way parent reconstruction, strict full native total
length/completeness/decontamination, prefix sampling order, each exact B/U,
q/q+1 exposure and all complete-answer schedules. Preserve every disagreement;
no silent response deletion, budget change, answer truncation or old rerun.
''')
    files={str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file()}
    dump(OUT/'MANIFEST.json',{'files':files})
    dump(R/'ACTUAL_DATA_PUBLICATION_DONE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'out':str(OUT),'manifest_sha256':sha(OUT/'MANIFEST.json'),'members':len(files),'done_once':True})


if __name__=='__main__': main()
