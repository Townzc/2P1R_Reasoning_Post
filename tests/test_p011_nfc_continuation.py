import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from transformers import AutoTokenizer

from experiments.p011 import native_nfc_encoding as encoding
from scripts import prepare_p011_ot3_nfc_continuation as continuation


class NativeNFC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = AutoTokenizer.from_pretrained(
            '.local/exploratory_20261014/r1/inputs/instruct_model',
            local_files_only=True,trust_remote_code=False,use_fast=True)

    def check_case(self,q,a,changed):
        row,proof=encoding.encode_complete(self.tok,q,a,'synthetic')
        prefix,raw=encoding.rules.native_text(self.tok,q,a)
        parts=(prefix,a+'<|im_end|>','\n')
        original_ids=sum([self.tok(p,add_special_tokens=False,truncation=False)['input_ids']
                          for p in parts],[])
        self.assertEqual(row['input_ids'],original_ids)
        self.assertEqual(proof['normalization_changed_text'],changed)
        self.assertFalse(proof['raw_text_rewritten'])
        self.assertEqual(row['labels'][-1],-100)
        self.assertEqual(row['labels'][row['assistant_end']-1],151645)
        return row,proof,raw

    def test_decomposed_bar_preserves_native_ids(self):
        _,proof,raw=self.check_case('Define a symbol.','Let a\u0304 = 2. \\boxed{2}',True)
        self.assertEqual(proof['raw_characters']-proof['normalized_characters'],1)
        self.assertIn('a\u0304',raw)

    def test_decomposed_question_preserves_prompt_mask(self):
        row,_,_=self.check_case('Cafe\u0301?', '\\boxed{1}',True)
        self.assertEqual(row['labels'][:row['assistant_start']],[-100]*row['assistant_start'])

    def test_no_NFKC_or_whitespace_cleanup(self):
        self.check_case('Ａ ①?', '\n  \\boxed{①}\n',False)

    def test_precomposed_original_remains_exact(self):
        self.check_case('Symbol ā?', '\\boxed{ā}',False)

    def test_non_NFC_tokenizer_rejected(self):
        tok=copy.deepcopy(self.tok)
        from tokenizers import normalizers
        tok.backend_tokenizer.normalizer=normalizers.NFKC()
        with self.assertRaisesRegex(ValueError,'NFC normalizer'):
            encoding.encode_complete(tok,'a','b','x')

    def test_other_decode_change_rejected(self):
        with patch.object(self.tok,'decode',return_value='different'):
            with self.assertRaisesRegex(ValueError,'beyond pinned NFC'):
                encoding.encode_complete(self.tok,'a','b','x')

    def test_original_limit_still_enforced(self):
        with patch.object(encoding.rules,'MAX_TOTAL_TOKENS',3):
            with self.assertRaisesRegex(ValueError,'original total limit'):
                encoding.encode_complete(self.tok,'a','b','x')


class PrefixAndPartial(unittest.TestCase):
    def fixture(self,directory):
        rows={};raw=[];enc=[]
        for i in range(10080):
            key=f'p{i:05}';rows[key]={'path_id':key,'question':'synthetic question','response':'synthetic answer'}
            if i<965:
                raw.append((json.dumps(rows[key],separators=(',',':'))+'\n').encode())
                obj={'path_id':key,'parent_sha256':encoding.rules.identity('synthetic question'),
                     'input_ids':[10,11,151645,198],'labels':[-100,11,151645,-100],
                     'n_processed':4,'n_supervised':2,'assistant_start':1,'assistant_end':3,
                     'eos_token_id':151645,'template_final_newline_supervised':False}
                enc.append((json.dumps(obj)+'\n').encode())
        (directory/'SELECTED_RAW.jsonl').write_bytes(b''.join(raw))
        (directory/'ENCODED.jsonl').write_bytes(b''.join(enc))
        return rows,raw,enc

    def test_original_bytes_reused_without_tokenizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);rows,raw,enc=self.fixture(p)
            with patch.object(encoding,'encode_complete',side_effect=AssertionError('reencode')):
                a,b,s=continuation.confirm_prefix(p,rows)
            self.assertEqual(a,raw);self.assertEqual(b,enc);self.assertEqual(len(s),965)

    def test_changed_prefix_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);rows,_,_=self.fixture(p);rows['p00000']['response']='changed'
            with self.assertRaisesRegex(ValueError,'identity/raw differs'):continuation.confirm_prefix(p,rows)

    def test_partial_last_line_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);rows,_,enc=self.fixture(p);(p/'ENCODED.jsonl').write_bytes(b''.join(enc)[:-1])
            with self.assertRaisesRegex(ValueError,'partial original line'):continuation.confirm_prefix(p,rows)

    def test_changed_mask_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);rows,_,enc=self.fixture(p);x=json.loads(enc[0]);x['labels'][0]=10
            enc[0]=(json.dumps(x)+'\n').encode();(p/'ENCODED.jsonl').write_bytes(b''.join(enc))
            with self.assertRaisesRegex(ValueError,'encoded structure'):continuation.confirm_prefix(p,rows)

    def test_only_next_unconfirmed_attempted_and_failure_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);rows,raw,enc=self.fixture(p);_,_,summary=continuation.confirm_prefix(p,rows)
            with patch.object(encoding,'encode_complete',side_effect=ValueError('new diagnostic failure')) as call:
                with self.assertRaisesRegex(ValueError,'new diagnostic failure'):
                    continuation.append_remaining(rows,summary,object(),p)
                self.assertEqual(call.call_count,1);self.assertEqual(call.call_args.args[-1],'p00965')
            self.assertEqual((p/'SELECTED_RAW.jsonl').read_bytes(),b''.join(raw))
            self.assertEqual((p/'ENCODED.jsonl').read_bytes(),b''.join(enc))
            self.assertTrue((p/'NATIVE_NORMALIZATION.jsonl').exists())


if __name__=='__main__':unittest.main()
