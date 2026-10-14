"""New saved-batch proof fixtures, no generation/model call."""
import copy
import unittest
from transformers import AutoTokenizer
from analyses.e017_stopping import prediction
from experiments.sft_exploratory_20261014.runtime import reference_event,audit_batch


class BatchProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok=AutoTokenizer.from_pretrained('.local/exploratory_20261014/r1/metadata',local_files_only=True)
    def fixture(self):
        row={'problem_id':'fixture','prompt':'one plus one','answer':'2'}
        tokens=self.tok('\\boxed{2}',add_special_tokens=False)['input_ids']+[151643]
        event=reference_event(tokens,self.tok,[151643,151645]);p=[{'problem_id':'fixture','input_ids':[1,2]}]
        record=prediction(row,self.tok,tokens,event,1.,0,2)
        raw=dict(problem_ids=['fixture'],input_ids=[[1,2]],prompt_width=2,batch_output_ids=[tokens],events=[event],seconds=1.)
        return raw,[record],[row],p
    def test_original_alternate_eos_batch(self):
        self.assertTrue(audit_batch(*self.fixture(),self.tok,[151643,151645]))
    def test_prompt_or_score_or_metadata_mutation(self):
        for field in ('score','prompt','width','missing_event','padding'):
            raw,records,rows,p=self.fixture()
            if field=='score':records[0]['task_score']['task_answer_correct']=False
            if field=='prompt':raw['input_ids']=[[2,1]]
            if field=='width':records[0]['padded_prompt_width']=3
            if field=='missing_event':raw['events']=[]
            if field=='padding':records[0]['post_stop_padding_tokens']=1
            with self.assertRaises(ValueError):audit_batch(raw,records,rows,p,self.tok,[151643,151645])


if __name__=='__main__':unittest.main()
