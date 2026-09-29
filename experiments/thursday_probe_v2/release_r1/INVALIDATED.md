# CPU registration failure, retained before any model execution

The first v2 CPU preparation mistakenly scanned hexadecimal hashes as possible
experiment IDs and proposed E869–E875. These IDs were never registered as runs
or executed. All files remain byte-preserved for audit. `release_r2` fixes the
allocator to inspect identity fields only and reserves E030–E036 after the old
E019–E029 aliases. The arithmetic data, selections, dose and outcomes are not
changed; there were no model outputs in either CPU preparation.
