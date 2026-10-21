"""One create-only original-byte archive and metadata handoff, no science calls."""
from pathlib import Path
import datetime
import gzip
import hashlib
import io
import json
import tarfile

R=Path('.local/p011_20261020/r1')
SOURCE=R/'ot3_inputs_nfc_r1'
OUT=Path('reports/p011_20261020/ot3_nfc_inputs_actual_v1')


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def dump(p,v):
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')


class Split(io.RawIOBase):
    def __init__(self,root):self.root,self.stream,self.size,self.parts=root,None,0,[]
    def writable(self):return True
    def write(self,data):
        data=memoryview(data);original=len(data)
        while data:
            if self.stream is None or self.size==40*1024*1024:
                if self.stream:self.stream.close()
                path=self.root/f'original_artifacts.tar.gz.part{len(self.parts):03d}'
                self.parts.append(path);self.stream=path.open('xb');self.size=0
            n=min(len(data),40*1024*1024-self.size)
            self.stream.write(data[:n]);self.size+=n;data=data[n:]
        return original
    def finish(self):
        if self.stream:self.stream.close()


class Joined(io.RawIOBase):
    def __init__(self,paths):self.paths,self.index,self.f=paths,0,None
    def readable(self):return True
    def read(self,n=-1):
        if n<0:raise ValueError('Bounded streaming required')
        pieces=[]
        while n and self.index<len(self.paths):
            if self.f is None:self.f=self.paths[self.index].open('rb')
            data=self.f.read(n)
            if data:pieces.append(data);n-=len(data)
            else:self.f.close();self.f=None;self.index+=1
        return b''.join(pieces)
    def close(self):
        if self.f:self.f.close()
        super().close()


def main():
    if (SOURCE/'FAILED.json').exists():raise ValueError('Preserve genuine failure; no completed publication')
    done=json.loads((SOURCE/'CONSTRUCTION_COMPLETED.json').read_text())
    if (done['planning_failures'] or done['reused_confirmed_encodings']!=965
            or done['new_encodings']!=9115 or done['total_unique_encodings']!=10080
            or done['parents']!=4032):raise ValueError('Actual full construction required')
    cli=json.loads((R/'CLI_SESSIONS.json').read_text())['ot3_nfc_continuation']
    if cli['session_id']!=32741 or cli['state']!='EXIT0_CONSUMED':raise ValueError('Original CLI must be closed')
    original=json.loads((SOURCE/'MANIFEST.json').read_text())['files']
    expected={**original,'MANIFEST.json':{'bytes':(SOURCE/'MANIFEST.json').stat().st_size,'sha256':sha(SOURCE/'MANIFEST.json')}}
    if any('/' in k or k.startswith('.') or (SOURCE/k).is_symlink() for k in expected):raise ValueError('Unexpected original member')
    OUT.mkdir(exist_ok=False)
    (OUT/'COPY_SCRIPT.py').write_bytes(Path(__file__).read_bytes())
    sink=Split(OUT)
    with gzip.GzipFile(fileobj=sink,mode='wb',compresslevel=1,mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w|') as tar:
            for name in sorted(expected):
                info=tarfile.TarInfo(name);info.size=expected[name]['bytes'];info.mode=0o644;info.mtime=0
                with (SOURCE/name).open('rb') as f:tar.addfile(info,f)
    sink.finish();observed={};joined=Joined(sink.parts)
    with tarfile.open(fileobj=joined,mode='r|gz') as tar:
        for m in tar:
            if not m.isfile() or m.name not in expected or m.name in observed:raise ValueError('Archive member mismatch')
            h=hashlib.sha256();size=0
            with tar.extractfile(m) as f:
                for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b);size+=len(b)
            observed[m.name]={'sha256':h.hexdigest(),'bytes':size}
    joined.close()
    if observed!=expected:raise ValueError('Original-byte archive mismatch; retain partial publication, no retry')
    print(json.dumps({'archive_parts':len(sink.parts),'archive_bytes':sum(p.stat().st_size for p in sink.parts),'readback_members':len(observed)}),flush=True)
    for name in expected:
        if name.endswith('.json'):(OUT/name).write_bytes((SOURCE/name).read_bytes())
    dump(OUT/'ARCHIVE_READBACK.json',{'parts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sink.parts},
         'original_members':observed,'all_original_bytes_equal':True,'original_manifest_sha256':expected['MANIFEST.json']['sha256'],
         'source_inputs_mutated':False,'whole_publisher_retry_allowed':False})
    # New result-only verification of the copied prefix; no tokenizer or old builder.
    prefix={}
    for name in ('SELECTED_RAW.jsonl','ENCODED.jsonl'):
        old=R/'ot3_inputs_4032_r1'/name;h=hashlib.sha256()
        with (SOURCE/name).open('rb') as f:
            for _ in range(965):
                line=f.readline()
                if not line.endswith(b'\n'):raise ValueError('Complete confirmed prefix required')
                h.update(line)
        oldsha=sha(old)
        if h.hexdigest()!=oldsha:raise ValueError('Original965 byte prefix differs')
        prefix[name]={'original965_file_sha256':oldsha,'new_first965_bytes_sha256':h.hexdigest(),'equal':True}
    dump(OUT/'CONFIRMED_PREFIX_BYTE_REUSE.json',prefix)
    counts={'total':0,'reused':0,'new':0,'new_normalization_changed_text':0}
    with (SOURCE/'NATIVE_NORMALIZATION.jsonl').open() as f:
        for line in f:
            v=json.loads(line);counts['total']+=1
            if v.get('encoding_reused') is True:counts['reused']+=1
            else:
                counts['new']+=1;counts['new_normalization_changed_text']+=int(v['normalization_changed_text'])
    if (counts['total'],counts['reused'],counts['new'])!=(10080,965,9115):raise ValueError('Full normalization record inventory differs')
    dump(OUT/'NORMALIZATION_COUNTS.json',{'counts':counts,'basis':'Original saved normalization proof flags counted once; no encoding, normalization or decode repeated.'})
    dose=json.loads((SOURCE/'FROZEN_DOSE.json').read_text())
    dump(OUT/'SUMMARY.json',{'written_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'completed':done,'dose':dose,'normalization_counts':counts,'actual_A1_accepted':False,'training_admitted':False,
         'source_target':'10738e624300ff125c59fd127e798bc4e5fbdc85','original_cli':32741,
         'complete_CR_acceptance_file_sha256':sha(R/'OT3_NFC_CONTINUATION_CR_ACCEPTED.json'),
         'owner_file_sha256':sha(R/'OWNER_OT3_NFC_CONTINUATION.json'),
         'both_original_failed_parents_retained':True,'new_model_calls':0,'new_reserved_usd':0})
    binding=json.loads(Path('reports/p011_20261020/ot3_nfc_continuation_preflight_v1/SOURCE_BINDING.json').read_text())
    dump(OUT/'SOURCE_BINDING.json',{'original_full_source_and_input_binding':binding,
         'complete_CR_packet':'reports/p011_20261020/review_c7977d2a_NFC_complete_CR_and_diagnostic_request_v1',
         'copy_script_sha256':sha(__file__),'new_constructed_manifest_sha256':expected['MANIFEST.json']['sha256'],
         'old_4096_adequacy':'FAIL_RETAINED','original4032strict_roundtrip_failure':'FAIL_RETAINED',
         'all16_strong_completeness_selection_limit_retained':True,'diagnostic_does_not_change_this_input':True})
    (OUT/'README.md').write_text('''# Actual approved NFC continuation — full input A1 pending

The one independently approved continuation completed. Original965 raw/encoded
lines were reused byte-for-byte; only9115 remaining identities were encoded.
All10080 answers,4032parents and eight owner-amended cells retain their original
selection. SUMMARY copies the original completed record and frozen B/U/dose;
NORMALIZATION_COUNTS counts the saved proof flags without rerunning encoding.
All raw/NFC/decode hashes remain in the original normalization journal.

Concatenate original_artifacts.tar.gz.partNNN in lexical order to recover the
full original archive. Each part is below40MiB. A single streaming readback
matched every member to the original constructor manifest, including full raw,
encoded tokens, complete plans, dose, intent, membership and normalization proof.
The two original965 file hashes separately match the new first965 lines.
No old constructor, preservation, filtering, symbolic scorer or model was rerun.
The original43GBSQLite stays private; its hash is not an external byte inspection.

The original4096 adequacy failure and strict-raw-roundtrip4032 failure remain
failed. NFC-only validation is the audited fixed tokenizer's own behavior, not
NFKC, whitespace cleanup or truncation. Strong all16-completeness selection and
missing difficulty labels remain limitations; the separately requested read-only
diagnostic cannot change these inputs. Real actual A1 is still required before
any training. No scientific model or paid reservation has been made.
''')
    dump(OUT/'PUBLIC_MANIFEST.json',{p.name:{'sha256':sha(p),'bytes':p.stat().st_size}
         for p in sorted(OUT.iterdir()) if p.is_file()})
    dump(R/'NFC_ACTUAL_PUBLICATION_DONE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'packet':str(OUT),'members':len(list(OUT.iterdir()))-1,'archive_readback_complete':True})
    print(json.dumps({'packet':str(OUT),'B':dose['B'],'U':dose['U'],'normalization_counts':counts}),flush=True)


if __name__=='__main__':main()
