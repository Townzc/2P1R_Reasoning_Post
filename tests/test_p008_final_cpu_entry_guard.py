import ast
import unittest
from pathlib import Path

from scripts.p008_final_cpu_guard import CURRENT_ENTRY, CURRENT_MODULE, require_current_entry


class FinalCPUEntryGuard(unittest.TestCase):
    def test_current_exact_candidate_bundle(self):
        tree = ast.parse(Path(CURRENT_MODULE).read_text())
        names = next(ast.literal_eval(n.value) for n in tree.body
                     if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name)
                     and t.id == 'SOURCES' for t in n.targets))
        bundle = {n:'candidate' for n in names}
        self.assertEqual(require_current_entry(CURRENT_MODULE, bundle), CURRENT_ENTRY)

    def test_reject_each_retired_cpu_entry(self):
        for name in ('modal_audit', 'modal_audit_lineage', 'modal_audit_replacements'):
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
