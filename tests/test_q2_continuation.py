import json
from pathlib import Path
import tempfile
import unittest
from experiments.q2_supervision_migration import screen_continue as sc
from experiments.q2_supervision_migration.gpu_profile import ProfileError

class ContinuationTests(unittest.TestCase):
    def test_original_deadline_is_not_renewed(self):
        intent={'provider_deadline_epoch':2000,'worker_deadline_epoch':1300}
        self.assertEqual(sc.inherited_deadline(intent,2000,1200),1300)
        for provider,now in [(2001,1200),(2000,1300),(2000,1400)]:
            with self.assertRaises(ProfileError):sc.inherited_deadline(intent,provider,now)
    def test_reserved_shutdown_margin(self):
        with self.assertRaises(ProfileError):sc.inherited_deadline({'provider_deadline_epoch':2000,'worker_deadline_epoch':1500},2000,1200)
    def test_cannot_replay_any_attempted_future_or_eval(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'screen_intent.json').write_text(json.dumps({'plan_sha256':'a'}))
            (root/'screen_failure.json').write_text(json.dumps({'phase':'C_prefix'}))
            (root/'W_future').mkdir()
            with self.assertRaisesRegex(ProfileError,'already attempted'):sc.validate_old(root,'a')
    def test_no_c_retry_in_queue(self):
        self.assertEqual(sc.PHASES,('W_future','R_future','eval_R','eval_W_prefix','eval_W_future','eval_R_future'))

if __name__=='__main__':unittest.main()
