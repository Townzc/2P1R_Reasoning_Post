import ast,copy,unittest
from pathlib import Path
from tests.test_p008_student_binding import prepared
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.pool_lineage import validate_pool_lineages,PARENT_CAMPAIGN,CHILD_CAMPAIGN,CHILD_RUN
from experiments.sft_allocation_p008.lineage_student_binding import validate_student_binding


def item(campaign,run,status):
    claim=dict(intent_sha256='1'*64,plan_sha256='2'*64,attempt_id=run)
    return dict(campaign=campaign,run_id=run,claim=claim,terminal=dict(status=status,claim_sha256=digest(claim),evidence_sha256='3'*64))


def fixture():
    a=prepared();plan,cfg,release,spec=a
    one=item(PARENT_CAMPAIGN,'pool_d1','completed')
    parent=item(PARENT_CAMPAIGN,'pool_d2','failed');child=item(CHILD_CAMPAIGN,CHILD_RUN,'completed')
    proof=dict(passed=True,parent_plus_child_redecoded=True,all_wallets_replayed=True,parent_status='failed',child_status='completed',
               parent_physical_outputs=3992,physical_outputs=4992,child_physical_outputs=1000,parent_terminal=parent['terminal'],
               child_terminal=child['terminal'],parent_reconciliation_sha256='a'*64)
    lineages={'1':dict(kind='completed_original',local_oracle_sha256='b'*64,original=one),
              '2':dict(kind='failed_parent_completed_child',merged_oracle_sha256='c'*64,parent=parent,child=child,
                       parent_reconciliation_sha256='a'*64,merged_proof=proof)}
    spec['pool_lineages']=lineages
    records=validate_pool_lineages(lineages,spec['draw_local_oracle_sha256'])
    g=release['gates'];g['pool_terminals']=records;g['pool_lineage_sha256']=digest(lineages)
    g['required_terminals']=[x for x in g['required_terminals'] if x['campaign'].startswith('p008-phase0-')]+records
    rehash(a);return a


def rehash(a):
    _,_,release,spec=a;release['spec_sha256']=digest(spec);release['gates']['runtime_review']['spec_sha256']=digest(spec)
    release['gates']['pool_lineage_sha256']=digest(spec['pool_lineages'])


class LineageStudentTests(unittest.TestCase):
    def test_true_failed_parent_plus_child(self):self.assertTrue(validate_student_binding(*fixture()))
    def test_parent_cannot_be_relabelled(self):
        a=fixture();a[3]['pool_lineages']['2']['parent']['terminal']['status']='completed';rehash(a)
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_missing_child_or_original_draw(self):
        for draw in ('1','2'):
            a=fixture();del a[3]['pool_lineages'][draw];rehash(a)
            with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_different_claim_rejected_even_rehashed(self):
        a=fixture();a[3]['pool_lineages']['2']['child']['claim']['attempt_id']='other';rehash(a)
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_merged_raw_and_full_wallet_checks_mandatory(self):
        for name in ('passed','parent_plus_child_redecoded','all_wallets_replayed'):
            a=fixture();a[3]['pool_lineages']['2']['merged_proof'][name]=False;rehash(a)
            with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_parent_outputs_not_counted_as_new(self):
        a=fixture();a[3]['pool_lineages']['2']['merged_proof']['child_physical_outputs']=4992;rehash(a)
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_old_draw_oracle_is_not_merged_G1(self):
        a=fixture();a[3]['pool_lineages']['2']['merged_oracle_sha256']='d'*64;rehash(a)
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_failure_terminal_cannot_be_omitted(self):
        a=fixture();a[2]['gates']['required_terminals']=[x for x in a[2]['gates']['required_terminals'] if x['terminal']['status']!='failed']
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_different_completed_child_cannot_substitute(self):
        a=fixture();a[2]['gates']['pool_terminals']=copy.deepcopy(a[2]['gates']['pool_terminals']);a[2]['gates']['pool_terminals'][-1]['terminal']['evidence_sha256']='f'*64
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_exact_new_source_review_still_required(self):
        a=fixture();a[2]['gates']['runtime_review']['source_files']={'old.py':'a'*64}
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_joint_target_input_and_scientific_dose_not_waived(self):
        for field in ('targets','updates','seed'):
            a=fixture();a[1][field]+=1;a[3]['config_sha256'][a[1]['run_id']]=digest(a[1]);rehash(a)
            with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_oracle_scientific_body_unchanged(self):
        def function(path):return next(x for x in ast.parse(Path(path).read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='audit')
        self.assertEqual(ast.dump(function('scripts/audit_p008_student.py')),ast.dump(function('scripts/audit_p008_student_lineage.py')))
    def test_worker_scientific_execute_and_block_journal_unchanged(self):
        paths=['experiments/sft_allocation_p008/modal_students.py','experiments/sft_allocation_p008/modal_students_lineage.py']
        calls=[]
        for p in paths:
            tree=ast.parse(Path(p).read_text());calls.append([ast.dump(x) for x in ast.walk(tree) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id in ('execute','BlockTrainingJournal')])
        self.assertEqual(*calls)

if __name__=='__main__':unittest.main()
