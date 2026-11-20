# Audit 20261014bm — P0 remainder result publisher and read-only helper (code only)

| Request | Target | Manifest | Script |
|---|---|---|---|
| `p009-p0-fast-remainder-result-publication-code-r1` | `58a4f5111703f04467c0cc30484c379bcc134748` | `43ae81d8…` | `299c662b…` |
| `p009-p0-fast-remainder-readonly-code-r1` | `3ddfadfd46079fa60946a52d899c2a9caad60b3c` | `db542e32…` | `f9ffa532…` |

## Verdicts

**Both PASS-WITH-NOTES.**

**Publisher**
- Create-only archive (`xb`), with readback verification of the original-byte projection.
- Requires an oracle with `inherited_raw_count == 256`, `parent_acknowledgement_fabricated == False` and `old_reference_rescored == False`.
- Links the 256 inherited rows to the immutable failed-parent packet instead of copying them.
- No scoring or model path.

**Read-only helper**
- Same pattern as 20261014bk: `app info` / `container list` only, Dict reads, and create-only local preservation with fsync journaling.
- No delete, overwrite or remote write.

## Note

My A2 replays the 256 inherited rows from the parent packet (SHA `142defc1…`) plus all 2,382 child rows, independently of either tool.
