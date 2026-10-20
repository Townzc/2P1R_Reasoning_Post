"""Read original saved raw token-list lengths only; no decode, model or scoring."""
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,utc
r=Path('.local/p010_20261019/r1');out=r/'e3_t08_metadata_r1';assert not out.exists()
source=r/'e3_inputs_r1/ORIGINAL_T08_ROWS.json';rows=read(source);env=read(r/'teacher_t72_r1/RESULT.json')
assert env['status']=='completed' and len(rows)==1600
files={};cache={};lengths=[]
for item in rows:
 old=item['original_record'];assert digest(old)==item['original_record_sha256']
 name=old['raw_file'];path=r/'teacher_t72_export_r1/evidence'/name
 if name not in cache:
  expected=env['artifact']['all_files'][name]
  assert path.stat().st_size==expected['bytes'] and sha(path)==expected['sha256']
  raw=read(path);cache[name]={x['candidate_id']:x for x in raw};assert len(cache[name])==len(raw)
  files[name]=expected
 x=cache[name][old['candidate_id']];assert digest(x)==old['raw_record_sha256']
 n=len(x['token_ids']);assert 0<n<=1024
 lengths.append(dict(candidate_id=old['candidate_id'],original_record_sha256=digest(old),raw_file=name,
  raw_record_sha256=digest(x),physical_returned_tokens=n,old_symbolic_score_unchanged=True))
assert len({x['candidate_id'] for x in lengths})==1600
out.mkdir();dump(out/'PHYSICAL_LENGTHS.json',lengths);dump(out/'ORIGINAL_RAW_FILE_BINDING.json',files)
dump(out/'COMPLETED.json',dict(utc=utc(),original_rows_sha256=sha(source),length_rows_sha256=sha(out/'PHYSICAL_LENGTHS.json'),
 original_model_result_sha256=sha(r/'teacher_t72_r1/RESULT.json'),original_raw_file_binding_sha256=sha(out/'ORIGINAL_RAW_FILE_BINDING.json'),
 rows=1600,old_raw_decodes=0,old_symbolic_calls=0,new_model_calls=0,new_generated_tokens=0))
print('Original1600 saved physical lengths prepared; no decode/scoring/model')
