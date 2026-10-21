"""New admission/transport integration fixtures; no original science inputs."""
from pathlib import Path
import copy
import hashlib
import io
import json
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.p011 import c1_admission as a,c1_artifacts as art,c1_execution as c,c1_nll
from experiments.sft_allocation_midpoint.common import dump,sha,digest
# Fixtures only: no old TestCase or old test method imported/executed.
from tests.test_p011_c1_execution_draft import spec,roster,forward,Store


class C1AdmissionArtifactsDraftTests(unittest.TestCase):
    def test_failed_pending_unknown_unmatched_accounting(self):
        records=[{'logical_id':'old1','app_id':'ap-stopped','budget':{'category':'C','new_reserved_usd':'2'}},
                 {'logical_id':'old2','app_id':'ap-unknown','budget':{'category':'B','new_reserved_usd':'3'}},
                 {'logical_id':'pending','budget':{'category':'A','new_reserved_usd':'1'}}]
        totals,slots=a.accounting(records,[{'app_id':'ap-other'}],{'ap-stopped':'stopped'})
        self.assertEqual(totals['C'],'2');self.assertEqual(totals['B'],'3');self.assertEqual(slots,3)

    def test_duplicates_and_category_transfer_refused(self):
        x={'logical_id':'x','app_id':'ap-x','budget':{'category':'C','new_reserved_usd':'1'}}
        with self.assertRaises(ValueError):a.accounting([x,x],[],{})
        y=copy.deepcopy(x);y['logical_id']='y'
        with self.assertRaises(ValueError):a.accounting([x,y],[],{})
        x['budget']['new_reserved_usd']='12.01'
        with self.assertRaises(ValueError):a.accounting([x],[],{})

    def budget(self,root):
        dump(root/'meter.json',{'synthetic_only':True});s=spec();s['task_inventory']={'journal_chunks':2}
        b={'observed_epoch':time.time(),'all_attempted_reservations_usd':{k:'0' for k in a.CAPS},
           'cap_usd':'12','category':'C','overall_cap_usd':'180','protected_usd':'48',
           'reserve_release_used':False,'owner_estimate_used_as_balance':False,
           'availability_basis':'delayed_gross_plus_retained_reserves_conservative_floor',
           'source_evidence_files':{'meter.json':sha(root/'meter.json')},
           'available_after_retained_prior_reserves_usd':'50','observed_gross_resource_usd':'300'}
        return s,b

    def test_fresh_budget_and_protected_floor(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s,b=self.budget(root)
            result=a.fresh_budget(s,b,[],[],{},time.time(),root)
            self.assertEqual(result['new_reserved_usd'],'1.95')
            b['available_after_retained_prior_reserves_usd']='49.94'
            with self.assertRaises(ValueError):a.fresh_budget(s,b,[],[],{},time.time(),root)

    def test_unknown_four_slots_stale_or_changed_meter_block(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s,b=self.budget(root);now=time.time()
            with self.assertRaises(ValueError):a.fresh_budget(s,b,[],[{}]*4,{},now,root)
            with self.assertRaises(ValueError):a.fresh_budget(s,b,[],[],{},now+3601,root)
            b['source_evidence_files']['meter.json']='0'*64
            with self.assertRaises(ValueError):a.fresh_budget(s,b,[],[],{},now,root)

    def test_shared_C1_review_exact_scope_and_binding(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=spec();s.update({'source_files':{'synthetic.py':'a'*64},
                'input_files':{'original.json':{'sha256':'b'*64,'bytes':9}},
                'original_group_binding_sha256':'c'*64,'task_inventory':{'journal_chunks':2}})
            dump(root/'spec.json',s);(root/'report.md').write_text('synthetic only, not an acceptance')
            review={'decision':'PASS','target_commit':'d'*40,'local_report_path':str(root/'report.md'),
                'report_sha256':sha(root/'report.md'),'scope':a.SCOPE,'original_plan_commit':a.PLAN,
                'spec_sha256':sha(root/'spec.json'),'source_files':s['source_files'],
                'input_files':s['input_files'],'original_group_binding_sha256':s['original_group_binding_sha256'],
                'task_inventory_sha256':digest(s['task_inventory']),'timing_sha256':digest(s['timing']),
                'measurement_exceptions':0}
            for k in ('complete_input_A1_accepted','complete_source_closure_accepted','exact_timing_scope_accepted',
                      'original_tokens_masks_and_EOS_unchanged','untouched_base_forward_only',
                      'full_result_window_and_budget_accepted'):review[k]=True
            self.assertNotIn('local_report_path',a.reviewed_path(s,root/'spec.json',review))
            review['input_files']={}
            with self.assertRaises(ValueError):a.reviewed_path(s,root/'spec.json',review)

    def test_exact_source_changed_or_unsafe(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'x.py').write_text('# synthetic\n');s={'source_files':{'x.py':sha(root/'x.py')}}
            a.exact_source(s,root);(root/'x.py').write_text('# changed\n')
            with self.assertRaises(ValueError):a.exact_source(s,root)
            with self.assertRaises(ValueError):a.exact_source({'source_files':{'../x.py':'0'*64}},root)

    def complete(self,root):
        s=spec();tasks,members=roster(3);claim={'id':'synthetic'};records=Store({'c1/claim':claim})
        out=root/'payload';start=time.time();basis={'synthetic':True}
        def loader(s,out,deadline):
            dump(out/'MODEL_LOADED.json',{'model':s['model'],'forward':s['forward'],
                'optimizer_created':False,'adapter_loaded':False,'new_tokenization':False});return object()
        with patch.object(c1_nll,'forward_one',side_effect=forward):
            c.run_body(s,tasks,members,out,basis,records,'c1',claim,lambda:None,start,start+900,0,loader)
        artifact=art.pack(out)
        receipt={'status':'completed','app_id':'ap-synthetic','spec_sha256':digest(s),'claim':claim,
                 'worker_start_epoch':start,'finished_epoch':time.time(),'artifact':artifact}
        records['c1/terminal']=copy.deepcopy(receipt)
        provider={'app_id':'ap-synthetic','state':'stopped','owned_containers':0,'observed_epoch':time.time()}
        return s,tasks,members,claim,records,out,basis,receipt,provider

    def test_full_new_pack_extract_readonly_completion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s,tasks,members,claim,records,out,basis,receipt,provider=self.complete(root)
            extracted=root/'extracted';art.extract(out/'evidence.tar.gz',extracted,receipt['artifact'])
            with patch.object(c1_nll,'forward_one',side_effect=AssertionError('no new forward')), \
                 patch.object(c1_nll,'descriptive_summary',side_effect=AssertionError('no recompute')):
                proof=art.check_complete(s,receipt,provider,records,'c1',claim,extracted,tasks,members,basis)
            self.assertTrue(proof['receipt_verified']);self.assertFalse(proof['statistics_recomputed'])
            with self.assertRaises(ValueError):art.pack(out)
            with self.assertRaises(FileExistsError):art.extract(out/'evidence.tar.gz',extracted,receipt['artifact'])

    def test_provider_unknown_owned_container_and_changed_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            s,tasks,members,claim,records,out,basis,receipt,provider=self.complete(Path(d))
            for k,v in [('state','unknown'),('owned_containers',1),('owned_containers',False),('app_id','ap-wrong')]:
                bad={**provider,k:v}
                with self.assertRaises(ValueError):art.original_completion(s,receipt,bad,records,'c1',claim)
            receipt['finished_epoch']+=901
            with self.assertRaises(ValueError):art.original_completion(s,receipt,provider,records,'c1',claim)

    def test_archive_traversal_duplicate_or_link_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for n,mode in enumerate(('traversal','duplicate','symlink')):
                archive=root/f'{n}.tar.gz';name='../escape.json' if mode=='traversal' else 'x.json';raw=b'{}'
                with tarfile.open(archive,'w:gz') as tar:
                    obj=tarfile.TarInfo(name);obj.size=len(raw)
                    if mode=='symlink':obj.type=tarfile.SYMTYPE;obj.linkname='../outside';obj.size=0
                    tar.addfile(obj,io.BytesIO(raw) if mode!='symlink' else None)
                    if mode=='duplicate':tar.addfile(obj,io.BytesIO(raw))
                artifact={'members':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':2}},
                    'members_file_sha256':'0'*64,'tar_sha256':sha(archive),'tar_bytes':archive.stat().st_size}
                out=root/f'out{n}'
                with self.assertRaises(ValueError):art.extract(archive,out,artifact)
                self.assertFalse(out.exists())

    def test_failed_payload_never_packed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dump(root/'ALL_CONFIRMED.json',{});dump(root/'FAILED.json',{'synthetic':True})
            with self.assertRaises(ValueError):art.pack(root)
            self.assertFalse((root/'evidence.tar.gz').exists())


if __name__=='__main__':unittest.main()
