"""Finalize unpublished Tier3 config metadata without repeating input preparation.

The first preparation omitted the existing contract's literal tier=3 field.
Only this field is added; all source rows, encodings and computed plans are copied.
The original first preparation is retained unmodified and never run again.
"""
from pathlib import Path
import shutil,json
from experiments.p010.common import read,dump,sha,manifest,utc
from experiments.p010.student_contract import CELLS
from experiments.p010.student_training import checked_recipe

def execute(root):
 r=Path(root);old=r/'seed29_inputs_r1';out=r/'seed29_inputs_r2';summary=read(old/'COMPLETED.json')
 if summary['status']!='PREPARED_A1_PENDING' or (old/'FAILED.json').exists():raise ValueError('Original complete preparation required')
 old_manifest=read(old/'MANIFEST.json')
 for n,e in old_manifest.items():
  if e!=dict(bytes=(old/n).stat().st_size,sha256=sha(old/n)):raise ValueError('Original prepared byte mismatch')
 out.mkdir();changes={}
 for run in summary['cells']:
  cell=CELLS[run];assert cell['tier']==3 and cell['seed']==29
  source=read(old/run/'config.json');assert 'tier' not in source
  config=dict(source,tier=3);recipe=checked_recipe(config,read(old/run/'encoded.json'),read(old/run/'plan.json'))
  for name in ['rows.json','encoded.json','plan.json']:
   dest=out/run/name;dest.parent.mkdir(parents=True,exist_ok=True)
   with (old/run/name).open('rb') as f,dest.open('xb') as g:shutil.copyfileobj(f,g)
   assert sha(dest)==sha(old/run/name)
  dump(out/run/'config.json',config)
  changes[run]=dict(original_config_file_sha256=sha(old/run/'config.json'),final_config_file_sha256=sha(out/run/'config.json'),only_field_added=dict(tier=3),actual_original_contract_recipe=recipe)
 with (old/'MATH_ENDPOINT.json').open('rb') as f,(out/'MATH_ENDPOINT.json').open('xb') as g:shutil.copyfileobj(f,g)
 dump(out/'ORIGINAL_COMPLETED.json',summary);dump(out/'ORIGINAL_PREPARATION_MANIFEST.json',old_manifest)
 dump(out/'METADATA_FINALIZATION.json',dict(utc=utc(),changes=changes,source_sha256=sha(__file__),original_preparation_source_sha256=sha('scripts/prepare_p010_seed29_inputs.py'),original_preparation_r1_preserved=True,new_schedule_builds=0,new_encodings=0,new_model_calls=0))
 dump(out/'COMPLETED.json',dict(**summary,metadata_finalization_utc=utc(),literal_tier_field=3,old_original_contract_validated=True,original_preparation_unmodified=True))
 dump(out/'MANIFEST.json',manifest(out));return changes
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);print(json.dumps(execute(p.parse_args().root)))
