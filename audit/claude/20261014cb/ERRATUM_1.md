# Erratum 1 to 20261014cb (REPORT.md left unchanged; its SHA 8e27ab94… stays bound)

Part A, line 44 says the P0 endpoint intervals were eager-mode runs. That is wrong.
The completed 650-row P0 endpoint used enforce_eager=false with FULL_AND_PIECEWISE
CUDA graphs. That covers the fast 256 rows and the remaining 1063. The 128 eager rows
were excluded and never scored. This was already recorded in
review_448e0ac1_accepted_v1/DISPOSITION.md, and Codex's ff916e38 disposition is correct.

Effect: one of the two qualitative reasons I gave for why the 4,193 s scenario might
be conservative ("Stage 1 uses graphs, P0 was eager") does not hold. The only remaining
reason is that SFT students usually stop at EOS. The scenario number, the 18-host basis,
the 4,500 s cap and the PASS-WITH-NOTES decision did not depend on this sentence, so
none of them change. The ~277 s setup-headroom note gets more weight. I make no claim
that students will run faster than the scenario.
