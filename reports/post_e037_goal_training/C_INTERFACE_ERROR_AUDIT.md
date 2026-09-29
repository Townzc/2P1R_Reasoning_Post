# C-interface error audit: all 13 failures

This independent CPU audit replayed all **288 C greedy scores** (96 per state), matched them exactly to the raw outputs and core analysis, and manually inspected **every one of the 13 failures**. All failures completed and supplied a parseable, incorrect final value. No model calls, added generations, score changes, or edits to the core analysis were made. C asks for the value of the supplied expression; a locally true trace that changes that expression still fails.

| State | Strict correct | Failures | False local equality | Grouping | Reversed subtraction | Literal substitution | Other program change |
|---|---:|---:|---:|---:|---:|---:|---:|
| E031 | 89/96 | 7 | 5 | 2 | 0 | 0 | 0 |
| G-single | 92/96 | 4 | 0 | 0 | 2 | 1 | 1 |
| G-paired | 94/96 | 2 | 0 | 0 | 1 | 0 | 1 |

**Interpretation.** All six failures after training contain correct displayed local equalities but compute an altered program. Three reverse a subtraction, one substitutes a number, one adds a subtraction after first reaching the correct answer, and one inserts an operation and reuses an input. The baseline has five explicit false equalities and two grouping changes. These are descriptive observations from a small, shared set of 48 groups; they do not establish why training changed behavior or estimate a general failure taxonomy.

**Conservative classification.** Primary categories are exclusive for counting, but causes may overlap. E031 g037/t1 also changes division grouping despite being counted under its explicit false equality. In G-single g032/t1, both earlier steps produce 2; the provenance of the extra subtracted 2 cannot be determined. An inferred expression transcribes displayed operations and does not claim to recover an internal program. A false equation compatible with omitting a number is not automatically labeled an omission.

The JSON retains the complete original expressions, responses, exact values, equation checks, frozen strict scores, automatic candidates, manual annotations, and source SHA-256 bindings. The [annotation table](C_INTERFACE_ERROR_ANNOTATIONS.json) preserves the manual decision independently; [structured audit](C_INTERFACE_ERROR_AUDIT.json) contains the validated result. The original [core analysis](REPORT.md) and scores remain unchanged.

## Complete review

Identifiers below abbreviate the common `goal_train_v1_eval_` prefix. Every record has sample index 0 and native-EOS completion.

### 1. E031 · g006_t1_C

Original: `((9 - (1 - 39)) + 40)` = **87**; returned **9**. Classification: **Changed grouping**.

```text
Step 1: 9 - 1 = 8.
Step 2: 8 - 39 = -31.
Step 3: -31 + 40 = 9.
Answer: 9
```

Displayed-program transcription: `(((9 - 1) - 39) + 40)` = 9.

The original inner subtraction is1-39; displayed left-to-right9-1 then minus39 changes grouping. All displayed equalities are exact.

### 2. E031 · g007_t0_C

Original: `((5 + (27 - 12)) + 38)` = **58**; returned **57**. Classification: **False local equality**.

```text
Step 1: 5 + (27 - 12) = 19.
Step 2: 19 + 38 = 57.
Answer: 57
```

5+(27-12)=20, so the displayed19 is an explicit false equality. Do not infer an omitted input or latent program from this alone.

### 3. E031 · g007_t1_C

Original: `((5 - (27 - 12)) + 38)` = **28**; returned **4**. Classification: **Changed grouping**.

```text
Step 1: 5 - 27 = -22.
Step 2: -22 - 12 = -34.
Step 3: -34 + 38 = 4.
Answer: 4
```

Displayed-program transcription: `(((5 - 27) - 12) + 38)` = 4.

Original5-(27-12)=-10; trace instead computes(5-27)-12=-34. All displayed local equations are exact.

### 4. E031 · g016_t0_C

Original: `((20 + (33 - 1)) / 2)` = **26**; returned **16**. Classification: **False local equality**.

```text
Step 1: 20 + (33 - 1) = 32.
Step 2: 32 / 2 = 16.
Answer: 16
```

20+(33-1)=52, not32. Returning the inner32 is compatible with dropping20, but the displayed equation explicitly retains20; the warranted category is false local arithmetic.

### 5. E031 · g016_t1_C

Original: `((20 + (33 - 1)) + 2)` = **54**; returned **34**. Classification: **False local equality**.

```text
Step 1: 20 + (33 - 1) = 32.
Step 2: 32 + 2 = 34.
Answer: 34
```

Same explicit false equality:20+(33-1)=52, not32. No separate claim about the internal cause.

### 6. E031 · g037_t1_C

Original: `((39 / (9 / 3)) * 6)` = **78**; returned **8**. Classification: **False local equality**.

```text
Step 1: 39 / 9 = 4.
Step 2: 4 / 3 = 4/3.
Step 3: 4/3 * 6 = 24/3 = 8.
Answer: 8
```

39/9=13/3, not4. The trace also begins with39/9 then divides by3, unlike the original39/(9/3). The final chained equality4/3*6=24/3=8 is mathematically true but outside the conservative one-equality parser. Primary category remains the explicit false first equation.

### 7. E031 · g042_t0_C

Original: `((40 + (5 - 15)) / 2)` = **15**; returned **10**. Classification: **False local equality**.

```text
Step 1: 40 + (5 - 15) = 20.
Step 2: 20 / 2 = 10.
Answer: 10
```

40+(5-15)=30, not20. The displayed second division is true for the wrong intermediate.

### 8. G-single · g013_t1_C

Original: `((18 + (34 - 31)) + 9)` = **30**; returned **24**. Classification: **Reversed subtraction**.

```text
Step 1: 31 - 34 = -3.
Step 2: 18 + (-3) = 15.
Step 3: 15 + 9 = 24.
Answer: 24
```

Displayed-program transcription: `((18 + (31 - 34)) + 9)` = 24.

The supplied34-31 is reversed to31-34. The connected displayed program gives24 exactly, but the original gives30.

### 9. G-single · g032_t1_C

Original: `(34 - (4 - (3 - 1)))` = **32**; returned **30**. Classification: **Additional operation / program change**.

```text
Step 1: 3 - 1 = 2.
Step 2: 4 - 2 = 2.
Step 3: 34 - 2 = 32.
Step 4: 32 - 2 = 30.
Answer: 30
```

Displayed-program transcription: `((34 - (4 - (3 - 1))) - 2)` = 30.

The first three steps correctly compute the supplied expression to32. Step4 adds an unsupported subtraction of2, producing30. Both steps1 and2 produced2, so which earlier value was reused is ambiguous. The inferred program transcribes the displayed extra scalar2 without claiming its provenance.

### 10. G-single · g034_t0_C

Original: `(20 - (9 - (28 - 21)))` = **18**; returned **11**. Classification: **Input literal substituted**.

```text
Step 1: 21 - 21 = 0.
Step 2: 9 - 0 = 9.
Step 3: 20 - 9 = 11.
Answer: 11
```

Displayed-program transcription: `(20 - (9 - (21 - 21)))` = 11.

The innermost28-21 becomes21-21;28 is replaced by a second21 in the displayed connected computation. It evaluates to11 rather than the original18.

### 11. G-single · g036_t0_C

Original: `(34 + (24 - (20 - 23)))` = **61**; returned **55**. Classification: **Reversed subtraction**.

```text
Step 1: 23 - 20 = 3.
Step 2: 24 - 3 = 21.
Step 3: 34 + 21 = 55.
Answer: 55
```

Displayed-program transcription: `(34 + (24 - (23 - 20)))` = 55.

The supplied20-23 is reversed to23-20, yielding55 instead of61. All three local equations are true.

### 12. G-paired · g034_t0_C

Original: `(20 - (9 - (28 - 21)))` = **18**; returned **39**. Classification: **Additional operation / program change**.

```text
Step 1: 21 - 21 = 0.
Step 2: 28 - 0 = 28.
Step 3: 9 - 28 = -19.
Step 4: 20 - (-19) = 39.
Answer: 39
```

Displayed-program transcription: `(20 - (9 - (28 - (21 - 21))))` = 39.

The trace adds21-21 as a new innermost step, then uses28-0. This connected displayed program reuses21 and changes the original program; it gives39, not18. This is not merely a subtraction reversal or a single literal substitution.

### 13. G-paired · g036_t0_C

Original: `(34 + (24 - (20 - 23)))` = **61**; returned **55**. Classification: **Reversed subtraction**.

```text
Step 1: 23 - 20 = 3.
Step 2: 24 - 3 = 21.
Step 3: 34 + 21 = 55.
Answer: 55
```

Displayed-program transcription: `(34 + (24 - (23 - 20)))` = 55.

The supplied20-23 is reversed to23-20, yielding55 instead of61. All three local equations are true.

## Scope and reproducibility

Review is exhaustive for failures, not an audit of every intermediate line in the 275 successful C responses. The original scorer checks C final-value correctness; this supplement leaves that contract intact. Exact rational arithmetic avoids floating-point classification. Unsupported equation syntax is marked separately and read manually. No hidden computation is observable from these traces.

Source file hashes and the private CPU audit implementation hash are recorded in the structured audit. A standalone check needs the frozen release, the three public C JSONL files, core scored outputs, and annotation table named there. The supplemental audit is outside the original core manifest and is intended for a separate supplemental manifest.
