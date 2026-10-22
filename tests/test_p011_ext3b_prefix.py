import io
import json
from pathlib import Path
import tempfile
import unittest
from experiments.p011.ext3b_contract import prefix_metadata
from experiments.p011.data_contract import whole_schedule
from scripts.prepare_p011_ext3b_inputs import copy_prefix


def roster(n=12096):
    return [{'path_id':str(i),'parent_sha256':str(i),'n_supervised':1,'n_processed':2} for i in range(n)]


class RevisedPrefix(unittest.TestCase):
    def test_exact_prefix_and_nested_answers(self):
        rows=roster();large,small=prefix_metadata(rows)
        self.assertEqual(large,rows[:9072]);self.assertEqual(small,large[:3024])
        self.assertIs(large[0],rows[0])

    def test_duplicate_or_wrong_original_count_refused(self):
        with self.assertRaises(ValueError):prefix_metadata(roster(9072))
        rows=roster();rows[-1]=rows[0]
        with self.assertRaises(ValueError):prefix_metadata(rows)

    def test_prefix_bytes_preserved_and_old_tail_not_read(self):
        rows=roster(2);lines=[(json.dumps(r)+'\n').encode() for r in rows]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'old').write_bytes(b''.join(lines)+b'not-json-unneeded-tail\n')
            result=copy_prefix(root/'old',root/'new',rows)
            self.assertEqual((root/'new').read_bytes(),b''.join(lines));self.assertEqual(result['new_encodings'],0)
            with self.assertRaises(FileExistsError):copy_prefix(root/'old',root/'new',rows)

    def test_short_or_mismatched_prefix_stays_failed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'old').write_text(json.dumps(roster(1)[0])+'\n')
            with self.assertRaises(ValueError):copy_prefix(root/'old',root/'short',roster(2))
            bad=roster(1);bad[0]['n_supervised']=2
            with self.assertRaises(ValueError):copy_prefix(root/'old',root/'bad',bad)

    def test_original_schedule_gives_same_dose_for_new_three_to_one(self):
        large,small=prefix_metadata(roster());B=sum(r['n_supervised'] for r in large)
        lp=whole_schedule(large,B,17);sp=whole_schedule(small,B,17)
        self.assertEqual(lp['supervised_tokens'],sp['supervised_tokens']);self.assertEqual(B,9072)
        self.assertEqual(lp['q'],1);self.assertEqual(sp['q'],3)
        self.assertEqual(lp['optimizer_updates'],sp['optimizer_updates'])


if __name__=='__main__':unittest.main()
