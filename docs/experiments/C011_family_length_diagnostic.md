# C011 — Separate within-family length support from cross-family length equality

**Registered 2026-09-09 UTC before these CPU outcomes.** C009 showed that all
large targets disappear at its token stage, before the structure constraint.
That does not reveal whether one family's same-length support already fails,
or whether requiring the two families' lengths to be equal creates the loss.

Use the unchanged C009 25,846-row tokenized archive, original 256 training
questions/targets, pinned tokenizer/serialization and K=4. Verify archive bytes
and provenance. No enumeration of new questions, development outcomes, model
inference, GPU execution or server connection is allowed in this entry.

Measure a fixed two-by-two table: common length across families versus a separate
length for each family, crossed with four-distinct-structures requirement off
versus on. Every cell still requires four different AC classes per family and
eight different classes jointly. At each length or ordered length pair use
complete Hall/class checks and a separate NetworkX flow test for structures.
Report all feasible length pairs, each family's individual candidate lengths,
explicit structure witnesses and per-question IDs, not only support counts.
Changing lengths here is a CPU constraint ablation, not a claim of equal training
dose across families. Verify that the common-length cells reproduce C009's
67 class-feasible and 66 structure-feasible questions.

Describe each branch relative to the original 256 and its own preceding stage:
target at least41, input1, consecutive pairs, target equal to an input or its
successor, and the explicitly defined four-input preview template. Report
zero-denominator strata as unavailable. These descriptors are post-C009
selection diagnostics; none is used to choose a favorable model result.

Do not run the optional per-family global join in this entry. C010 completes
the original common-length design; C012 separately tests the absent-only
training candidate. A larger support count here alone neither establishes a
trainable block population nor a pure identity mechanism. The user authorized
CPU preparation and deciding a training plan; no server is to be started.

**Outcome: pending.** Preserve source/config hashes, completion, all four counts,
selection and witnesses, runtime and zero added GPU seconds in a fresh directory.
