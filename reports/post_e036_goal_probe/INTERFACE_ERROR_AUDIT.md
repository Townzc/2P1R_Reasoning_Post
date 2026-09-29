# Independent interface error audit

CPU-only post-hoc review of all 960 H outputs and 192 C outputs. All 1,152 stored score objects exactly match a fresh call to the frozen scorer; raw records exactly match the existing analysis rows. Strict scores and original files are unchanged.

| State | Decoding | H n | Correct | Wrong hole with template followed | Unfilled ? | Unbalanced parentheses | Other parse | Resource edits | Tree/order edits | Fixed-operator edits | Incomplete |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C-S | greedy | 48 | 10 | 22 | 14 | 0 | 0 | 1 | 1 | 0 | 0 |
| C-S | sampled | 192 | 33 | 79 | 56 | 10 | 1 | 2 | 8 | 2 | 1 |
| C-P | greedy | 48 | 10 | 19 | 13 | 0 | 0 | 2 | 2 | 1 | 1 |
| C-P | sampled | 192 | 41 | 70 | 48 | 9 | 3 | 6 | 12 | 3 | 0 |
| B-S | greedy | 48 | 10 | 21 | 12 | 0 | 0 | 0 | 3 | 1 | 1 |
| B-S | sampled | 192 | 43 | 71 | 54 | 6 | 3 | 1 | 10 | 4 | 0 |
| B-P | greedy | 48 | 11 | 21 | 10 | 0 | 0 | 2 | 2 | 2 | 0 |
| B-P | sampled | 192 | 42 | 65 | 50 | 9 | 1 | 4 | 18 | 3 | 0 |

Across 960 H outputs: 200 strict correct, 368 follow the template but select the wrong hole operator, 299 parse failures, 90 parsed template violations, and 3 incomplete stops.
Retaining '?' in the final Answer is the main parse failure (257); numeric-only answers account for 0 parsed template violations. The full JSON retains overlapping flags, every H segment, and every C failure.

| State | C n | Correct | Wrong final value | False local equation | Locally true equations, wrong original-expression evaluation |
|---|---:|---:|---:|---:|---:|
| C-S | 48 | 43 | 5 | 0 | 5 |
| C-P | 48 | 45 | 3 | 0 | 3 |
| B-S | 48 | 44 | 4 | 1 | 3 |
| B-P | 48 | 47 | 1 | 0 | 1 |

The 13 C failures divide further as follows. These are descriptive trace readings; all 12 inferred changed programs were independently exact-evaluated and equal the returned wrong answer.

| State | Reversed subtraction | Replaced input | Omitted input/changed program | Changed grouping | False local subtraction |
|---|---:|---:|---:|---:|---:|
| C-S | 2 | 1 | 1 | 1 | 0 |
| C-P | 3 | 0 | 0 | 0 | 0 |
| B-S | 1 | 1 | 1 | 0 | 1 |
| B-P | 1 | 0 | 0 | 0 | 0 |

Of the 257 H answers retaining `?`, 180 copy the exact original template after removing whitespace. The other six syntax failures comprise two trailing full stops, three missing operators rendered as implicit function calls, and one `!=` comparison. Both missing-marker cases give an answer expression in prose without the required `Answer:` line. These details remain post-hoc descriptions; no repair is scored.

All 13 C failures are genuine wrong evaluations of the supplied expression, not answer-format false negatives. Twelve have individually true displayed equations: common traces reverse a subtraction, replace/omit an input, or change grouping. One has an explicitly false local equality. Thus “locally consistent arithmetic” must not be described as correctly evaluating the original expression.

## Representative evidence

1. `B-P_H_greedy` / `goal_v1_g05_t0_H` / sample0: `parse_unfilled_question_mark`.
   Template `(11 + ((4 ? 22) - 27))`, target72, expected operator `*`.

```text
Step 1: 4 ? 22 = 8.
Step 2: 11 + 8 = 19.
Step 3: 19 - 27 = -8.
Answer: ((11 + (4 ? 22)) - 27)
```

2. `B-P_H_greedy` / `goal_v1_g09_t0_H` / sample0: `template_tree_or_leaf_order_changed`.
   Template `(23 + (36 ? (22 - 40)))`, target21, expected operator `/`.

```text
Step 1: 40 - 22 = 18.
Step 2: 36 * 18 = 648.
Step 3: 648 / 23 = 28.
Answer: ((36 * (40 - 22)) / 23)
```

3. `B-P_C_greedy` / `goal_v1_g03_t0_C` / sample0: `wrong_value_with_true_local_equations`.
   Supplied `((29 - (25 - 36)) + 7)` = 47; returned 25.

```text
Step 1: 36 - 25 = 11.
Step 2: 29 - 11 = 18.
Step 3: 18 + 7 = 25.
Answer: 25
```

4. `B-S_C_greedy` / `goal_v1_g06_t0_C` / sample0: `wrong_value_with_false_local_equation`.
   Supplied `(2 + (11 - (24 - 32)))` = 21; returned 22.

```text
We now calculate: 24 - 32 = -9.
We now calculate: 11 - (-9) = 20.
We now calculate: 2 + 20 = 22.
Answer: 22
```

## Implication for the next proposal

Preserve all strict metrics. H failures include substantial copying/format problems and substantial valid-template wrong-operator choices; neither alone identifies target knowledge. C errors require checking the supplied ordered computation, including signs and grouping, rather than only local arithmetic equalities. A future separately authorized intervention can teach full-expression hole completion and paired targets while holding the program scaffold fixed, then test transfer on fresh free-construction and paired-goal instances. Do not repair or reuse these same outputs as new evidence.

This audit adds no model calls, generations, training, or new independent groups. Source hashes and all per-output evidence are in `INTERFACE_ERROR_AUDIT.json`.
