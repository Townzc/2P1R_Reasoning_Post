import unittest
from scripts.p011_b_students_io import local_audit_assets


class LocalAuditAssetTests(unittest.TestCase):
    def test_exact_native_metadata_subset_and_unchanged_full_inventory(self):
        required={'config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt'}
        files={n:{'sha256':n,'bytes':7} for n in required|{'model.safetensors','README.md','LICENSE','generation_config.json'}}
        model={'files':files}
        selected=local_audit_assets(model)
        self.assertEqual(set(selected),required)
        self.assertEqual(len(files),9)
        self.assertTrue(all(selected[n] is files[n] for n in required))

    def test_missing_required_metadata_fails_closed(self):
        with self.assertRaises(KeyError):
            local_audit_assets({'files':{'config.json':{}}})


if __name__=='__main__':
    unittest.main()
