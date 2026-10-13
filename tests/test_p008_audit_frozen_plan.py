"""New pure CPU fixtures: exact frozen bytes, no inference or old oracle rerun."""
import copy
import json
from pathlib import Path
import unittest
from experiments.sft_allocation_p008.audit_frozen_plan import checked_plan, check_state_trajectory


def fixture(physical='d1_b1_p4_breadth_t1'):
    root=Path('reports/p008_20261013/student_admission_v1')
    spec=json.loads((root/'ADMISSION.json').read_text())
    logical=physical.removesuffix('_replacement_r1')
    science=spec['configs'][logical]
    cfg=dict(science)
    identity=dict(config=science)
    if physical != logical:
        cfg.update(run_id=physical,logical_run_id=logical)
        identity['physical_run_id']=physical
    inputs=root/'inputs'
    # Only immutable input files are read. No previous model output is rescored.
    raw_plan=(inputs/cfg['plan_file']).read_text()
    plan=json.loads(raw_plan)
    label=dict(config=cfg,run_id=physical,original_student_spec=spec,
        frozen_input_bytes=dict(manifest_json=(inputs/'manifest.json').read_text(),plan_json=raw_plan))
    recipe=dict(identity=identity,schedule=plan['updates'],lrs=list(plan['lrs']))
    return label,recipe,plan


class FrozenPlanAudit(unittest.TestCase):
    def test_original_exact_plan(self):
        label,recipe,plan=fixture()
        self.assertEqual(checked_plan(label,recipe),plan)

    def test_distinct_replacement_uses_unchanged_logical_plan(self):
        label,recipe,plan=fixture('d1_b1_p0_breadth_t1_replacement_r1')
        self.assertEqual(checked_plan(label,recipe),plan)

    def test_frozen_lr_change_rejected(self):
        label,recipe,plan=fixture();plan['lrs'][42]+=1e-12
        label['frozen_input_bytes']['plan_json']=json.dumps(plan)
        with self.assertRaises(ValueError):checked_plan(label,recipe)

    def test_manifest_encoding_change_rejected(self):
        label,recipe,_=fixture();label['frozen_input_bytes']['manifest_json']+=' '
        with self.assertRaises(ValueError):checked_plan(label,recipe)

    def test_rehashed_science_amendment_rejected(self):
        label,recipe,_=fixture();label['original_student_spec']['configs'][label['run_id']]['targets']+=1
        with self.assertRaises(ValueError):checked_plan(label,recipe)

    def test_replacement_cannot_hide_physical_identity(self):
        label,recipe,_=fixture('d1_b1_p0_depth_t1_replacement_r1')
        del recipe['identity']['physical_run_id']
        with self.assertRaises(ValueError):checked_plan(label,recipe)

    def test_changed_schedule_rejected(self):
        label,recipe,_=fixture();recipe['schedule']=copy.deepcopy(recipe['schedule'])
        recipe['schedule'][0][0]+=1
        with self.assertRaises(ValueError):checked_plan(label,recipe)

    def test_recipe_cannot_disagree_with_frozen_lr(self):
        label,recipe,_=fixture();recipe['lrs'][42]+=1e-12
        with self.assertRaises(ValueError):checked_plan(label,recipe)

    def test_state_checks_frozen_vector_not_local_cosine(self):
        label,recipe,plan=fixture();checked_plan(label,recipe)
        state=dict(step=256,cursor=256,schedule=plan['updates'],lrs=list(plan['lrs']))
        self.assertTrue(check_state_trajectory(state,recipe,plan,256))
        state['lrs'][42]+=1e-12
        with self.assertRaises(ValueError):check_state_trajectory(state,recipe,plan,256)

    def test_forensic_cursor_mismatch_rejected(self):
        label,recipe,plan=fixture('d1_b8_p0_breadth_t8');checked_plan(label,recipe)
        state=dict(step=1024,cursor=1023,schedule=plan['updates'],lrs=plan['lrs'])
        with self.assertRaises(ValueError):check_state_trajectory(state,recipe,plan,1024)


if __name__=='__main__':unittest.main()
