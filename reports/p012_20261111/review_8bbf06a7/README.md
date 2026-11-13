# Accepted review 8bbf06a7 and owner-approved Amendment5

T-1 adds the double-wrapper guard and reuses frozen C7 conversations for pre-training generation. T-2 uses repository-relative local inputs/assets in new requests. Historical artifacts are unchanged. Real C6 holdout500 problems are raw; training/NLL problems are wrapped. Both wrapper spellings are rejected when passed without messages. All5,638 frozen C7 conversation rows pass unchanged.

B-1 changes bridge alpha64→32; B-2 removes lm_head, retaining seven attention/MLP modules. The previous review packet's tied-head vLLM support claim was incorrect; the accepted correction is now implemented. The bridge manifest records its output-head difference from Tinker. Expected trainable parameters36,929,536. L first; first20 adapter/base comparison; fullL cap>25percent stops remainingbridge. No extra low-LR bridge requested.

A5 changes only the CELLS dose table in the full-parameter training/evaluation path. Frozen nested subsets are included with their exact hashes and C6 source bindings. All14newcells are exploratory, onlytwoQwenMATHinitializations, seed17, excludedfromH0–H3. A5-1 adds the two frozen Instruct baseline0 endpoints. Existing trainingconfig/input tests pass31cases, including allapproveddoses.

`PREDICTION_FREEZE.json` records the actualreview/predictioncommit before anyformalTinker/bridge/A5run. Tpretraining usesMATH500 baselines andheldout500x8. Posttraining usesfullMATH5000 withnestedMATH500. Existing scoring andterminationcode unchanged. Formalorder: premeasurement→L,P,R→K8→K4; percell originaloutputandusage saved.

`MODAL_BATCH_ADMISSION.json` covers A5 plus conditionalbridge under actualbalance-minus4. Phasecaps soft. R3/E2held. No review round remains for theseacceptedfixes.
