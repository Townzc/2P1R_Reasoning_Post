# Frozen-endpoint goal-switch diagnostic

Status: **all_registered_outputs_verified**. No training was performed.

| State | Interface | Decoding | Strict correct / outputs | Both targets correct / pairs |
|---|---|---|---:|---:|
| C-S | F | greedy | 2/48 | 1/24 |
| C-S | H | greedy | 10/48 | 2/24 |
| C-S | C | greedy | 43/48 | 21/24 |
| C-S | F | sampled | 5/192 | 1/96 |
| C-S | H | sampled | 33/192 | 2/96 |
| C-P | F | greedy | 3/48 | 1/24 |
| C-P | H | greedy | 10/48 | 0/24 |
| C-P | C | greedy | 45/48 | 22/24 |
| C-P | F | sampled | 8/192 | 1/96 |
| C-P | H | sampled | 41/192 | 2/96 |
| B-S | F | greedy | 1/48 | 0/24 |
| B-S | H | greedy | 10/48 | 1/24 |
| B-S | C | greedy | 44/48 | 21/24 |
| B-S | F | sampled | 6/192 | 0/96 |
| B-S | H | sampled | 43/192 | 2/96 |
| B-P | F | greedy | 3/48 | 1/24 |
| B-P | H | greedy | 11/48 | 0/24 |
| B-P | C | greedy | 47/48 | 23/24 |
| B-P | F | sampled | 8/192 | 0/96 |
| B-P | H | sampled | 42/192 | 1/96 |

Two targets and four stochastic samples are nested within each number group. Intervals resample groups and skeleton families, not individual outputs or training seeds. Missing views remain NA; invalid and truncated outputs stay in measured denominators.

F accepts any legal correct construction. H additionally requires the exact ordered template and its unique correct operator. C measures expression evaluation only. Template rescue changes difficulty and interface as well as search freedom; it does not identify an internal mechanism.

Operator scores are conditional on a supplied valid prefix. Raw full-vocabulary log probabilities, candidate total probability mass, and within-candidate normalized probabilities remain distinct. Correct ranking or positive D_goal alone does not establish free-generation competence.
