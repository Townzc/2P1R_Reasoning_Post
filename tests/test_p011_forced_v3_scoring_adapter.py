"""New CR8125 regressions only. No old production, tests, model or symbolic calls."""
import unittest
from experiments.p011.forced_answer import (
    decode_continuation, forced_request, forced_sampling, digest, original_digest)
from experiments.learning_regime_p009.math_scoring import decide, last_box


class Tokenizer:
    all_special_ids = [900, 901]

    def get_vocab(self):
        return {chr(i):i for i in range(32, 127)} | {'EOS':900, 'BAD':901}

    def decode(self, ids, **kwargs):
        return ''.join(chr(i) for i in ids)


class ForcedV3Regressions(unittest.TestCase):
    def continuation(self, text, ending='eos', special_after=None):
        ids = list(map(ord, text))
        if ending == 'eos':
            ids.append(900)
        elif ending == 'cap':
            ids += [ord(' ')] * (64-len(ids))
        elif ending == 'invalid':
            ids.append(901)
            ids += list(map(ord, special_after or ''))
        request = {'id':'math500:0000:sample:0','prompt_token_ids':[32]*16400}
        item = {'id':request['id'],'request_sha256':digest(request),
            'prompt_token_ids':request['prompt_token_ids'],'sampling':forced_sampling([900]),
            'answers':[{'token_ids':ids,'backend_text':text,
                'finish_reason':'length' if ending=='cap' else 'stop',
                'stop_reason':None if ending=='cap' else ids[-1]}]}
        return decode_continuation(request,item,[900],Tokenizer(),1000)

    def test_closed_at_cap_scores_correct_without_claiming_actual_eos(self):
        value = self.continuation('42} trailing', 'cap')
        self.assertEqual(value['answer_segment'], '\\boxed{42}')
        self.assertEqual(value['native_stop_reason'], 'length_cap')
        self.assertEqual(value['backend_finish_reason'], 'length')
        self.assertEqual(value['forced_box_completion_category'], 'closed_without_native_eos')
        self.assertTrue(decide('42',last_box(value['answer_segment']),{'status':'parse_failure'},
            stop_reason=value['stop_reason'])['correct'])

    def test_later_box_cannot_replace_the_forced_answer(self):
        value = self.continuation('41} then \\boxed{42}', 'cap')
        self.assertEqual(value['answer_segment'], '\\boxed{41}')
        self.assertEqual(last_box(value['answer_segment'])['answer'], '41')

    def test_nested_and_escaped_braces_close_at_forced_outer_boundary(self):
        for text, expected in [
                ('\\frac{1}{2}} tail','\\boxed{\\frac{1}{2}}'),
                ('\\{1,2\\}} tail','\\boxed{\\{1,2\\}}')]:
            value = self.continuation(text)
            self.assertEqual(value['answer_segment'], expected)
            self.assertEqual(value['forced_box_completion_category'], 'closed_with_native_eos')

    def test_unclosed_outer_box_cannot_backfill_inner_box_even_with_eos(self):
        for ending in ('eos','cap'):
            value = self.continuation('unclosed \\boxed{42}',ending)
            self.assertFalse(value['forced_box_closed'])
            self.assertEqual(value['forced_box_completion_category'],'forced_box_unclosed')
            self.assertFalse(decide('42',last_box(value['answer_segment']),{},
                stop_reason=value['stop_reason'])['correct'])

    def test_invalid_special_before_closure_blocks_answer_but_after_does_not(self):
        bad = self.continuation('42','invalid',special_after='}')
        good = self.continuation('42}','invalid')
        self.assertFalse(bad['forced_box_closed'])
        self.assertEqual(bad['stop_reason'],'invalid_special_token')
        self.assertTrue(good['forced_box_closed'])
        self.assertEqual(good['native_stop_reason'],'invalid_special_token')
        self.assertEqual(good['stop_reason'],'native_eos')

    def test_native_eos_at_old_cap_and_invalid_special_are_not_selected(self):
        for stop in ('native_eos','invalid_special_token'):
            raw={'id':'math500:0000:sample:0','request_sha256':'a'*64,
                'prompt_token_ids':[1],'answers':[{'token_ids':[1]*16384,'finish_reason':'length'}]}
            decoded={'id':raw['id'],'raw_record_sha256':original_digest(raw),
                'backend_finish_reason':'length','stop_reason':stop,'unmapped_model_token_ids':[]}
            with self.assertRaises(ValueError):forced_request(raw,decoded,[2])

    def test_native_cap_with_original_unmapped_ids_keeps_literal_context(self):
        raw={'id':'math500:0000:sample:0','request_sha256':'a'*64,
            'prompt_token_ids':[1],'answers':[{'token_ids':[151700]*16384,'finish_reason':'length'}]}
        decoded={'id':raw['id'],'raw_record_sha256':original_digest(raw),
            'backend_finish_reason':'length','stop_reason':'length_cap','unmapped_model_token_ids':[151700]}
        value=forced_request(raw,decoded,[2])
        self.assertEqual(value['prompt_token_ids'],[1]+[151700]*16384+[2])


if __name__ == '__main__':
    unittest.main()
