"""Local transfer fixtures, including real POSIX alarms interrupting stalls."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import io
import json
from pathlib import Path
import signal
import tempfile
import time
import unittest

from analyses.e015_export import CHECKPOINT_FILENAMES, CHUNK_BYTES, copy_checkpoint


def fixture():
    payloads = {name: ('fixture: ' + name).encode() for name in sorted(CHECKPOINT_FILENAMES)}
    manifest = {'kind': 'weights_only_not_optimizer_rng_resume', 'files': {
        name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for name, data in payloads.items()}}
    return payloads, manifest


class ObservedStream(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class ExportFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / 'new-export'
        self.payloads, self.manifest = fixture()
        self.opened, self.remaining, self.streams = [], [], []

    def opener(self, name, remaining_seconds):
        self.opened.append(name)
        self.remaining.append(remaining_seconds)
        stream = ObservedStream(self.payloads[name])
        self.streams.append(stream)
        return stream

    def receipt(self):
        return json.loads((self.destination / 'transfer_receipt.json').read_text())


class ExportIntegrity(ExportFixture):
    def test_successful_twelve_file_copy_has_exact_inventory_and_separate_receipt(self):
        events = []
        result = copy_checkpoint(self.opener, self.manifest, self.destination,
                                 progress=events.append, manifest_sha256='a' * 64)
        self.assertEqual(result, self.receipt())
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['all_files_verified'])
        self.assertTrue(result['full_backup_verified'])
        self.assertEqual(result['source_manifest_sha256'], 'a' * 64)
        self.assertEqual(result['rental_billing_status'], 'not_checked')
        self.assertEqual(result['bytes_written'], sum(len(value) for value in self.payloads.values()))
        self.assertEqual(result['verified_files'], self.manifest['files'])
        self.assertEqual(result['partial_files'], {})
        folder = self.destination / 'checkpoint_final'
        self.assertEqual({path.name for path in folder.iterdir()}, CHECKPOINT_FILENAMES)
        for name, data in self.payloads.items():
            self.assertEqual((folder / name).read_bytes(), data)
        self.assertEqual(self.opened, sorted(CHECKPOINT_FILENAMES))
        self.assertTrue(all(0 < remaining <= 1320 for remaining in self.remaining))
        self.assertTrue(all(a > b for a, b in zip(self.remaining, self.remaining[1:])))
        self.assertTrue(all(stream.closed and set(stream.read_sizes) == {CHUNK_BYTES}
                            for stream in self.streams))
        self.assertEqual([event['event'] for event in events], ['file_started', 'file_verified'] * 12)

    def test_corrupt_file_preserves_prior_verified_file_and_bad_partial(self):
        first, second = sorted(CHECKPOINT_FILENAMES)[:2]
        self.payloads[second] = b'!' * len(self.payloads[second])
        with self.assertRaisesRegex(ValueError, 'verification failed'):
            copy_checkpoint(self.opener, self.manifest, self.destination)
        folder = self.destination / 'checkpoint_final'
        self.assertTrue((folder / first).is_file())
        self.assertFalse((folder / second).exists())
        self.assertEqual((folder / (second + '.part')).read_bytes(), self.payloads[second])
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'partial_not_full_backup')
        self.assertFalse(receipt['full_backup_verified'])
        self.assertEqual(set(receipt['verified_files']), {first})
        self.assertEqual(receipt['partial_files'][second + '.part']['bytes'], len(self.payloads[second]))
        self.assertEqual(self.opened, [first, second])

    def test_wrong_size_stops_without_retry_or_publishing(self):
        first = sorted(CHECKPOINT_FILENAMES)[0]
        self.payloads[first] += b'extra bytes'
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            copy_checkpoint(self.opener, self.manifest, self.destination)
        self.assertEqual(self.opened, [first])
        self.assertEqual(self.receipt()['verified_files'], {})
        self.assertTrue((self.destination / 'checkpoint_final' / (first + '.part')).is_file())

    def test_missing_bytes_and_source_errors_remain_partial(self):
        first = sorted(CHECKPOINT_FILENAMES)[0]
        self.payloads[first] = b''
        with self.assertRaisesRegex(ValueError, 'verification failed'):
            copy_checkpoint(self.opener, self.manifest, self.destination)
        self.assertFalse(self.receipt()['full_backup_verified'])
        other = Path(self.temp.name) / 'source-error'
        calls = []

        def broken(name, remaining):
            calls.append((name, remaining))
            raise ConnectionError('fixture opener failure')

        with self.assertRaisesRegex(ConnectionError, 'fixture opener failure'):
            copy_checkpoint(broken, self.manifest, other)
        receipt = json.loads((other / 'transfer_receipt.json').read_text())
        self.assertEqual(receipt['failure_type'], 'ConnectionError')
        self.assertFalse(receipt['full_backup_verified'])
        self.assertEqual(len(calls), 1)
        self.assertGreater(calls[0][1], 0)
        self.assertEqual((other / 'checkpoint_final' / (first + '.part')).read_bytes(), b'')

    def test_unsafe_names_sizes_hashes_and_allowlist_are_rejected_before_destination(self):
        original = sorted(CHECKPOINT_FILENAMES)[0]
        variants = []
        for unsafe in ('../outside', '/absolute', 'nested/name', 'nested\\name', '.', '..', 'bad\x00name'):
            bad = copy.deepcopy(self.manifest)
            bad['files'][unsafe] = bad['files'].pop(original)
            variants.append(bad)
        for key, value in [('bytes', True), ('bytes', 0), ('bytes', -1), ('bytes', 1.0),
                           ('sha256', 'f' * 63), ('sha256', 'x' * 64)]:
            bad = copy.deepcopy(self.manifest)
            bad['files'][original][key] = value
            variants.append(bad)
        bad = copy.deepcopy(self.manifest)
        del bad['files'][original]
        variants.append(bad)
        for manifest in variants:
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                copy_checkpoint(self.opener, manifest, self.destination)
            self.assertFalse(self.destination.exists())
        self.assertEqual(self.opened, [])

    def test_existing_destination_is_never_overwritten_or_resumed(self):
        self.destination.mkdir()
        sentinel = self.destination / 'keep.txt'
        sentinel.write_bytes(b'untouched')
        with self.assertRaises(FileExistsError):
            copy_checkpoint(self.opener, self.manifest, self.destination)
        self.assertEqual(sentinel.read_bytes(), b'untouched')
        self.assertEqual(list(self.destination.iterdir()), [sentinel])
        self.assertEqual(self.opened, [])

    def test_progress_failure_preserves_completed_file_and_does_not_retry(self):
        first = sorted(CHECKPOINT_FILENAMES)[0]

        def interrupted(event):
            if event['event'] == 'file_verified':
                raise KeyboardInterrupt('fixture user interruption')

        with self.assertRaises(KeyboardInterrupt):
            copy_checkpoint(self.opener, self.manifest, self.destination, progress=interrupted)
        self.assertEqual(self.opened, [first])
        self.assertEqual(set(self.receipt()['verified_files']), {first})
        self.assertFalse(self.receipt()['full_backup_verified'])


@unittest.skipUnless(hasattr(signal, 'setitimer'), 'POSIX real-time alarms required')
class ExportDeadline(ExportFixture):
    def test_actual_alarm_interrupts_stalled_read_and_preserves_partial_bytes(self):
        first = sorted(CHECKPOINT_FILENAMES)[0]
        previous_handler = signal.getsignal(signal.SIGALRM)

        class Stalled(io.BytesIO):
            def read(self, size=-1):
                if self.tell():
                    time.sleep(2)
                return super().read(min(size, 3))

        started = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, 'deadline'):
            copy_checkpoint(lambda name, remaining: Stalled(self.payloads[name]),
                            self.manifest, self.destination, max_seconds=.05)
        self.assertLess(time.monotonic() - started, .8)
        self.assertEqual((self.destination / 'checkpoint_final' / (first + '.part')).read_bytes(),
                         self.payloads[first][:3])
        self.assertFalse((self.destination / 'checkpoint_final' / first).exists())
        self.assertEqual(self.receipt()['failure_type'], 'TimeoutError')
        self.assertFalse(self.receipt()['full_backup_verified'])
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertIs(signal.getsignal(signal.SIGALRM), previous_handler)

    def test_actual_alarm_also_covers_opener_and_context_exit(self):
        def stalled_open(name, remaining):
            time.sleep(2)
            return io.BytesIO(self.payloads[name])

        class StalledExit(io.BytesIO):
            def __exit__(self, *args):
                super().__exit__(*args)
                time.sleep(2)

        for index, opener in enumerate((stalled_open,
                lambda name, remaining: StalledExit(self.payloads[name]))):
            destination = Path(self.temp.name) / f'stall-{index}'
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                copy_checkpoint(opener, self.manifest, destination, max_seconds=.04)
            self.assertLess(time.monotonic() - started, .8)
            receipt = json.loads((destination / 'transfer_receipt.json').read_text())
            self.assertEqual(receipt['status'], 'partial_not_full_backup')
            self.assertEqual(receipt['verified_files'], {})

    def test_existing_alarm_is_rejected_and_previous_handler_timer_preserved(self):
        previous_handler = signal.getsignal(signal.SIGALRM)
        previous_timer = signal.getitimer(signal.ITIMER_REAL)
        self.assertEqual(previous_timer, (0.0, 0.0))

        def existing_handler(signum, frame):
            raise AssertionError('Existing alarm should not expire in this fixture')

        signal.signal(signal.SIGALRM, existing_handler)
        signal.setitimer(signal.ITIMER_REAL, 10, 2)
        try:
            with self.assertRaisesRegex(RuntimeError, 'existing active'):
                copy_checkpoint(self.opener, self.manifest, self.destination)
            remaining, interval = signal.getitimer(signal.ITIMER_REAL)
            self.assertGreater(remaining, 9)
            self.assertEqual(interval, 2)
            self.assertIs(signal.getsignal(signal.SIGALRM), existing_handler)
            self.assertFalse(self.destination.exists())
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)

    def test_non_main_thread_and_invalid_deadlines_are_rejected(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(copy_checkpoint, self.opener, self.manifest, self.destination)
            with self.assertRaisesRegex(RuntimeError, 'main-thread'):
                future.result()
        for seconds in (True, 0, -1, float('nan'), float('inf')):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                copy_checkpoint(self.opener, self.manifest, self.destination, max_seconds=seconds)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.opened, [])


if __name__ == '__main__':
    unittest.main()
