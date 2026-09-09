"""Historical source provenance guards; no models or development outputs."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import verify_pilot as audit


def digest(data):
    return hashlib.sha256(data).hexdigest()


class SyntheticSourceProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        (self.repo/'src').mkdir()
        self.source = self.repo/'src/example.py'
        self.source.write_bytes(b'original source\n')
        self.recorded = self.commit()
        self.manifest = {'source_commit': self.recorded, 'source_worktree_dirty': False,
                         'source_files_sha256': {'src/example.py': digest(self.source.read_bytes())}}

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'synthetic fixture')
        return self.git('rev-parse', 'HEAD')

    def raw(self, manifest=None):
        return json.dumps(self.manifest if manifest is None else manifest, sort_keys=True).encode()

    def legacy_binding(self):
        self.manifest['source_worktree_dirty'] = True
        manifest_path = 'runs/history/manifest.json'
        path = self.repo/manifest_path
        path.parent.mkdir(parents=True)
        path.write_bytes(self.raw())
        snapshot = self.commit()
        return {digest(self.raw()): {'commit': snapshot, 'manifest_path': manifest_path}}

    def test_clean_snapshot_passes_after_current_source_changes(self):
        self.source.write_text('evolved current source\n')
        self.commit()
        result = audit.verify_preparation_sources(self.raw(), self.repo)
        self.assertEqual(result['verified_source_snapshot'], self.recorded)
        self.assertFalse(result['later_publication'])
        self.assertFalse(result['prepublication_claimed'])

    def test_known_dirty_snapshot_preserves_later_publication_disclosure(self):
        bindings = self.legacy_binding()
        self.source.write_text('later worktree change\n')
        with patch.object(audit, 'LATER_PUBLISHED_SOURCE_SNAPSHOTS', bindings):
            result = audit.verify_preparation_sources(self.raw(), self.repo)
        self.assertEqual(result['recorded_preparation_commit'], self.recorded)
        self.assertTrue(result['recorded_source_worktree_dirty'])
        self.assertTrue(result['later_publication'])
        self.assertFalse(result['prepublication_claimed'])
        self.assertEqual(result['verified_source_snapshot'], next(iter(bindings.values()))['commit'])

    def test_unknown_dirty_manifest_is_rejected_even_if_source_matches(self):
        self.manifest['source_worktree_dirty'] = True
        with self.assertRaisesRegex(ValueError, 'Unknown dirty preparation'):
            audit.verify_preparation_sources(self.raw(), self.repo)

    def test_missing_or_wrong_clean_snapshot_cannot_use_worktree_fallback(self):
        for snapshot in ('f'*40, self.recorded):
            manifest = copy.deepcopy(self.manifest)
            manifest['source_commit'] = snapshot
            if snapshot == self.recorded:
                manifest['source_files_sha256']['src/example.py'] = digest(b'other source')
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                audit.verify_preparation_sources(self.raw(manifest), self.repo)

    def test_bound_snapshot_change_missing_file_or_digest_change_rejected(self):
        bindings = self.legacy_binding()
        original = next(iter(bindings.values()))
        self.source.write_text('incorrect published source\n')
        mismatched_source_snapshot = self.commit()
        for snapshot, path in (('f'*40, original['manifest_path']),
                               (self.recorded, original['manifest_path']),
                               (original['commit'], 'runs/history/missing.json'),
                               (mismatched_source_snapshot, original['manifest_path'])):
            changed = {digest(self.raw()): {'commit': snapshot, 'manifest_path': path}}
            with self.subTest(snapshot=snapshot, path=path), patch.object(
                    audit, 'LATER_PUBLISHED_SOURCE_SNAPSHOTS', changed), self.assertRaises(ValueError):
                audit.verify_preparation_sources(self.raw(), self.repo)

    def test_bound_manifest_bytes_must_match(self):
        bindings = self.legacy_binding()
        binding = next(iter(bindings.values()))
        (self.repo/binding['manifest_path']).write_text('changed manifest')
        binding['commit'] = self.commit()
        with patch.object(audit, 'LATER_PUBLISHED_SOURCE_SNAPSHOTS', bindings):
            with self.assertRaisesRegex(ValueError, 'Historical manifest differs'):
                audit.verify_preparation_sources(self.raw(), self.repo)

    def test_tampered_legacy_manifest_loses_exception(self):
        bindings = self.legacy_binding()
        changed = copy.deepcopy(self.manifest)
        changed['source_files_sha256']['src/example.py'] = digest(b'tampered')
        with patch.object(audit, 'LATER_PUBLISHED_SOURCE_SNAPSHOTS', bindings):
            with self.assertRaisesRegex(ValueError, 'Unknown dirty preparation'):
                audit.verify_preparation_sources(self.raw(changed), self.repo)

    def test_commit_path_and_digest_injection_rejected_before_git(self):
        cases = []
        for name in ('/tmp/file', '../file', 'src/../file', 'src//file', 'src/./file',
                     'src/file:other', 'src/file\nother', 'src/$(command)', 'src/file\\other'):
            changed = copy.deepcopy(self.manifest)
            changed['source_files_sha256'] = {name: 'a'*64}
            cases.append(changed)
        for commit in ('HEAD', '--help', 'a'*40+':src/file', 'a'*39, 'A'*40):
            changed = copy.deepcopy(self.manifest)
            changed['source_commit'] = commit
            cases.append(changed)
        changed = copy.deepcopy(self.manifest)
        changed['source_files_sha256']['src/example.py'] = 'not-a-digest'
        cases.append(changed)
        for changed in cases:
            with self.subTest(manifest=changed), patch.object(audit.subprocess, 'check_output') as call:
                with self.assertRaises(ValueError):
                    audit.verify_preparation_sources(self.raw(changed), self.repo)
                call.assert_not_called()

    def test_invalid_bound_snapshot_or_manifest_path_rejected(self):
        bindings = self.legacy_binding()
        for field, value in (('commit', 'HEAD'), ('manifest_path', '../manifest.json')):
            changed = copy.deepcopy(bindings)
            next(iter(changed.values()))[field] = value
            with self.subTest(field=field), patch.object(audit, 'LATER_PUBLISHED_SOURCE_SNAPSHOTS', changed):
                with self.assertRaises(ValueError):
                    audit.verify_preparation_sources(self.raw(), self.repo)


class HistoricalSourceProvenanceTests(unittest.TestCase):
    def test_both_exact_legacy_manifests_match_the_published_source_bytes(self):
        repo = Path(__file__).resolve().parents[1]
        self.assertEqual(len(audit.LATER_PUBLISHED_SOURCE_SNAPSHOTS), 2)
        for expected_hash, binding in audit.LATER_PUBLISHED_SOURCE_SNAPSHOTS.items():
            data = (repo/binding['manifest_path']).read_bytes()
            self.assertEqual(digest(data), expected_hash)
            result = audit.verify_preparation_sources(data, repo)
            self.assertEqual(result['verified_source_snapshot'], '6128e4266d62f14f063585d4c8e94dbe3ad8c711')
            self.assertTrue(result['recorded_source_worktree_dirty'])
            self.assertTrue(result['later_publication'])
            self.assertFalse(result['prepublication_claimed'])


if __name__ == '__main__':
    unittest.main()
