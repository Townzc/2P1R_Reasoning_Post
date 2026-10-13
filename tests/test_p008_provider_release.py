import copy,subprocess,unittest
from unittest.mock import patch
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps,read_stopped_apps


def infos():
    return [dict(app_id=x,lifecycle=dict(state='stopped',stopped_at='2026-10-13T12:20:00Z')) for x in ('ap-one','ap-two')]


class ExactProviderTests(unittest.TestCase):
    def test_exact_stopped(self):self.assertEqual(validate_stopped_apps(['ap-one','ap-two'],infos(),[]),infos())
    def test_missing_not_stopped(self):
        with self.assertRaises(ValueError):validate_stopped_apps(['ap-one','ap-two'],[],[])
    def test_foreign_id(self):
        x=infos();x[0]['app_id']='ap-other'
        with self.assertRaises(ValueError):validate_stopped_apps(['ap-one','ap-two'],x,[])
    def test_current_containers_block_even_other_app(self):
        with self.assertRaises(ValueError):validate_stopped_apps(['ap-one','ap-two'],infos(),[dict(app_id='ap-other')])
    def test_unknown_or_active_state(self):
        for state in ('running','unknown',''):
            x=infos();x[0]['lifecycle']['state']=state
            with self.assertRaises(ValueError):validate_stopped_apps(['ap-one','ap-two'],x,[])
    def test_missing_stop_time(self):
        x=infos();x[0]['lifecycle']['stopped_at']=None
        with self.assertRaises(ValueError):validate_stopped_apps(['ap-one','ap-two'],x,[])
    def test_api_failure_not_fallback(self):
        with patch('experiments.sft_allocation_p008.provider_release.subprocess.check_output',side_effect=subprocess.CalledProcessError(1,'modal')):
            with self.assertRaises(subprocess.CalledProcessError):read_stopped_apps('modal',['ap-one'],[])
    def test_duplicate_expected_rejected(self):
        with self.assertRaises(ValueError):validate_stopped_apps(['ap-one','ap-one'],[infos()[0],infos()[0]],[])

if __name__=='__main__':unittest.main()
