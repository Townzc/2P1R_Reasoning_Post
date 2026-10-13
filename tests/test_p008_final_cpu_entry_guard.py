import json
import unittest
from pathlib import Path

from scripts.p008_final_cpu_guard import CURRENT_ENTRY, CURRENT_MODULE, require_current_entry


class FinalCPUEntryGuard(unittest.TestCase):
    def test_current_exact_published_bundle(self):
        bundle = json.loads(Path('reports/p008_20261013/final_cpu_replacements_preflight_v1/SOURCE_BUNDLE.json').read_text())
        self.assertEqual(require_current_entry(CURRENT_MODULE, bundle), CURRENT_ENTRY)

    def test_reject_each_retired_cpu_entry(self):
        for name in ('modal_audit', 'modal_audit_lineage'):
            module = 'experiments/sft_allocation_p008/' + name + '.py'
            with self.subTest(module=module), self.assertRaises(ValueError):
                require_current_entry(module, {module: 'unused'})

    def test_reject_current_name_with_legacy_bundle(self):
        with self.assertRaises(ValueError):
            require_current_entry(CURRENT_MODULE, {
                CURRENT_MODULE: 'unused',
                'experiments/sft_allocation_p008/modal_audit_lineage.py': 'unused'})


if __name__ == '__main__':
    unittest.main()
