import copy,unittest
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.contract import run_roster,DEADLINE_EPOCH
from experiments.sft_allocation_p008.audit_binding import validate,validate_label


def fixture():
    rows=run_roster(8,False,2)+[dict(run_id='pool_d1'),dict(run_id='pool_d2'),dict(run_id='base')]
    slots={x['run_id']:{'reserved_cents':100} for x in rows};slots['audit']={'reserved_cents':500}
    source={'test.py':'1'*64};files={'fixture.json':{'bytes':2,'sha256':'2'*64}}
    labels={};meta={}
    for row in rows:
        run=row['run_id'];terminal=dict(status='completed',evidence_sha256=digest(files))
        label=dict(campaign='fixture',run_id=run,config=row,envelope=dict(receipt=terminal,artifact_manifest=files),
            local_oracle=dict(passed=True,artifact_digest=digest(files)))
        labels[run]=label
        meta[run]=dict(campaign='fixture',run_id=run,terminal=terminal,provider_stopped=True,owned_containers=0,label_sha256=digest(label))
    binding=dict(plan=dict(campaign_id='fixture',deadline_epoch=DEADLINE_EPOCH,slots=slots),
      config=dict(run_id='audit',role='audit',max_seconds=3300,readers=2,input_directory='audit_inputs'),
      labels=meta,config_sha256={r:digest(v['config']) for r,v in labels.items()},
      input_manifest={'files':{r+'.json':{} for r in labels}},
      code_review=dict(decision='PASS-WITH-NOTES',scope='p008_cpu_integrity_code',source_files=source,target_commit='a'*40,report_sha256='b'*64))
    spec=dict(status='admitted_after_all_local_oracles_and_resource_release',binding_sha256=digest(binding),source_files=source)
    release=dict(source_files=source,spec_sha256=digest(spec))
    return binding,spec,release,labels


def rebind(binding,spec,release):
    # Adversarial input has consistent outer hashes; semantic gates must still reject it.
    spec['binding_sha256']=digest(binding);release['spec_sha256']=digest(spec)


class AuditBindingTest(unittest.TestCase):
    def test_complete_finite_roster(self):
        b,s,r,labels=fixture();self.assertEqual(len(validate(b,s,r)),21)
        for name,label in labels.items():self.assertEqual(validate_label(b,name,label),label)
    def test_no_pending_or_foreign_code_review(self):
        for field,value in [('decision','pending'),('scope','student_code'),('target_commit','HEAD')]:
            b,s,r,_=fixture();b['code_review'][field]=value;rebind(b,s,r)
            with self.assertRaisesRegex(ValueError,'scoped code review'):validate(b,s,r)
    def test_no_timeout_or_budget_extension(self):
        for field,value in [('max_seconds',6600),('readers',4)]:
            b,s,r,_=fixture();b['config'][field]=value;rebind(b,s,r)
            with self.assertRaisesRegex(ValueError,'CPU audit limits'):validate(b,s,r)
        b,s,r,_=fixture();b['plan']['deadline_epoch']+=1;rebind(b,s,r)
        with self.assertRaisesRegex(ValueError,'deadline'):validate(b,s,r)
    def test_omitted_source_even_with_matching_roster_and_hashes(self):
        b,s,r,_=fixture();run=next(x for x in b['labels'] if x.startswith('d2_'))
        for d in (b['labels'],b['config_sha256'],b['plan']['slots']):d.pop(run)
        b['input_manifest']['files'].pop(run+'.json');rebind(b,s,r)
        with self.assertRaisesRegex(ValueError,'eighteen students'):validate(b,s,r)
    def test_no_running_or_failed_source(self):
        b,s,r,_=fixture();b['labels']['pool_d1']['owned_containers']=1;rebind(b,s,r)
        with self.assertRaisesRegex(ValueError,'resources'):validate(b,s,r)
        b,s,r,_=fixture();b['labels']['pool_d2']['terminal']['status']='failed';rebind(b,s,r)
        with self.assertRaisesRegex(ValueError,'terminal'):validate(b,s,r)
    def test_oracle_must_bind_original_source(self):
        b,s,r,labels=fixture();run='pool_d1';label=labels[run];label['local_oracle']['artifact_digest']='f'*64
        b['labels'][run]['label_sha256']=digest(label)
        with self.assertRaisesRegex(ValueError,'Local oracle'):validate_label(b,run,label)
    def test_config_and_terminal_cannot_be_substituted(self):
        b,s,r,labels=fixture();run='pool_d1';label=copy.deepcopy(labels[run]);label['config']['draw']=2
        b['labels'][run]['label_sha256']=digest(label)
        with self.assertRaisesRegex(ValueError,'input/config'):validate_label(b,run,label)


if __name__=='__main__':unittest.main()
