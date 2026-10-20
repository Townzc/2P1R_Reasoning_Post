"""Create-only audit dispositions and technical notes; no scientific computation."""
import copy
import datetime
import hashlib
import json
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(".")
R = ROOT / ".local/p010_20261019/r1"
P = ROOT / "reports/p010_20261019"
REVIEW = R / "review_f04922a_actual"
COMMIT = "f04922a0407c03445a59f8982241cb51bf98057b"
REPO = "https://github.com/Townzc/2P1R_Reasoning_Post"
NOW = datetime.datetime.now(datetime.timezone.utc)
UTC = NOW.isoformat()
PDT = NOW.astimezone(ZoneInfo("America/Los_Angeles")).isoformat()
ACCEPT_DIR = P / "review_f04922a_actual_E3_C6_Z2_accepted_v1"
NOTES_DIR = P / "post_audit_technical_notes_20261020_v1"
HANDOFF_DIR = P / "technical_handoff_20261020_v1"
INDEX = Path("reports/p007_audit/INDEX.json")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write_text(path, content):
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


definitions = [
    {
        "kind": "E3",
        "file": "E3_A3_REPORT.md",
        "sha": "7b7764bd42856c70fb0a0edfc9ed73ac3228f3b0eb1198a54a9158991eb96247",
        "request": "p010-E3-complete-temperature-supply-and-metrics-A3-r1",
        "scope": "p010-E3-complete-temperature-supply-and-metrics-A3",
        "target": "1efc3b4970ef77e3d26b2fcf1ea64ccbe99d6b38",
        "private": "E3_COMPLETE_RESULTS_A3_ACCEPTED.json",
        "manifests": {
            "e3_complete_results_v1": "3d040dd81c48fe9aef541efb8d07efc366d083fffd07f62b985c0108636b8f3f"
        },
    },
    {
        "kind": "C6",
        "file": "C6_A3_REPORT.md",
        "sha": "f13b20cbdb5a9ec035d5394cf806b0ad40ae1217c118669948884c3782579283",
        "request": "p010-C6-complete-cue-endpoints-and-analysis-A3-r1",
        "scope": "p010-C6-complete-cue-endpoints-and-analysis-A3",
        "target": "e150366b76c5277b3e0d3dccb47c08060c9f0647",
        "private": "C6_COMPLETE_RESULTS_ANALYSIS_A3_ACCEPTED.json",
        "manifests": {
            "c6_complete_results_v1": "4062e5c7e35f26bc20ec729ec3a96ee30e40f52262ee06fa9f9a5484253acefe",
            "c6_analysis_v1": "6b968592302349db6886dce258285fc57c44a83ee33cd1e1edb9c1d66c30d6c5",
        },
    },
    {
        "kind": "Z2",
        "file": "Z2_A5_REPORT.md",
        "sha": "3b115ccfe26263ab25371987d3b2617084ed34df6ca7d0d4ce8ebced4469d538",
        "request": "p010-Z2-deterministic-table-figure-number-trace-A5-r1",
        "scope": "p010-Z2-deterministic-table-figure-number-trace-A5",
        "target": "9178029d82776b01a759d6376d7309bd7df9681a",
        "private": "Z2_EARLY_NUMBER_TRACE_A5_ACCEPTED.json",
        "manifests": {
            "z2_number_trace_v1": "40c6ae6323a9a3408528cc7e847c011faa3cd93b5d4512b8bda996012f34aa3d"
        },
    },
]

# Preflight every new destination and fixed report before writing any disposition.
assert all(not path.exists() for path in [ACCEPT_DIR, NOTES_DIR, HANDOFF_DIR])
assert not (R / "Z1_EMBEDDED_REPORT_EXPOSURE_20261020.json").exists()
assert not (R / "F04922A_AUDIT_DISPOSITION_COMPLETED.json").exists()
index = read(INDEX)
requests = {row["request_id"]: row for row in index["review_requests"]}
for definition in definitions:
    report = REVIEW / definition["file"]
    assert sha(report) == definition["sha"]
    text = report.read_text()
    assert definition["scope"] in text and definition["target"] in text
    assert "PASS-WITH-NOTES" in text
    assert not (R / definition["private"]).exists()
    assert requests[definition["request"]]["target_commit"] == definition["target"]
    for packet, expected in definition["manifests"].items():
        assert sha(P / packet / "MANIFEST.json") == expected

e3_result = read(REVIEW / "A3_E3_RESULT.json")
c6_result = read(REVIEW / "A3_C6_RESULT.json")
assert sha(REVIEW / "A3_E3_RESULT.json") == "4a756ced383cd11b40d03db05c5e878e22c693d75ea09743e0659ba84d5ab272"
assert sha(REVIEW / "A3_C6_RESULT.json") == "ba2050e5b10afd11798bc5fce1acac184e92fbbc07773eae3ab64a00bd8f41cd"
assert e3_result["manifest_files_bad"] == []
assert e3_result["raw_rows"] == 3200 and e3_result["raw_identity_mismatch"] == 0
assert e3_result["metrics_all_ok"] and e3_result["same_seed_all_three_temps"]
assert c6_result["results_manifest_bad"] == [] and c6_result["analysis_manifest_bad"] == []
assert c6_result["paired_point_all_equal"] and c6_result["paired_ci_all_equal"]
for cell in ("base_math", "base_gsm", "s1_n400_math", "t72_n400_math"):
    assert c6_result[cell]["raw_ids_eq_roster"]
    assert c6_result[cell]["raw_identity_mismatch"] == 0
    assert c6_result[cell]["question_correct_eq_journal"]

source_z2 = (REVIEW / "Z2_A5_REPORT.md").read_text()
excluded_start = source_z2.index("## 三、Z1")
excluded_end = source_z2.index("## 四、", excluded_start)
z2_projection = (
    source_z2[:excluded_start]
    + "## Claude-owned section excluded from this Codex projection\n\n"
    + "The original third section is excluded in full. This projection does not "
    + "adopt its labels, numeric conclusions, or claimed owner checks. "
    + "See PROJECTION.json and the exposure record.\n\n"
    + source_z2[excluded_end:]
)

exposure = {
    "recorded_utc": UTC,
    "source_report_commit": COMMIT,
    "source_report": "audit/claude/20261020q/Z2_A5_REPORT.md",
    "source_report_sha256": definitions[2]["sha"],
    "unexpected_embedded_Z1_material_exposed": True,
    "event": "A filename-selected non-Z1 A5 report contained a Z1 summary and label information; the first full tool rendering exposed it before the mixed content was recognized.",
    "exposure_window": {
        "after_fetch_receipt_utc": read(REVIEW / "FETCH_RECEIPT.json")["utc"],
        "before_this_record_utc": UTC,
    },
    "original_Z1_report_or_label_files_fetched_or_opened": False,
    "subsequent_Z1_processing": False,
    "Codex_Z1_relabeling_or_numeric_adoption": False,
    "owner_12_item_check_independently_verified_by_Codex": False,
    "containment": [
        "Preserve the original mixed report and SHA without changing it.",
        "Exclude the entire third section from all further Codex projections and acceptance scope.",
        "Do not claim Codex remained blind after this exposure.",
        "Do not repeat the already-completed C7 review or open any original Z1 artifact.",
    ],
}

for directory in (ACCEPT_DIR, NOTES_DIR, HANDOFF_DIR):
    directory.mkdir()
write_json(R / "Z1_EMBEDDED_REPORT_EXPOSURE_20261020.json", exposure)
write_json(ACCEPT_DIR / "BOUNDARY_EXPOSURE.json", exposure)
write_text(ACCEPT_DIR / "Z2_A5_NON_Z1_PROJECTION.md", z2_projection)
write_json(ACCEPT_DIR / "PROJECTION.json", {
    "original_report_sha256": definitions[2]["sha"],
    "original_report_url": f"{REPO}/blob/{COMMIT}/audit/claude/20261020q/Z2_A5_REPORT.md",
    "projection": "Z2_A5_NON_Z1_PROJECTION.md",
    "omitted_section": "Complete third section, Claude-owned Z1",
    "projection_is_original_bytes": False,
    "original_private_bytes_retained": True,
    "initial_mixed_report_exposure_disclosed": True,
})

acceptances = []
for definition in definitions:
    report = REVIEW / definition["file"]
    history = read(REVIEW / (definition["file"] + ".history.json"))[0]
    value = {
        "created_utc": UTC,
        "decision": "PASS-WITH-NOTES",
        "reviewer": "Claude",
        "scope": definition["scope"],
        "request_id": definition["request"],
        "target_commit": definition["target"],
        "report_commit": COMMIT,
        "report_last_change_commit": history["sha"],
        "report_commit_event_utc": history["author"]["date"],
        "report_header_time_is_approximate_not_actual_observation": True,
        "report_path": "audit/claude/20261020q/" + definition["file"],
        "report_sha256": definition["sha"],
        "report_url": f"{REPO}/blob/{COMMIT}/audit/claude/20261020q/{definition['file']}",
        "report_fetch_utc": read(REVIEW / "FETCH_RECEIPT.json")["utc"],
        "report_read_confirmed_utc": UTC,
        "local_report_file": str(report.resolve()),
        "result_manifest_sha256": {
            str(P / key): val for key, val in definition["manifests"].items()
        },
        "new_scientific_calls": 0,
        "new_scoring": 0,
        "new_statistics": 0,
        "new_rendering": 0,
        "frozen_labels_and_results_unchanged": True,
        "technical_audit_disposition_not_course_interpretation": True,
    }
    if definition["kind"] == "E3":
        value.update({
            "evidence_source_binding_sha256": sha(P / "e3_complete_results_v1/SOURCE_BINDING.json"),
            "runtime_source_count": 25,
            "verification_source_count": 28,
            "spec_sha256": e3_result["spec_sha"],
            "independent_result_sha256": sha(REVIEW / "A3_E3_RESULT.json"),
            "new_rows_verified": 3200,
            "old_T08_rows_reused_without_rescoring": 1600,
            "metrics_reproduced": True,
            "reviewer_ran_vllm_or_math_verify": False,
            "notes": [
                "Six capped UTF-8 tails differ from backend text; all remain wrong under the unchanged stop rule.",
                "The reported numeral-base boundary case retains its original label.",
                "The prior A1 canonical-serialization discrepancy is acknowledged by the reviewer; neither original report nor JSON is overwritten.",
                "Shared attempt seeds and lexical expression-set Jaccard limits are retained. No new CI or causal claim.",
                "Provider application timestamps are distinct from the actual worker-entry timestamp.",
            ],
        })
    elif definition["kind"] == "C6":
        value.update({
            "evidence_source_binding_sha256": sha(P / "c6_complete_results_v1/SOURCE_BINDING.json"),
            "analysis_source_binding_sha256": sha(P / "c6_analysis_v1/SOURCE_BINDING.json"),
            "spec_sha256": "70122980ab2623384dd86cd81b0c0b8bc33d9f88bd1d39b18fdd14122d961b9b",
            "independent_result_sha256": sha(REVIEW / "A3_C6_RESULT.json"),
            "raw_rows_verified": 21371,
            "old_failed_parent_rows": 18871,
            "new_rows": 2500,
            "failed_parent_remains_failed": True,
            "eight_paired_estimates_and_intervals_reproduced": True,
            "reviewer_numpy": "2.5.3",
            "original_numpy": "2.2.6",
            "reviewer_ran_vllm_or_math_verify": False,
            "reviewer_rechecked_base_nocue_greedy_per_question_lineage_in_this_packet": False,
            "notes": [
                "The reported permissive GSM parser is an additional reviewer diagnostic, not a changed frozen endpoint or primary method.",
                "The parser-dependent difference is not a causal fraction attributable to formatting. No new symmetric greedy comparison is established.",
                "One reported numerical-tolerance false-positive sample, numeral-base/percent boundary cases and seven parse-failure statuses retain original labels.",
                "All eight original pointwise conditional intervals remain unchanged; no equivalence or training-seed population claim.",
                "C6 report references to Claude-owned Z1 are not incorporated into this disposition.",
                "No independent private-checkpoint loading or human adjudication is claimed.",
            ],
        })
    else:
        value.update({
            "accepted_component": "Early dated Codex-owned number-trace assembly only; Claude-owned Z1 excluded",
            "manifest_members_checked_by_reviewer": 38,
            "trace_entries": 77,
            "trace_entries_independently_verified": 73,
            "local_only_trace_entries_not_independently_verified": 4,
            "report_read_mode": "Initial mixed report exposed embedded Z1 material; that section is excluded from subsequent processing and acceptance.",
            "embedded_Z1_exposure_disclosed": True,
            "Z1_accepted_by_Codex": False,
            "author_12_item_check_verified_by_Codex": False,
            "final_scheduled_freeze_accepted": False,
            "final_frozen_version_requires_A5": True,
            "scheduled_freeze_utc": "2026-10-21T19:00:00Z",
            "notes": [
                "Four local-only provenance entries were not independently verified by the reviewer.",
                "T1 retried_questions means K1 selected from attempts 2–4, excluding fallback; the dated notes supply the explicit definition.",
                "T3 GSM cue rows require the reported parser-sensitivity footnote, supplied separately without changing original CSV values.",
                "Original figure bytes were checked, not rerendered; original visual-check provenance remains separate.",
                "Original T4 intervals, all contrasts and the reviewer's correction to the O1 summary remain explicit; no winner-only selection.",
                "This early A5 does not certify the future scheduled freeze or any Claude-owned Z1 component.",
            ],
        })
    write_json(R / definition["private"], value)
    public = copy.deepcopy(value)
    public.pop("local_report_file")
    public["private_acceptance_sha256"] = sha(R / definition["private"])
    write_json(ACCEPT_DIR / definition["private"], public)
    acceptances.append(public)
    entry = requests[definition["request"]]
    entry["status"] = (
        "completed_early_A5_PASS_WITH_NOTES_final_freeze_A5_still_required"
        if definition["kind"] == "Z2"
        else "completed_actual_A3_PASS_WITH_NOTES"
    )
    entry.update({
        "review_commit": COMMIT,
        "review_report_sha256": definition["sha"],
        "review_read_confirmed_utc": UTC,
        "review_event_utc": history["author"]["date"],
        "acceptance_packet": str(ACCEPT_DIR),
        "post_audit_technical_notes": str(NOTES_DIR),
    })

write_json(ACCEPT_DIR / "REVIEWS.json", acceptances)
write_text(ACCEPT_DIR / "README.md", f"""# Actual E3/C6 A3 and early Z2 A5 dispositions

Recorded {UTC}. All three fixed Claude reports give PASS-WITH-NOTES. Their targets,
manifest hashes, original report hashes, actual commit events and read-confirmation
times are bound in REVIEWS.json. Approximate times printed in the reports are not
used as observation times.

- E3: 3,200 new rows, 1,600 reused rows and the saved descriptive metrics accepted.
- C6: all 21,371 rows, retained failed-parent lineage and all eight paired results accepted.
- Z2: early Codex-owned assembly accepted with 73/77 trace sources independently
  verified. Four local-only sources remain unverified by the reviewer. Final freeze A5 is outstanding.

The [dated technical notes](../{NOTES_DIR.name}/README.md) provide required field
definitions and parser-sensitivity disclosure without altering original data.
Original reports are linked in REVIEWS.json; original bytes remain preserved.

The A5 file unexpectedly contained a Claude-owned Z1 section. Its initial display
exposed that material; BOUNDARY_EXPOSURE.json records this failure of separation.
No original Z1 artifact was opened. The public projection excludes that entire
section, and no Codex acceptance of Z1 or of the author's checks is asserted.
Completed C7 is not repeated. No model, scorer, statistic or renderer ran here.
""")

field_definition = {
    "source_packet": "reports/p010_20261019/z2_number_trace_v1",
    "source_target": definitions[2]["target"],
    "source_file": "T1_COMPOSITION.csv",
    "source_column_unchanged": "retried_questions",
    "display_definition": "K1_selected_from_attempt_2to4",
    "meaning": "Number of questions whose selected usable K1 answer came from attempt 2, 3 or 4; fallback questions are excluded.",
    "not_the_number_of_all_first_attempt_failures": True,
    "original_CSV_and_values_unchanged": True,
    "source_review_sha256": definitions[2]["sha"],
}
diagnostic = {
    "source": "Claude C6 actual A3 additional diagnostic",
    "source_report_sha256": definitions[1]["sha"],
    "source_commit": COMMIT,
    "scope": "base GSM cue sampled mean; additional permissive parser, not frozen primary scoring",
    "frozen_rule_sampled": {"denominator_per_condition": 5276, "cue_correct": 2552, "no_cue_correct": 2008, "original_difference_pp": 10.31084154662623},
    "reviewer_reported_permissive_rule_sampled": {"denominator_per_condition": 5276, "cue_correct": 2661, "no_cue_correct": 2381, "approximate_difference_pp": 5.31},
    "new_Codex_parser_run": False,
    "new_Codex_score_or_statistic": False,
    "symmetric_permissive_greedy_comparison_available": False,
    "frozen_scores_labels_and_intervals_unchanged": True,
    "causal_format_fraction_established": False,
    "notes": [
        "This is a reviewer-reported sensitivity diagnostic, not an alternative calibrated endpoint or a replacement primary result.",
        "No-cue greedy raw text was not in the C6 packet; no symmetric permissive greedy effect is asserted.",
        "No Z1 numbers or labels are used here.",
    ],
}
# Copy the already-saved exact primary number rather than inventing extra precision.
paired = read(P / "c6_analysis_v1/GSM_SAMPLED_MEAN_PASS_AT_1_PAIRED.json")
diagnostic["original_paired_source_sha256"] = sha(P / "c6_analysis_v1/GSM_SAMPLED_MEAN_PASS_AT_1_PAIRED.json")
diagnostic["frozen_rule_sampled"]["original_difference_pp"] = c6_result["paired_theirs"]["gsm/sampled_mean_pass_at_1/base_gsm"][0]
diagnostic["frozen_rule_sampled"]["precision_note"] = "Reviewer result JSON prints six decimals; original full-precision file remains authoritative."
write_json(NOTES_DIR / "T1_FIELD_DEFINITION.json", field_definition)
write_json(NOTES_DIR / "GSM_PARSER_SENSITIVITY_DISCLOSURE.json", diagnostic)
write_text(NOTES_DIR / "README.md", f"""# Dated technical footnotes after actual audit

Recorded {UTC}; based on the [actual review disposition](../{ACCEPT_DIR.name}/README.md).
This is audit metadata and table documentation, not interpretive course prose.
Original tables, images, labels and interval files remain unchanged.

## T1 field definition

In [T1_COMPOSITION.csv](../z2_number_trace_v1/T1_COMPOSITION.csv),
`retried_questions` means **K1 selected from attempts 2–4**, excluding fallback
questions. It is not the count of all unavailable first attempts. Display it as
`K1_selected_from_attempt_2to4` or carry this footnote beside the original heading.
All four cancelled K4/K8 cells remain cancelled and unattempted.

## T3 / C6 GSM parser sensitivity

The frozen sampled cue-minus-no-cue result is +10.31 pp. Claude's additional
permissive-parser diagnostic reports approximately +5.31 pp on the same sampled
conditions (2,661 versus 2,381 correct, each out of 5,276). These are reviewer
diagnostic values, not a replacement primary score or a causal formatting share.
The original counts, all eight intervals and all frozen labels remain unchanged.
A symmetric permissive greedy contrast was not established. No Z1 values are used.
See GSM_PARSER_SENSITIVITY_DISCLOSURE.json and the fixed C6 report.

## Other retained audit limits

- E3: capped UTF-8 boundary differences and the reported numeral-base boundary
  case retain original stop decisions and labels; old T0.8 rows were not rescored.
- C6: the reported single sampled numerical-tolerance false positive, numeral-base
  and percent cases, and explicit parse failures remain disclosed without relabeling.
- Intervals are pointwise conditional results, not familywise coverage, equivalence,
  a seed-population bound or a mechanism.
- Use every original T4 contrast. The reviewer corrected its earlier O1 summary;
  no contrast is selected or recomputed in this handoff.
- Early Z2 A5 verified 73 trace sources; four local-only sources were not independently
  verified. Images were byte-compared, not rerendered by the reviewer.
- Z1 remains Claude-owned. Unexpected embedded content exposure is recorded in
  the acceptance packet; Codex does not adopt its labels or claim the owner's checks.

## Scheduled freeze

This addendum does not perform the scheduled 2026-10-21 12:00 PDT (19:00 UTC)
freeze. The actual frozen version and this footnote linkage must be submitted for
final A5, as requested by the reviewer.
""")
write_json(NOTES_DIR / "SOURCE_BINDING.json", {
    "report_commit": COMMIT,
    "E3_report_sha256": definitions[0]["sha"],
    "C6_report_sha256": definitions[1]["sha"],
    "Z2_report_sha256": definitions[2]["sha"],
    "T1_CSV_sha256": sha(P / "z2_number_trace_v1/T1_COMPOSITION.csv"),
    "T3_CSV_sha256": sha(P / "z2_number_trace_v1/T3_CUE_ALL8_PAIRED.csv"),
    "scope": "Metadata/footnotes only; immutable scientific sources not changed.",
})

handoff = {
    "created_utc": UTC,
    "status": "ALL_LOCAL_SCIENCE_AND_ACTUAL_RESULT_AUDITS_CLOSED_EARLY_MATERIALS_ACCEPTED_FINAL_FREEZE_A5_OUTSTANDING",
    "new_scientific_work_authorized_by_this_handoff": False,
    "active_scientific_GPU_CPU_from_original_closeouts": 0,
    "all_failed_parents_and_exceptions_retained": True,
    "original_results_immutable": True,
    "E3_actual_A3": "PASS-WITH-NOTES",
    "C6_actual_A3": "PASS-WITH-NOTES",
    "Z2_early_A5": "PASS-WITH-NOTES; Codex-owned component only",
    "Z1": "Claude-owned; no Codex numeric acceptance or author-check claim",
    "embedded_Z1_exposure_disclosed": True,
    "scheduled_freeze_utc": "2026-10-21T19:00:00Z",
    "scheduled_freeze_local": "2026-10-21 12:00 America/Los_Angeles",
    "freeze_already_performed": False,
    "final_frozen_version_A5": "NOT_YET_REQUESTED_BEFORE_ACTUAL_FREEZE",
    "monitor_should_remain_active": True,
    "billing_observation_utc": "2026-10-20T12:51:38.852582+00:00",
    "delayed_workspace_gross_USD": 302.93554409,
    "observed_P010_description_rows_USD": 55.23443347,
    "observed_P010_rows": 30,
    "cash_billed_USD": 0,
    "meter_is_final_invoice_or_balance": False,
    "P010_prefix_scope_may_omit_unlabelled_setup_build_storage_lag": True,
    "effective_reservations_USD": {"G": 35.16, "T": 108.33, "I": 14.68, "C": 0},
    "reservations_are_actual_expense": False,
    "caps_USD": {"total": 240, "G": 50, "T": 150, "I": 15, "C": 25, "protected": 43},
    "accepted_D1_reservation_adjustments_USD": [19.97, 2.27],
    "adjustments_are_refunds": False,
    "new_billing_or_provider_request": False,
}
write_json(HANDOFF_DIR / "STATUS.json", handoff)
write_text(HANDOFF_DIR / "README.md", f"""# P010 technical handoff — 2026-10-20

All retained scientific runs, local proofs and actual result audits are closed.
E3 and C6 actual A3, and the early Codex-owned Z2 assembly A5, are
**PASS-WITH-NOTES**. No scientific GPU/CPU remains active according to the saved
original closeouts. This is an early dated handoff, not the scheduled freeze.

| Material | Fixed source | Current status |
|---|---|---|
| E3 temperature supply | [Complete evidence]({REPO}/blob/{definitions[0]['target']}/reports/p010_20261019/e3_complete_results_v1/README.md) | Actual A3 accepted; 3,200 new and 1,600 unchanged reused outputs |
| C6 cue endpoints | [Complete evidence]({REPO}/blob/{definitions[1]['target']}/reports/p010_20261019/c6_complete_results_v1/README.md) | Actual A3 accepted; 18,871 preserved plus 2,500 new outputs |
| C6 comparisons | [All eight saved comparisons]({REPO}/blob/{definitions[1]['target']}/reports/p010_20261019/c6_analysis_v1/README.md) | Original point estimates and conditional intervals retained |
| T1–T4 / F1–F2 | [Number-trace assembly]({REPO}/blob/{definitions[2]['target']}/reports/p010_20261019/z2_number_trace_v1/README.md) | Early A5 accepted with access limits; includes original E1/E1d/E4/E9/seed29 and P008 references |
| Required footnotes | [Dated technical notes](../{NOTES_DIR.name}/README.md) | T1 selection-count definition and GSM parser sensitivity |
| Audit evidence | [Exact dispositions](../{ACCEPT_DIR.name}/README.md) | Fixed report/source/manifest hashes and limitations |
| Z1 | Claude-owned deliverable | Not adopted or verified by Codex; embedded-exposure record retained |

The original four T7/T72 K4/K8 cancellations, E5-to-E9 delegated scope change,
failed calls, approved output-only continuations and E4 evaluation-only repairs
remain in the linked original evidence. No failure is relabeled completed.
No old model, scorer, bootstrap, renderer or publisher was rerun for this handoff.

## Cost record

The last necessary observation, 12:51:38 UTC, shows whole-workspace delayed usage
of **$302.94** and **$55.23** across 30 P010-description rows. The latter is incomplete
attribution and may omit unlabelled/setup/build/storage/lag costs. Cash billed is
$0 in that observation. None of these is a final invoice or remaining balance.
Effective reservations G35.16/T108.33/I14.68/C0 are separate from expenditure.
The $240 cap and G50/T150/I15/C25 subcaps remain unchanged; retained failed-call
reservations are not treated as free or refunded.

## Remaining delivery

At **2026-10-21 12:00 PDT / 19:00 UTC**, capture the actual immutable technical
freeze from the already-saved tables/figures and dated footnotes, recording the
scheduled cutoff separately from the actual write time. Do not rescore, regenerate,
rerender or open Z1 artifacts. Submit the actual frozen version for final A5.
Pause the finite monitor only after that audit and final handoff are closed.

P010 is exploratory. This packet contains technical status, provenance and
numeric caveats, not AI-written course-report or slide interpretation.
""")
write_json(HANDOFF_DIR / "SOURCE_BINDING.json", {
    "acceptance_packet": str(ACCEPT_DIR),
    "technical_notes_packet": str(NOTES_DIR),
    "original_Z2_manifest_sha256": definitions[2]["manifests"]["z2_number_trace_v1"],
    "existing_billing_projection_sha256": sha(P / "z2_number_trace_v1/OBSERVED_P010_PREFIX_METER.json"),
    "all_completed_scientific_tools_not_repeated": True,
})

for directory in (ACCEPT_DIR, NOTES_DIR, HANDOFF_DIR):
    if directory == ACCEPT_DIR:
        shutil.copyfile(Path(__file__), directory / "record_reviews.py")
    members = {
        str(path.relative_to(directory)): {"sha256": sha(path), "bytes": path.stat().st_size}
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }
    write_json(directory / "MANIFEST.json", {
        "schema": "p010-dated-metadata-manifest-v1",
        "created_utc": UTC,
        "files": members,
        "new_scientific_computation": False,
    })

# INDEX and ordinary narrative logs are mutable; immutable packets above are not.
index["last_updated_utc"] = UTC
INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
for path, relative_base in [
    (Path("README.md"), "reports/p010_20261019/"),
    (P / "README.md", ""),
]:
    prefix = f"""# Current P010 — actual result audits accepted; scheduled freeze remains

[Dated technical handoff]({relative_base}{HANDOFF_DIR.name}/README.md),
[exact E3/C6 A3 and early Z2 A5 dispositions]({relative_base}{ACCEPT_DIR.name}/README.md)
and [required table footnotes]({relative_base}{NOTES_DIR.name}/README.md) are available.
All retained scientific work is closed. The actual 2026-10-21 12:00 PDT freeze and
its final A5 remain outstanding. Original tables and labels are unchanged.
The mixed A5 report unexpectedly exposed a Claude-owned Z1 section; this is
recorded explicitly. No original Z1 artifact was opened, and Codex does not
adopt its values or claim independent verification of the owner's checks.

--- Earlier dated entries ---

"""
    path.write_text(prefix + path.read_text())

log = f"""
### {PDT} — Actual E3/C6 A3 and early Z2 A5 accepted; dated technical handoff

Fixed Claude f04922a reports E3/C6/Z2 PASS-WITH-NOTES were read and bound to their
exact targets/manifests. File-commit events are14:06:20/14:11:30/14:14:08UTC;
approximate header labels are retained separately and are not observation times.
E3 raw/old-T08 reuse and descriptive metrics, all21371 C6 rows and eight saved
paired estimates/intervals are accepted. Reviewer did not run vLLM/math-verify;
base no-cue greedy per-question lineage was not rechecked in this packet.
Early Z2 A5 independently verified73/77 trace sources; four local-only references
remain unverified. Actual scheduled Oct21 19UTC freeze/finalA5 still outstanding.

The read-only A5 report unexpectedly included a Claude-owned Z1 section. Initial
full display exposed summary/label information before separation; original Z1
files were not fetched/opened. An explicit incident record preserves this fact,
all subsequent projections exclude the section, no values are adopted, and no
claim of continued blindness or owner12-item verification is made. C7 is not rerun.
Future mixed reports must be section-screened before model-visible rendering.

Dated metadata notes define T1 retried_questions as selected K1 attempts2–4,
excluding fallback, and disclose reviewer GSM parser sensitivity10.31→about5.31pp
as an additional diagnostic, not a primary replacement or causal formatting
fraction. Original label/parse/tolerance/UTF8 caveats and all contrasts remain.
No scientific calls, scoring, statistics, renderer, old validation or paid requests.
An overbroad filename search accidentally matched hash substrings and produced
noisy filenames only; no artifact contents or scientific work were executed.

Last necessary delayed meter302.93554409 workspace and55.23443347 P010-description
rows is retained, with incomplete attribution/invoice limits. Effective reservations
are separate and no new release or budget change occurred. The finite monitor
continues only for dated delivery and the real scheduled freeze/finalA5.
"""
for name in [
    "docs/WORKBOARD.md",
    "reports/sft_allocation_midpoint_20261011/RUN_LOG.md",
    "AI_USE_LOG.md",
]:
    with Path(name).open("a") as handle:
        handle.write(log)

write_json(R / "F04922A_AUDIT_DISPOSITION_COMPLETED.json", {
    "utc": UTC,
    "report_commit": COMMIT,
    "public_packets": [str(path) for path in (ACCEPT_DIR, NOTES_DIR, HANDOFF_DIR)],
    "new_members": {
        str(path): len(read(path / "MANIFEST.json")["files"])
        for path in (ACCEPT_DIR, NOTES_DIR, HANDOFF_DIR)
    },
    "actual_E3_A3": "PASS-WITH-NOTES",
    "actual_C6_A3": "PASS-WITH-NOTES",
    "early_Z2_A5": "PASS-WITH-NOTES",
    "scheduled_freeze_and_final_A5": "OUTSTANDING",
    "embedded_Z1_exposure_disclosed": True,
    "new_scientific_computation": False,
})
print(json.dumps(read(R / "F04922A_AUDIT_DISPOSITION_COMPLETED.json")))
