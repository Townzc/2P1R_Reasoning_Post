"""Complete only the unwritten config/publication tail after local schema rejection.

Original input preparation and failed metadata script remain unchanged. No plan,
encoding, teacher generation or scientific invocation is repeated. The originally
prepared model-id/revision is expressed as the existing full identity dictionary.
"""
from pathlib import Path
import json,shutil
from experiments.p010.common import read,dump,sha,manifest,utc
from experiments.p010.student_contract import CELLS
from experiments.p010.student_training import checked_recipe
from experiments.learning_regime_p009.stage0_generation_contract_v2 import MODELS

def normalize_config(source):
    if source.get('model')!=[MODELS['qwen']['model_id'],MODELS['qwen']['revision']] or 'tier' in source:
        raise ValueError('Only original unpublished representation may be finalized')
    if source.get('run_id') not in CELLS or CELLS[source['run_id']]['tier']!=3 or source['seed']!=29:
        raise ValueError('Only the four original Tier3 seed replications')
    return dict(source,tier=3,model=MODELS['qwen'])

def execute(root):
 r=Path(root);old=r/'seed29_inputs_r1';out=r/'seed29_inputs_r2'
 if not out.is_dir() or list(out.iterdir()):raise ValueError('Only untouched metadata-tail directory permitted')
 failure=r/'seed29_recipe_metadata_r2.log'
 if 'Frozen P010 whole-answer inventory/model/dose differs' not in failure.read_text():raise ValueError('Original precise local failure required')
 summary=read(old/'COMPLETED.json');changes={}
 dump(out/'TAIL_INTENT.json',dict(utc=utc(),prior_failure_log_sha256=sha(failure),old_manifest_sha256=sha(old/'MANIFEST.json'),new_source_sha256=sha(__file__),no_model_calls=True,old_prefix_manifest_validation_already_completed=True,old_manifest_validation_repeated=False))
 for run in summary['cells']:
  source=read(old/run/'config.json');config=normalize_config(source)
  recipe=checked_recipe(config,read(old/run/'encoded.json'),read(old/run/'plan.json'))
  dest=out/run;dest.mkdir()
  for name in ['rows.json','encoded.json','plan.json']:
   with (old/run/name).open('rb') as f,(dest/name).open('xb') as g:shutil.copyfileobj(f,g)
   assert sha(dest/name)==sha(old/run/name)
  dump(dest/'config.json',config)
  changes[run]=dict(original_config_file_sha256=sha(old/run/'config.json'),final_config_file_sha256=sha(dest/'config.json'),added_tier=3,model_identity_representation_only=True,actual_existing_contract_recipe=recipe)
 with (old/'MATH_ENDPOINT.json').open('rb') as f,(out/'MATH_ENDPOINT.json').open('xb') as g:shutil.copyfileobj(f,g)
 dump(out/'ORIGINAL_COMPLETED.json',summary);dump(out/'ORIGINAL_PREPARATION_MANIFEST.json',read(old/'MANIFEST.json'))
 dump(out/'METADATA_FINALIZATION.json',dict(utc=utc(),changes=changes,source_sha256=sha(__file__),original_preparation_r1_preserved=True,failed_finalizer_preserved=True,new_schedule_builds=0,new_encodings=0,new_model_calls=0))
 dump(out/'COMPLETED.json',dict(**summary,metadata_finalization_utc=utc(),literal_tier_field=3,old_original_contract_validated=True,original_preparation_unmodified=True))
 dump(out/'MANIFEST.json',manifest(out));return dict(cells=list(changes),new_schedule_builds=0,new_encodings=0,new_model_calls=0)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);print(json.dumps(execute(p.parse_args().root)))
