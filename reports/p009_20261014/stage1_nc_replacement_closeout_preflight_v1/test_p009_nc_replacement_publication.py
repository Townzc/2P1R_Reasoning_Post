"""Synthetic lineage/projection boundaries only, no original science or provider."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import publish_p009_nc_replacement_pair as p


def oracle():
    return dict(passed=True,run_id=p.RUN,updates_verified=1024,targets_verified=2097148,
        outputs_rescored=1319,total=1319,technical_unknown=0,correct=0,
        question_correct={str(i):False for i in range(1319)},state_sha256='a'*64)


def fixture():
    files={'checkpoint_1024/state.pt':{'sha256':'a'*64,'bytes':5}}
    claim=dict(attempt_id='new_attempt',reserved_cents=655)
    terminal=dict(status='completed',run_id=p.RUN,claim_sha256=p.digest(claim),
        attempt_id='new_attempt',evidence_sha256=p.digest(files),actual_cost_cents=655)
    parent=dict(status='failed',evidence_sha256=p.PARENT_FAILURE_DIGEST,actual_cost_cents=655)
    parent_key='midpoint/'+p.PARENT_CAMPAIGN+'/terminal/'+p.PARENT_RUN
    spec=dict(required_records={parent_key:copy.deepcopy(parent)},required_stopped_app_ids=['old_app'])
    sent=dict(run_id=p.RUN,spec=spec,plan={},release={'dispatch_app_id':'new_app'})
    envelope=dict(receipt=terminal,artifact_manifest=files)
    value=oracle();value['artifact_digest']=p.digest(files)
    proof=dict(passed=True,original_failed_parent_retained=True,ledger_sha256='ledger',original_receipt_sha256='receipt')
    provider=dict(app_ids=['old_app','new_app'],state='stopped',owned_container_ids=[],
        owned_containers=[],original_app_info=[])
    ledger={'midpoint/'+p.CAMPAIGN+'/claim/'+p.RUN:claim,
        'midpoint/'+p.CAMPAIGN+'/terminal/'+p.RUN:terminal,parent_key:parent,
        p.dispatch_key(p.RUN):{'new_marker':True},p.logical_key(p.RUN):{'new_marker':True}}
    return [spec,sent,envelope,value,proof,provider,ledger,'receipt','ledger']


class ReplacementPublication(unittest.TestCase):
    def check(self, args):
        with patch.object(p,'validate'),patch.object(p,'marker',return_value={'new_marker':True}),patch.object(p,'validate_stopped_apps'):
            return p.check_lineage(*args)

    def test_exact_full_bool_oracle(self):
        self.assertEqual(p.check_oracle(oracle(),p.RUN,'a'*64)['total'],1319)
        for key,value in [('run_id',p.PARENT_RUN),('updates_verified',896),('technical_unknown',1),('correct',1)]:
            x=oracle();x[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):p.check_oracle(x,p.RUN,'a'*64)

    def test_missing_or_nonbool_is_not_zero(self):
        for values in ({str(i):False for i in range(1318)},{str(i):0 for i in range(1319)}):
            x=oracle();x['question_correct']=values
            with self.assertRaises(ValueError):p.check_oracle(x,p.RUN)

    def test_preserved_third_physical_lineage(self):
        args=fixture();self.assertEqual(self.check(args),['old_app','new_app'])
        key='midpoint/'+p.PARENT_CAMPAIGN+'/terminal/'+p.PARENT_RUN
        args[6][key]['status']='completed'
        with self.assertRaises(ValueError):self.check(args)

    def test_old_failure_cannot_be_dropped(self):
        args=fixture();args[4]['original_failed_parent_retained']=False
        with self.assertRaises(ValueError):self.check(args)
        args=fixture();del args[6]['midpoint/'+p.PARENT_CAMPAIGN+'/terminal/'+p.PARENT_RUN]
        with self.assertRaises((KeyError,ValueError)):self.check(args)

    def test_no_fence_or_receipt_substitution(self):
        args=fixture();args[6][p.logical_key(p.RUN)]={'original_marker':True}
        with self.assertRaises(ValueError):self.check(args)
        args=fixture();args[2]['receipt']['run_id']=p.PARENT_RUN
        with self.assertRaises(ValueError):self.check(args)

    def test_partial_provider_or_tampered_state_rejected(self):
        args=fixture();args[5]['owned_container_ids']=['active']
        with self.assertRaises(ValueError):self.check(args)
        args=fixture();args[3]['state_sha256']='b'*64
        with self.assertRaises(ValueError):self.check(args)

    def test_nested_host_projection_preserves_actual_flags(self):
        original={'release':{'original_release':{'runtime_review':{'local_report_path':'/Users/test/report','decision':'PASS'},
            'budget':{'source_snapshot':'private/snapshot','observed':235.}},
            'parent_disposition_review':{'paired_NC_gate_available':False,'local_report_path':'/Users/test/A4'}}}
        copied=copy.deepcopy(original);projected,removed=p.projection(original)
        self.assertEqual(original,copied);self.assertEqual(len(removed),3)
        self.assertEqual(projected['release']['original_release']['runtime_review'],{'decision':'PASS'})
        self.assertIs(projected['release']['parent_disposition_review']['paired_NC_gate_available'],False)
        self.assertEqual(removed['release.original_release.budget.source_snapshot'],p.digest('private/snapshot'))

    def test_partial_publication_never_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'existing';dest.mkdir();(dest/'PUBLICATION_INTENT.json').write_text('{}')
            with self.assertRaises(ValueError):p.publish('unused',dest,'unused','unused')
            self.assertEqual((dest/'PUBLICATION_INTENT.json').read_text(),'{}')


if __name__=='__main__':unittest.main()
