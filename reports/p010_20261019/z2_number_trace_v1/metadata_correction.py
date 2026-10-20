"""Repair only unpublished display/provenance fields; preserve first bytes."""
from pathlib import Path
import csv,json,shutil
from experiments.p010.common import dump,sha,manifest,utc
r=Path('.local/p010_20261019/r1');out=Path('reports/p010_20261019/z2_number_trace_v1')
backup=r/'z2_unpublished_metadata_correction_r1';backup.mkdir(exist_ok=False)
files=['T1_COMPOSITION.csv','NUMBER_TRACE.json','SOURCE_BINDING.json','MANIFEST.json']
original={}
for name in files:
 shutil.copyfile(out/name,backup/name);original[name]=sha(out/name)
with (out/'T1_COMPOSITION.csv').open() as f:reader=csv.DictReader(f);fields=reader.fieldnames;data=list(reader)
for row in data:
 sel=json.loads(Path('reports/p010_20261019',row['teacher']+'_data_candidate_v1','SELECTION.json').read_text())['cells'][row['cell']]
 for field,sourcefield in [('underfilled_questions','underfilled_questions'),('unverified_K1_questions','unverified_questions')]:
  val=sel.get(sourcefield,'')
  assert row[field]==str(val)
  row[field]=len(val) if isinstance(val,list) else val
with (out/'T1_COMPOSITION.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
tr=json.loads((out/'NUMBER_TRACE.json').read_text());sb=json.loads((out/'SOURCE_BINDING.json').read_text());base=Path.cwd()
for item in tr:
 path=Path(item['source'])
 if path.is_absolute():item['source']=str(path.relative_to(base))
 if item['output']=='T1_COMPOSITION.csv' and item['source'].endswith('SELECTION.json'):
  item['rule']+='; underfilled/unverified columns count original named lists, no new label check'
newbinding={str(Path(name).relative_to(base)) if Path(name).is_absolute() else name:value for name,value in sb.items()}
(out/'NUMBER_TRACE.json').write_text(json.dumps(tr,ensure_ascii=False,indent=2)+'\n')
(out/'SOURCE_BINDING.json').write_text(json.dumps(newbinding,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(__file__,out/'metadata_correction.py')
dump(out/'PREPUBLICATION_METADATA_CORRECTION.json',dict(utc=utc(),original_unpublished_sha256=original,
 reason='Named underfill/unverified lists were displayed instead of counts; assembler provenance used a host absolute locator.',
 correction='Count only the existing named lists; make assembler locator repository-relative. No original scientific source/result/label changes.',
 original_bytes_preserved_privately=True,new_scoring=0,new_statistics=0,whole_assembler_repeated=False,
 correction_source_sha256=sha(__file__)))
for f in out.rglob('*'):
 if f.is_file() and f.suffix in ('.json','.md','.csv'):
  t=f.read_text();assert '/Users/' not in t and '/var/folders/' not in t,str(f)
(out/'MANIFEST.json').unlink()
dump(out/'MANIFEST.json',manifest(out))
dump(r/'Z2_NUMBER_TRACE_METADATA_CORRECTION.json',dict(utc=utc(),original_manifest_sha256=original['MANIFEST.json'],
 corrected_manifest_sha256=sha(out/'MANIFEST.json'),new_science=0,whole_builder_repeated=False))
print(json.dumps({'corrected_unpublished_metadata_only':True,'manifest_sha256':sha(out/'MANIFEST.json')}))
