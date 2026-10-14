# P009 pre-claim entry failure, independently reconciled

Original call `fc-01M4Y5X0QZVYFXKX0RXQTPCX39` in app
`ap-AWwBuFC9C1MSINlMCioi5O` failed at the worker's `spec['inputs']`
lookup. The actual immutable admission stores that manifest under
`spec['parent_spec']['inputs']`. This was an entry-schema implementation defect,
missed by the earlier runtime tests and scoped review; it is not a parity result.

The full original ledger contains only the identical campaign registration:
zero claim, admission intent, attempted units, terminal or generated output.
The remote campaign directory is absent; the parent successor marker remains
absent. Original provider records before and after the full read establish all
three apps STOPPED with zero owned containers. No model was loaded. No failed
terminal is fabricated for a claim that never existed. All original callback,
source, log and provider bytes remain private with hashes; public actor metadata
is explicitly projected. The earlier saved256 raw rows are untouched.

The same unused scientific slot may only be admitted after a separately fixed
repair/source/input/numeric audit and a fresh complete absence check. A new
permanent dispatch marker prevents another call if its response is lost. No
claim is cleared. The failed cloud call still has a full252-cent allowance;
zero scientific work does not mean zero platform cost.
