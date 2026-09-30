"""Authored evidence/admission checks; never execute a model-generated program."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from experiments.q2_supervision_migration.screen_scoring import score_pair
from experiments.q2_supervision_migration.screen_runtime import parse

class CompletionIntegrationTests(unittest.TestCase):
    def problem(self):
        return {'base_input':[[1]],'plus_input':[[2]],'entry_point':'fixture','atol':0}
    def reference(self):
        return {'base':[1],'plus':[2],'base_time':[.01],'plus_time':[.01]}
    def test_known_verdicts_never_invoke_repair(self):
        def forbidden(*a,**k): raise AssertionError('repair called for known verdict')
        with patch.dict('sys.modules',{'experiments.q2_supervision_migration.scoring_guard_v2':SimpleNamespace(diagnose_timeout=forbidden)}):
            for status in ['pass','fail']:
                result=score_pair(self.problem(),self.reference(),'authored inert text',lambda *a,**k:(status,[status=='pass']),fast_check=True,guarded_scoring_v2=True)
                self.assertEqual([result[k]['status'] for k in ['base','extra']],[status]*2)
    def test_unresolved_recovery_is_not_converted_to_reward(self):
        fake=SimpleNamespace(diagnose_timeout=lambda *a,**k:{'verified_suite_verdict':None,'observed':[],'prefix_consistent':False})
        with patch.dict('sys.modules',{'experiments.q2_supervision_migration.scoring_guard_v2':fake}):
            result=score_pair(self.problem(),self.reference(),'authored inert text',lambda *a,**k:('timeout',[]),fast_check=True,guarded_scoring_v2=True)
        self.assertEqual([result[k]['status'] for k in ['base','extra']],['timeout']*2)
    def test_original_known_fail_detail_is_not_rewritten(self):
        result=score_pair(self.problem(),self.reference(),'inert',lambda *a,**k:('fail',[False]),fast_check=True,guarded_scoring_v2=True)
        for value in result.values():
            self.assertEqual(value['status'],'fail')
            self.assertIsNone(json.loads(value['detail'])['initialization_timeout_diagnosis'])

if __name__=='__main__': unittest.main()
