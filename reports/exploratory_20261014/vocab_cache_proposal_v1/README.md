# Unadmitted vocabulary-size cache proposal

The three original exploratory calls remain untouched. This packet is pure-CPU engineering preparation, not a new runtime/admission, continuation, cap change, or retry. No new model calls. The owner was asked whether to stop and preserve the original calls or keep their original6001-second limits; no answer has yet been received. There is no authorization for additional calls.

## Observed risk

At07:48:49UTC, completed original endpoint acknowledgments were base128 and Instruct32. Base's seven observed batch intervals were90/76/100/81/72/86/94seconds; the first Instruct interval was174seconds. These include work beyond generation. This creates a serious risk of an incomplete endpoint within6001seconds if it continues; it is not a guaranteed future rate. My earlier1–1.5hour completion estimate was too optimistic given this new evidence. No partial score was computed or used.

The live reference_event evaluates len(tokenizer) once per output token in the out-of-vocabulary set comprehension. Local Transformers4.56.2/tokenizers0.22.1 measured64lookups in0.405570833s (6.337ms/lookup). First saved base/instruct raw batches require3520/8192lookups respectively, implying22.306/51.913s from this lookup alone on the local host. The actual cloud lookup cost and full phase breakdown have not been profiled; do not treat these as calibrated worker predictions or the sole proven cause.

## Proposed change and evidence

Read len(tokenizer) once at the start of reference_event, then use that unchanged scalar in the comprehension. Tokenizer vocabulary is frozen throughout the function. Preserve normalization, special-token handling, complete-prefix boundary search, raw tokens and parser. PROPOSED_PATCH.diff has not been applied to the live file. The isolated proposal has no cloud entry or live monkeypatch.

Four new synthetic checks pass for alternate native EOS, boundary-before-EOS, out-of-vocabulary invalidity and the512-token cap. The proposal independently reconstructs32already-saved first-batch stop events exactly, approximately0.106s per16 on the local host. No gold/score comparison, token regeneration or full original oracle rerun. This is limited engineering evidence, not a full endpoint audit or cloud speed guarantee. All37active source bytes remain unchanged.

Any future executable release would need its own exact source/input/lineage/budget review and explicit owner authority under the once/no-retry restriction. Do not use this proposal to relabel current receipts, hot-modify the worker, discard failed attempts, or silently replay outputs.
