"""Authored context/POSIX smoke tests; no saved candidate or benchmark executes."""
from collections import Counter
from contextlib import contextmanager
import math
import multiprocessing as mp
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest import mock

from experiments.q2_supervision_migration import timing_probe as probe


@contextmanager
def ordinary_context(seconds):
    yield


class AuthoredAlarm(TimeoutError):
    pass


@contextmanager
def authored_signal_timer(seconds):
    """A test-only real SIGALRM context; does not import EvalPlus."""
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)

    def authored_alarm_handler(signum, frame):
        raise AuthoredAlarm("authored smoke timer expired")

    signal.signal(signal.SIGALRM, authored_alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer != (0.0, 0.0):
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


def authored_normal_child(recorder, alarm_remaining):
    with recorder.wrap(authored_signal_timer)(1.0):
        started_cpu = time.process_time()
        while time.process_time() - started_cpu < .02:
            pass
        time.sleep(.02)
    alarm_remaining.value = signal.getitimer(signal.ITIMER_REAL)[0]


def authored_timeout_child(recorder, observed_exception, alarm_remaining):
    try:
        with recorder.wrap(authored_signal_timer)(.04):
            while True:
                pass
    except AuthoredAlarm:
        observed_exception.value = 1
    alarm_remaining.value = signal.getitimer(signal.ITIMER_REAL)[0]


def authored_killed_child(recorder, ready):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    with recorder.wrap(authored_signal_timer)(1.0):
        ready.set()
        time.sleep(10)


@unittest.skipUnless("fork" in mp.get_all_start_methods() and hasattr(signal, "setitimer"),
                     "requires POSIX fork and interval signals")
class PosixForkSignalSmokeTests(unittest.TestCase):
    """Real fork, short hand-authored bodies and bounded process cleanup only."""

    def setUp(self):
        self.context = mp.get_context("fork")

    def clean_child(self, child):
        # Every join is <= 2s. Neither a failed assertion nor a hung body leaves
        # an owned process behind; kill is an explicit last resort after SIGTERM.
        if child.is_alive():
            child.terminate()
        child.join(timeout=1.0)
        if child.is_alive():
            child.kill()
            child.join(timeout=.5)
        self.assertFalse(child.is_alive(), "authored child survived bounded cleanup")

    def test_forked_normal_boundary_reads_real_cpu_wall_and_timer_in_parent(self):
        recorder = probe.BoundaryRecorder([1.0], context=self.context)
        remaining = self.context.RawValue("d", -1.0)
        child = self.context.Process(target=authored_normal_child, args=(recorder, remaining))
        child.start()
        try:
            child.join(timeout=1.5)
            self.assertEqual(child.exitcode, 0)
            row, = recorder.records()
            self.assertTrue(row["boundary_completed"])
            self.assertGreaterEqual(row["cpu_seconds"], .015)
            self.assertGreaterEqual(row["wall_seconds"], .035)
            self.assertGreater(row["wall_seconds"] - row["cpu_seconds"], .01)
            self.assertGreater(row["alarm_armed_delay"], 0)
            self.assertLessEqual(row["alarm_armed_delay"], 1.0)
            self.assertIn("authored_alarm_handler", row["alarm_handler_armed"])
            self.assertEqual(row["alarm_after_delay"], 0)
            self.assertEqual(remaining.value, 0)
            self.assertFalse(recorder.error.value)
        finally:
            self.clean_child(child)

    def test_real_sigalrm_exception_and_cleanup_are_shared_back_to_parent(self):
        recorder = probe.BoundaryRecorder([.04], context=self.context)
        caught = self.context.RawValue("b", 0)
        remaining = self.context.RawValue("d", -1.0)
        child = self.context.Process(target=authored_timeout_child, args=(recorder, caught, remaining))
        child.start()
        try:
            child.join(timeout=1.5)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(caught.value, 1)
            row, = recorder.records()
            self.assertEqual(row["exception_type"], "AuthoredAlarm")
            self.assertEqual(row["exception"], 1)
            self.assertTrue(row["boundary_completed"])
            self.assertGreaterEqual(row["wall_seconds"], .03)
            self.assertGreater(row["cpu_seconds"], 0)
            self.assertGreater(row["alarm_armed_delay"], 0)
            self.assertLessEqual(row["alarm_armed_delay"], .04)
            self.assertEqual(row["alarm_after_delay"], 0)
            self.assertEqual(remaining.value, 0)
            self.assertFalse(recorder.error.value)
        finally:
            self.clean_child(child)

    def test_terminated_fork_keeps_incomplete_shared_boundary_without_fake_elapsed(self):
        recorder = probe.BoundaryRecorder([1.0], context=self.context)
        ready = self.context.Event()
        child = self.context.Process(target=authored_killed_child, args=(recorder, ready))
        child.start()
        try:
            self.assertTrue(ready.wait(timeout=.5), "authored child did not enter timer body")
            child.terminate()
            child.join(timeout=1.0)
            self.assertEqual(child.exitcode, -signal.SIGTERM)
            row, = recorder.records()
            self.assertFalse(row["boundary_completed"])
            self.assertIsNone(row["wall_seconds"])
            self.assertIsNone(row["cpu_seconds"])
            self.assertGreater(row["start_wall"], 0)
            self.assertGreater(row["alarm_armed_delay"], 0)
        finally:
            self.clean_child(child)


class BoundaryMeasurementTests(unittest.TestCase):
    def wrapper(self, recorder, timer=ordinary_context):
        return recorder.wrap(timer, wall=iter([10.0, 12.0, 20.0, 23.0]).__next__,
            cpu=iter([4.0, 4.5, 6.0, 7.0]).__next__,
            gettimer=lambda: (0.0, 0.0), gethandler=lambda: 0)

    def test_measurement_preserves_original_context_and_limits(self):
        seen = []

        @contextmanager
        def timer(seconds):
            seen.append(("enter", seconds))
            yield
            seen.append(("exit", seconds))

        recorder = probe.BoundaryRecorder([1.0, 2.0])
        wrapped = self.wrapper(recorder, timer)
        with wrapped(1.0):
            seen.append(("body", 1))
        with wrapped(2.0):
            seen.append(("body", 2))
        self.assertEqual(seen, [("enter", 1.0), ("body", 1), ("exit", 1.0),
                                ("enter", 2.0), ("body", 2), ("exit", 2.0)])
        first, second = recorder.records()
        self.assertEqual((first["wall_seconds"], first["cpu_seconds"]), (2.0, .5))
        self.assertEqual((second["wall_seconds"], second["cpu_seconds"]), (3.0, 1.0))
        self.assertTrue(first["boundary_completed"])
        self.assertFalse(recorder.error.value)

    def test_candidate_like_exception_is_recorded_and_identical_exception_reraised(self):
        recorder = probe.BoundaryRecorder([1.0])
        failure = TimeoutError("synthetic context-only timeout")
        with self.assertRaises(TimeoutError) as caught:
            with self.wrapper(recorder)(1.0):
                raise failure
        self.assertIs(caught.exception, failure)
        row, = recorder.records()
        self.assertEqual(row["exception_type"], "TimeoutError")
        self.assertEqual(row["exception"], 1)
        self.assertTrue(row["boundary_completed"])

    def test_context_entry_exception_is_not_swallowed(self):
        recorder = probe.BoundaryRecorder([1.0])

        @contextmanager
        def failed_timer(seconds):
            raise RuntimeError("synthetic timer error")
            yield  # pragma: no cover

        with self.assertRaisesRegex(RuntimeError, "synthetic timer"):
            with self.wrapper(recorder, failed_timer)(1.0):
                self.fail("body must not run")
        self.assertEqual(recorder.records()[0]["exception_type"], "RuntimeError")

    def test_timer_mismatch_fails_before_body(self):
        recorder = probe.BoundaryRecorder([5.0124])
        with self.assertRaisesRegex(probe.ProfileError, "sequence"):
            with self.wrapper(recorder)(5.1):
                self.fail("body must not run")
        self.assertTrue(recorder.error.value)
        self.assertEqual(recorder.records(), [])

    def test_extra_timer_call_is_not_silently_admitted(self):
        recorder = probe.BoundaryRecorder([1.0])
        wrapped = self.wrapper(recorder)
        with wrapped(1.0):
            pass
        with self.assertRaises(probe.ProfileError):
            with wrapped(1.0):
                self.fail("body must not run")

    def test_watchdog_interrupted_boundary_is_not_given_fake_elapsed(self):
        recorder = probe.BoundaryRecorder([1.0])
        recorder.count.value = 1
        recorder.values[0:3] = [1.0, 20.0, 8.0]
        row, = recorder.records()
        self.assertIsNone(row["wall_seconds"])
        self.assertIsNone(row["cpu_seconds"])
        self.assertFalse(row["boundary_completed"])

    def test_invalid_limits_rejected(self):
        for limits in ([], [0], [-1], [float("nan")], [float("inf")]):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                probe.BoundaryRecorder(limits)

    def test_text_truncation_is_bounded(self):
        recorder = probe.BoundaryRecorder([1.0])
        recorder._put_text(recorder.exception_names, 96, 0, "x" * 1000)
        self.assertEqual(len(recorder._get_text(recorder.exception_names, 96, 0)), 95)


class FixedDiagnosticContractTests(unittest.TestCase):
    def args(self, out="unused"):
        return ["--continuation-root", "saved", "--references", "refs", "--data-json", "data",
                "--data-sha256", "a" * 64, "--out", out, "--source-commit", "b" * 40,
                "--deadline-epoch", "9000", "--execute-saved-output-diagnostic"]

    def test_predeclared_plan_is_balanced_and_reversed(self):
        self.assertEqual(Counter(probe.CELL_PLAN), {
            ("original", False): 2, ("original", True): 2,
            ("guard", False): 2, ("guard", True): 2})
        self.assertEqual(probe.CELL_PLAN[:4], tuple(reversed(probe.CELL_PLAN[4:])))

    def test_artifact_envelope_cannot_admit_training_even_if_raw_result_does(self):
        with mock.patch.object(probe, "durable_json") as write:
            probe.diagnostic_json("unused", {"raw_result": {"status": "pass"},
                "eligible_for_reward": True, "model_admitted": True, "optimizer_updates": 8})
        result = write.call_args.args[1]
        self.assertFalse(result["eligible_for_reward"])
        self.assertFalse(result["model_admitted"])
        self.assertEqual(result["optimizer_updates"], 0)

    def test_shared_window_cannot_be_reset_or_extended(self):
        self.assertEqual(probe.available_seconds(10000, 100, 200), 1700)
        self.assertEqual(probe.available_seconds(350, 100, 200), 150)
        self.assertLessEqual(probe.available_seconds(350, 100, 351), 0)
        with self.assertRaises(probe.ProfileError):
            probe.available_seconds(math.inf, 100, 200)

    def test_refuses_non_linux_before_creating_output(self):
        with mock.patch.object(probe.sys, "platform", "darwin"), \
             mock.patch.object(Path, "mkdir") as mkdir:
            with self.assertRaisesRegex(probe.ProfileError, "Linux CPU-only"):
                probe.main(self.args())
        mkdir.assert_not_called()

    def test_refuses_gpu_visible_environment(self):
        with mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": "0"}):
            with self.assertRaisesRegex(probe.ProfileError, "CPU-only"):
                probe.main(self.args())

    def test_no_execution_without_explicit_saved_output_flag(self):
        with mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": ""}):
            with self.assertRaisesRegex(probe.ProfileError, "explicit"):
                probe.main(self.args()[:-1])

    def test_unowned_cell_is_refused(self):
        with mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.time, "time", return_value=100), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": "", "Q2_PROFILE_PARENT_PID": "invalid"}):
            with self.assertRaisesRegex(probe.ProfileError, "owned"):
                probe.main(self.args() + ["--_cell", "0"])

    def test_existing_output_refused_instead_of_replayed(self):
        with tempfile.TemporaryDirectory() as out, \
             mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.time, "time", return_value=100), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": ""}), \
             mock.patch.object(probe, "launch_guarded") as launch:
            with self.assertRaises(FileExistsError):
                probe.main(self.args(out))
        launch.assert_not_called()

    def test_failed_cells_preserved_then_fixed_queue_continues_without_retry(self):
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.time, "time", return_value=100), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": ""}), \
             mock.patch.object(probe, "launch_guarded", return_value=1) as launch:
            out = Path(root) / "probe"
            self.assertEqual(probe.main(self.args(str(out))), 1)
            self.assertEqual(launch.call_count, 8)
            self.assertEqual([call.args[0][-1] for call in launch.call_args_list],
                             [str(index) for index in range(8)])
            import json
            receipt = json.loads((out / "probe_receipt.json").read_text())
            self.assertFalse(receipt["eligible_for_reward"])
            self.assertFalse(receipt["model_admitted"])
            self.assertEqual(receipt["stop_reason"], "fixed_diagnostic_cells_attempted_with_failures")
            self.assertEqual(receipt["cells_attempted"], 8)
            self.assertEqual(receipt["cells_completed"], 0)
            self.assertEqual(receipt["failed_cell_indices"], list(range(8)))

    def test_shared_deadline_stops_queue_before_an_unaffordable_cell(self):
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.time, "time", side_effect=[100, 100, 100, 1801, 1801]), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": ""}), \
             mock.patch.object(probe, "launch_guarded", return_value=0) as launch:
            out = Path(root) / "probe"
            self.assertEqual(probe.main(self.args(str(out))), 1)
            launch.assert_called_once()
            import json
            receipt = json.loads((out / "probe_receipt.json").read_text())
            self.assertEqual(receipt["cells_attempted"], 1)
            self.assertEqual(receipt["stop_reason"], "insufficient_shared_window_for_next_fixed_cell")

    def test_finite_cells_run_without_score_based_selection(self):
        with tempfile.TemporaryDirectory() as root, \
             mock.patch.object(probe.sys, "platform", "linux"), \
             mock.patch.object(probe.time, "time", return_value=100), \
             mock.patch.dict(probe.os.environ, {"CUDA_VISIBLE_DEVICES": ""}), \
             mock.patch.object(probe, "launch_guarded", return_value=0) as launch:
            out = Path(root) / "probe"
            self.assertEqual(probe.main(self.args(str(out))), 0)
            self.assertEqual(launch.call_count, 8)
            for index, call in enumerate(launch.call_args_list):
                self.assertEqual(call.args[0][-2:], ["--_cell", str(index)])
                self.assertEqual(call.args[2], probe.CELL_SECONDS)


if __name__ == "__main__":
    unittest.main()
