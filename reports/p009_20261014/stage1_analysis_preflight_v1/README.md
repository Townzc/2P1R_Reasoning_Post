# Stage1 registered decision and bootstrap code — before student outcomes

This pure local core freezes the previously unspecified quantile method as
NumPy linear before any P009 student is run. Use NumPy2.2.6, explicit PCG64,
seed20261014 and10000 paired-question bootstrap draws. Sort the complete frozen
question IDs lexicographically and resample the same IDs for both models.
Intervals are pointwise and conditional on observed model/data choices, not
simultaneous or training-seed/procurement-population guarantees. Both data order
and training randomness change between Stage1 seeds. Stage2 remains adaptive
on already-seen benchmark questions, with its separate later exact analysis.

This is not a worker, publisher, oracle or dispatch gate. It never parses raw
answers or symbolically scores. The future actual caller must bind independently
verified complete endpoints and the actual frozen IDs. NC requires1319 exact
Boolean verdicts and S1 requires500. Missing/extra/unknown/numeric verdicts are
rejected. Original HF638/969 never enter the functions; existing P009 vLLM NC650
is only background, not a substitute for either newly trained NC endpoint.

NC400/3200 seed17 comes first; a positive gap of at least5pp stops all positive
regimes and is not itself proof of an implementation bug. S2 is excluded by its
real cap failure. If S1 G0 fails, no eligible positive regime is a G0 stop, not a
measured small-gap/futility result. An admitted S1 first pair with gap strictly
below2pp triggers the original futility stop. Do not analyze unauthorized later
outcomes through this path after a stop. A4 external review remains required.

G1 requires all six registered S1 endpoints, seed17 gap>=5pp and strict positive
95% paired lower bound, plus seed29 gap>=2.5pp. The n100 and n1600 cells cannot
be silently omitted. n* uses the unchanged registered n1600-versus-n3200 one-pp
rule. G1 PASS here is not Stage2 admission; actual A5/source/input/budget/runtime
review remains. Existing gates.py historical100USD constants are unchanged and
not called for any budget admission by this module.

Nine new checks are covered: seven passed initially; the initial NC fixture
incorrectly treated66/1319 as below5% and the isolated math-only environment had
no NumPy. The fixture now uses65 versus66 and a separate pinned analysis-only
environment was installed. Only the two originally failed/error checks were
rerun and passed. The source gate was correct and unchanged; no old tests or
real experiment scores were rerun. Original private failure bytes and their
hashes remain, while public traceback host locators are explicitly projected.
