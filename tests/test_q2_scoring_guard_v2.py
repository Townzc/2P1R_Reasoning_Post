"""Authored CPU checks: no generated candidate or benchmark execution."""
import ast
import copy
import unittest
from unittest import mock

from experiments.q2_supervision_migration import scoring_guard_v2 as sg


def admit(**changes):
    args = dict(original_details=[True, True], observed=[1, 1, 1], test_count=3,
                upstream_status="pass", child_exitcode=0, exception_events=[])
    args.update(changes)
    return sg.admit_diagnosis(**args)


class AdmissionTests(unittest.TestCase):
    def test_complete_pass_requires_matching_prefix(self):
        self.assertEqual(admit()["verified_suite_verdict"], "pass")
        self.assertIsNone(admit(observed=[1, 0, 1])["verified_suite_verdict"])
        self.assertIsNone(admit(observed=[1])["verified_suite_verdict"])

    def test_killed_or_incomplete_is_unknown_even_with_pass_status(self):
        for changed in [dict(child_exitcode=-15), dict(observed=[1, 1]),
                        dict(upstream_status=None), dict(observer_error=True),
                        dict(observed=[1, 1, 1, 1]), dict(observed=[1, 1, "1"])]:
            with self.subTest(changed=changed):
                self.assertIsNone(admit(**changed)["verified_suite_verdict"])

    def test_recovered_failure_before_original_pass_prefix_is_unknown(self):
        event = dict(scope="test", test_index=1, input_sha256="frozen",
                     classification="candidate_test_timeout")
        result = admit(observed=[1, 0], upstream_status="fail", exception_events=[event])
        self.assertFalse(result["prefix_consistent"])
        self.assertIsNone(result["verified_suite_verdict"])

    def test_attributable_failure_after_prefix(self):
        for classification in sg._ATTRIBUTABLE_TEST:
            event = dict(scope="test", test_index=2, input_sha256="frozen", classification=classification)
            result = admit(observed=[1, 1, 0], upstream_status="fail", exception_events=[event])
            self.assertEqual(result["verified_suite_verdict"], "fail")

    def test_opaque_or_misaligned_failure_does_not_become_reward_zero(self):
        base = dict(scope="test", test_index=2, input_sha256="frozen", classification="oracle_assertion")
        for events in [[], [{**base, "classification": "harness_or_unattributed_exception"}],
                       [{**base, "test_index": 1}], [{**base, "input_sha256": None}], [base, base]]:
            with self.subTest(events=events):
                self.assertIsNone(admit(observed=[1, 1, 0], upstream_status="fail",
                                        exception_events=events)["verified_suite_verdict"])

    def test_initialization_failure_requires_no_previous_or_current_tests(self):
        event = dict(scope="outer", classification="candidate_initialization_exception")
        args = dict(observed=[], upstream_status="fail", exception_events=[event])
        self.assertEqual(admit(original_details=[], **args)["verified_suite_verdict"], "fail")
        self.assertIsNone(admit(**args)["verified_suite_verdict"])
        self.assertIsNone(admit(original_details=[], observed=[0], upstream_status="fail",
                                exception_events=[event])["verified_suite_verdict"])

    def test_pass_with_exception_evidence_is_unknown(self):
        self.assertIsNone(admit(exception_events=[dict(scope="outer")])["verified_suite_verdict"])

    def test_known_status_cannot_start_worker(self):
        with mock.patch.object(sg.mp, "get_context") as context:
            for status in ("pass", "fail", "scorer_error"):
                with self.assertRaisesRegex(ValueError, "known verdicts"):
                    sg.diagnose_timeout({}, "", [], [], original_details=[], original_status=status)
            context.assert_not_called()

    def test_nonlinux_cannot_execute_diagnosis(self):
        with mock.patch.object(sg.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(ValueError, "isolated Linux"):
                sg.diagnose_timeout({}, "", [], [], original_details=[])


AUTHORED_STRUCTURE = '''
def unsafe_execute(dataset, entry_point, code, inputs, expected, time_limits,
                   atol, fast_check, stat, details, progress):
    try:
        for i, inp in enumerate(inputs):
            try:
                with time_limit(time_limits[i]):
                    out = fn(*inp)
                assert out == expected[i]
            except BaseException:
                details[i] = False
                progress.value += 1
                if fast_check:
                    raise
    except BaseException:
        stat.value = 1
'''


class InstrumentationTests(unittest.TestCase):
    def test_only_after_exception_statements_added(self):
        # Intercept compilation to compare AST; never run the authored candidate.
        with mock.patch("builtins.compile", wraps=compile) as compiler:
            _, assertions, provenance = sg._instrument(AUTHORED_STRUCTURE, "authored_evaluator.py")
        transformed = next(call.args[0] for call in compiler.call_args_list
                           if isinstance(call.args[0], ast.Module))
        stripped = copy.deepcopy(transformed)
        for node in ast.walk(stripped):
            if isinstance(node, ast.ExceptHandler):
                self.assertEqual(node.body[0].value.func.id, "_q2_observe_exception")
                node.body.pop(0)
                node.name = None
        original = ast.parse(AUTHORED_STRUCTURE)
        self.assertEqual(ast.dump(stripped, include_attributes=False), ast.dump(original, include_attributes=False))
        self.assertEqual(provenance["exception_observers"], 2)
        self.assertFalse(provenance["candidate_tracing"])
        self.assertEqual(len(assertions), 1)

    def test_changed_upstream_structure_is_rejected(self):
        for source in [AUTHORED_STRUCTURE.replace("BaseException", "Exception"),
                       AUTHORED_STRUCTURE.replace("dataset,", "changed,"),
                       AUTHORED_STRUCTURE.replace("details[i]", "other[i]")]:
            with self.assertRaises(ValueError):
                sg._instrument(source, "authored_evaluator.py")

    def test_failure_outside_candidate_is_not_attributed_by_exception_name(self):
        try:
            raise TimeoutError("authored infrastructure timeout")
        except TimeoutError as exc:
            event = sg._exception_event(exc, "test", 0, ["frozen"], "other.py", set(), TimeoutError, .1)
        self.assertEqual(event["classification"], "harness_or_unattributed_exception")

    def test_syntax_error_has_explicit_candidate_filename_requirement(self):
        for filename, wanted in [("<string>", "candidate_syntax_error"),
                                 ("harness.py", "harness_or_unattributed_exception")]:
            exc = SyntaxError("authored", (filename, 1, 1, "bad"))
            event = sg._exception_event(exc, "outer", -1, [], "other.py", set(), TimeoutError, .1)
            self.assertEqual(event["classification"], wanted)

    def test_authored_candidate_exception_and_timeout_are_distinct(self):
        # These are two authored exception fixtures, not saved/generated programs.
        for exception, wanted in [(ValueError, "candidate_call_exception"),
                                  (TimeoutError, "candidate_test_timeout")]:
            namespace = {"FixtureException": exception}
            exec(compile("def authored():\n    raise FixtureException('authored')\n", "<string>", "exec"), namespace)
            try:
                namespace["authored"]()
            except exception as exc:
                event = sg._exception_event(exc, "test", 0, ["frozen"], "evaluator.py", set(), TimeoutError, .1)
            self.assertEqual(event["classification"], wanted)
            self.assertEqual(event["input_sha256"], "frozen")

    def test_oracle_assertion_requires_exact_pinned_assertion_line(self):
        namespace = {}
        exec(compile("def authored():\n    assert False\n", "evaluator.py", "exec"), namespace)
        try:
            namespace["authored"]()
        except AssertionError as exc:
            good = sg._exception_event(exc, "test", 0, ["frozen"], "evaluator.py", {2}, TimeoutError, .1)
            bad = sg._exception_event(exc, "test", 0, ["frozen"], "evaluator.py", {3}, TimeoutError, .1)
        self.assertEqual(good["classification"], "oracle_assertion")
        self.assertEqual(bad["classification"], "harness_or_unattributed_exception")

    def test_propagated_test_timeout_is_not_an_initialization_failure(self):
        namespace = {"FixtureException": TimeoutError}
        exec(compile("def authored():\n    raise FixtureException('authored')\n", "<string>", "exec"), namespace)
        events = []
        original_exception = None
        try:
            try:
                namespace["authored"]()
            except TimeoutError as exc:
                original_exception = exc
                events.append(sg._exception_event(exc, "test", 2, ["a", "b", "frozen"],
                    "evaluator.py", set(), TimeoutError, .1))
                raise
        except TimeoutError as exc:
            events.append(sg._exception_event(exc, "outer", -1, [], "evaluator.py", set(),
                TimeoutError, .2, prior_test_exception=original_exception))
        self.assertEqual(events[0]["classification"], "candidate_test_timeout")
        self.assertEqual(events[1]["classification"], "propagated_test_exception")
        self.assertTrue(events[1]["propagated_from_test"])
        # Correcting this duplicate-event label must not change admission. The
        # matching-prefix case is a test failure; the conflicting-prefix case is unknown.
        old_events = [events[0], {**events[1], "classification": "candidate_initialization_timeout"}]
        for prefix in ([True, True], [True, True, True]):
            kwargs = dict(original_details=prefix, observed=[1, 1, 0], upstream_status="fail")
            self.assertEqual(admit(exception_events=events, **kwargs),
                             admit(exception_events=old_events, **kwargs))

    def test_unrelated_initialization_exception_is_not_marked_propagation(self):
        namespace = {"FixtureException": TimeoutError}
        exec(compile("def authored():\n    raise FixtureException('authored')\n", "<string>", "exec"), namespace)
        try:
            namespace["authored"]()
        except TimeoutError as exc:
            event = sg._exception_event(exc, "outer", -1, [], "evaluator.py", set(), TimeoutError,
                                        .1, prior_test_exception=TimeoutError("different instance"))
        self.assertEqual(event["classification"], "candidate_initialization_timeout")
        self.assertFalse(event["propagated_from_test"])

    def test_limits_and_prefix_validated_before_importing_evaluator(self):
        problem = dict(plus_input=[[1]], base_input=[[1]], entry_point="fixture", atol=0)
        with mock.patch.object(sg.platform, "system", return_value="Linux"), \
             mock.patch.object(sg, "_pinned_evaluator") as evaluator:
            for kwargs in [dict(outer_cap_seconds=181), dict(outer_cap_seconds=float("nan")),
                           dict(original_details=[False]), dict(original_details=[True, True])]:
                args = dict(original_details=[])
                args.update(kwargs)
                with self.assertRaises(ValueError):
                    sg.diagnose_timeout(problem, "authored", [1], [.1], **args)
            evaluator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
