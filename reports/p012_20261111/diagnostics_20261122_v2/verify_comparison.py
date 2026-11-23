"""Compare published diagnostic artifacts by training run and preserve full-precision differences."""
from pathlib import Path
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
OLD = HERE.with_name("diagnostics_20261122_v1")
REF = Path("audit/claude/20261122c/CLAUDE_LAST64_REFERENCE.json")
FIELD = "last64_training_loss_mean"
REVIEW = "02713c9857f938b78df3af64aae62ff568d51264"


def read(p):
    return json.loads(p.read_bytes())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compare():
    assert digest(REF) == "e2ff9778414bce02a71640d71b3ae5fcc4fd0236f7c3e549f6b5d34ffed7c97e"
    assert digest(HERE / "build_table.py") == "06b7f17601fedada5f4a89d1497376da5d5700c4ee87a82b393768008d840665"
    baseline = read(OLD / "RESULTS.json")["rows"]
    current = read(HERE / "RESULTS.json")["rows"]
    reference = read(REF)
    assert len(baseline) == len(current) == len(reference) == 113
    ids = [r["run_id"] for r in current]
    assert ids == [r["run_id"] for r in baseline] and set(ids) == set(reference)
    comparisons = []
    for old, row in zip(baseline, current, strict=True):
        name = row["run_id"]
        assert {k: v for k, v in row.items() if k != FIELD} == old, (name, "old field changed")
        actual, independently_computed = row[FIELD], reference[name]
        error = abs(actual - independently_computed)
        assert math.isfinite(error) and error < 1e-9, (name, actual, independently_computed)
        comparisons.append(dict(run_id=name, value=actual, reference=independently_computed, absolute_difference=error))
    assert read(OLD / "INPUT_MANIFEST.json")["endpoints"] == read(HERE / "INPUT_MANIFEST.json")["endpoints"]
    assert (OLD / "CHECKS.json").read_bytes() == (HERE / "CHECKS.json").read_bytes()
    return dict(pre_use_review_commit=REVIEW, reference_sha256=digest(REF),
                original_result_sha256=digest(OLD / "RESULTS.json"),
                result_sha256=digest(HERE / "RESULTS.json"), verified_rows=len(comparisons),
                existing_fields_per_row=len(baseline[0]), old_fields_unchanged=True,
                maximum_absolute_difference=max(x["absolute_difference"] for x in comparisons), rows=comparisons)


if __name__ == "__main__":
    out = compare()
    (HERE / "REFERENCE_COMPARISON.json").write_text(json.dumps(out,indent=2)+"\n")
    print(out["verified_rows"],out["existing_fields_per_row"],out["maximum_absolute_difference"])
