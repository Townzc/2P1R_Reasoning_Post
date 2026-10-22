"""Accept only the two already declared, byte-bound local endpoint links."""
from pathlib import Path
from experiments.sft_allocation_midpoint.common import sha, verify

ENDPOINTS = ("ENDPOINT_GPU.json", "ENDPOINT_LOCAL.json")
PASSED_PREFIX = ("ENCODED.jsonl", "ROW_METADATA.json", "RATES_S-F15.json")


def verify_inputs(root, files, prior_root, *, reuse_passed_prefix=False):
    root, prior_root = Path(root), Path(prior_root)
    if reuse_passed_prefix and tuple(files)[:3] != PASSED_PREFIX:
        raise ValueError("The recorded failed audit passed only the exact first three files")
    checked = []
    for name, record in files.items():
        if reuse_passed_prefix and name in PASSED_PREFIX:
            continue
        if name not in ENDPOINTS:
            verify(root, {name: record})
        else:
            p, expected = root / name, prior_root / name
            if (not p.is_symlink() or expected.is_symlink()
                    or not expected.is_file() or p.resolve(strict=True) != expected.resolve(strict=True)
                    or p.stat().st_size != record["bytes"] or sha(p) != record["sha256"]):
                raise ValueError("Exact original endpoint link and manifest bytes required: " + name)
        checked.append(name)
    return {"checked_in_this_continuation": checked,
            "reused_successful_prefix": list(PASSED_PREFIX) if reuse_passed_prefix else [],
            "links_materialized_or_reencoded": False}
