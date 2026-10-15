"""One structural failed-prefix audit; no model/state load/score or remote call."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
sys.path.insert(0,'.')
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
R=Path('.local/p009_20261014/r1');N=R/'stage1_nc_r1';F=N/'failed_nc3200_preservation_r1';E=F/'evidence'
OUT=F/'LOCAL_PREFIX_AUDIT.json';RUN='nc_s17_n3200'
def main():
 if OUT.exists():raise ValueError('Original failed prefix already checked; no rerun')
 p=read(F/'PRESERVED.json');db=read(F/'ledger.json');sent=read(E/'intent.json');spec=sent['spec']
 if (p['passed'] is not True or p['run_id']!=RUN or p['original_terminal']['status']!='failed'
     or p['saved_checkpoint_or_weight_files'] or p['output_raw_files']):raise ValueError('Require original failed no-state/no-endpoint evidence')
 a={x.stem:read(x) for x in (E/'intents').glob('*.json')};d={x.stem:read(x) for x in (E/'completed').glob('*.json')}
 inputs=R/'stage1_nc_inputs_r1';rows,encoded,plan,cfg=[read(inputs/('nc17_n3200_'+k+'.json')) for k in ('rows','encoded','plan','config')]
 recipe=read(E/'recipe.json');identity=recipe['identity'];pre='midpoint/'+spec['campaign']+'/'
 if (sent['run_id']!=RUN or identity['run_id']!=RUN or identity['config']!=cfg
     or identity['source_files']!=spec['source_files'] or identity['spec_sha256']!=digest(spec)
     or recipe['schedule']!=plan['updates'] or recipe['lrs']!=plan['lrs']
     or set(a)!=set(d) or db[pre+'terminal/'+RUN]!=p['original_terminal']):
  raise ValueError('Original source/failed claim/recipe/known unit identities differ')
 count=p['continuous_saved_updates'];targets=processed=0
 for step,indices in enumerate(plan['updates'][:count],1):
  k=f'update_{step:04d}';value=dict(step=step,indices=indices,lr=plan['lrs'][step-1],
   supervised_tokens=sum(encoded[i]['n_supervised'] for i in indices),processed_tokens=sum(encoded[i]['n_processed'] for i in indices))
  targets+=value['supervised_tokens'];processed+=value['processed_tokens']
  if (a[k]!=value or any(d[k].get(n)!=v for n,v in value.items())
      or d[k]['cumulative_targets']!=targets or d[k]['cumulative_processed']!=processed):
   raise ValueError('Saved known update/indices/LR/dose metadata differs')
 blocks={f'training_block_{i:04d}_{i+15:04d}' for i in range(1,count+1,16)}
 if count%16 or set(d)!=blocks|{f'update_{i:04d}' for i in range(1,count+1)}:
  raise ValueError('Unexpected/unknown original saved units')
 for k in blocks:
  if db.get(pre+RUN+'/done/'+k)!=d[k] or db.get(pre+RUN+'/unit/'+k)!=a[k]:raise ValueError('Original immutable block unit/ack differs')
 forecasts=sorted(x.name for x in (E/'training_forecasts').glob('*.json'));timings=sorted(x.name for x in (E/'training_timings').glob('*.json'))
 value=dict(passed_saved_record_structure=True,run_id=RUN,terminal_status='failed',
  source_sha256=sha(__file__),preservation_sha256=sha(F/'PRESERVED.json'),
  continuous_saved_updates=count,completed_block_acknowledgements=len(blocks),
  known_saved_target_tokens=targets,known_saved_processed_tokens=processed,
  known_intents=len(a),known_completed_records=len(d),unmatched_saved_intents=0,
  original_full_dose_required_updates=1024,original_full_dose_required_targets=2097148,
  full_training_complete=False,checkpoint_or_weight_files=0,resumable_checkpoint_present=False,
  saved_endpoint_outputs=0,full_state_or_raw_oracle_performed=False,
  forecasts_saved=len(forecasts),complete_block_timing_records_saved=len(timings),
  last_block_timing_not_completed=len(timings)!=len(blocks),
  unknown_lost_in_memory_state_not_reconstructed=True,original_failed_parent_unchanged=True,
  new_model_calls=0,new_scoring=0,utc=datetime.now(timezone.utc).isoformat())
 dump(OUT,value);print(json.dumps(value))
if __name__=='__main__':main()
