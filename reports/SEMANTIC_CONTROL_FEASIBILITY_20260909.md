# Feasibility of an identity-based control using the current four-path inventory

**The proposed two-family construction has no shared support under its
at-least-two-paths-per-family requirement.** Among the 256 frozen training
problems, none has two identity-containing and two identity-free paths in its
existing four-path inventory. This rejects that specific reuse of the current
inventory; it does not establish that additional mathematical solutions do not
exist or that meaningful semantic alternatives cannot be constructed.

## Exact count from the frozen inventory

The labels are the previously defined numerical identity events: multiplication
by evaluated one, division by evaluated denominator one, addition of evaluated
zero, or subtraction of evaluated right operand zero. The count refers to
whether each selected path contains at least one such event. It is not a count
of all solutions to a problem, and it is not a semantic-strategy taxonomy.

| Identity-containing paths among the four selected paths | Problems |
|---|---:|
| 0 | 72 |
| 1 | 0 |
| 2 | 0 |
| 3 | 41 |
| 4 | 143 |
| Total | 256 |

- At least one identity-containing and one identity-free path: **41/256**.
- At least two identity-containing and two identity-free paths: **0/256**.
- Every mixed inventory is a **3-to-1** split: three identity-containing paths
  and only one identity-free path. The 41 mixed problems do not supply two
  distinct identity-free paths each.

These counts reconcile with the earlier structure audit: 184 problems have any
identity-containing reference, 143 have identity events in every reference, and
41 × 3 + 143 × 4 = 695 of 1024 selected paths contain an identity event. Problem
identities, block IDs, inputs, targets, prompts and selected path IDs were checked
between the frozen training blocks and their saved labels.

## What this rules out, and what it leaves open

If a candidate 2×2 study crosses path allocation with two families defined only
by identity presence, and requires at least two distinct paths in each family
for the same problem, the existing four-path stock cannot instantiate a single
qualifying problem. Repeating the sole identity-free path does not supply a
second distinct path; changing its sentence frame supplies surface variation,
not another arithmetic path. The weaker 41-problem one-per-family inventory
also does not prove feasibility of token, structural or difficulty matching.

In this task every supplied number must be used exactly once. An identity
operation may be how a valid solution incorporates a supplied one or a zero/one
computed from other inputs. Its presence does **not** make the solution invalid,
and the identity-containing family is **not** equivalent to the Surface arm.
Surface preserves equations and calculation order while changing sentence
frames; the candidate families here concern properties of actual arithmetic
programs. Both families can contain valid solutions under the task rules.

This is a bounded inventory check, not a new solver search or an impossibility
proof. It says nothing about unselected solutions for the same problems, other
training pools, a richer path taxonomy, or the validity of the broader research
question. It does show that this particular mechanism-control proposal needs a
new, explicitly reviewed construction rather than a relabeling of the frozen
four paths. No new pool was solved, no holdout or seed23 model results were read,
and no training data, configuration, primary endpoint or GPU plan was changed.

## Sources and exact reproduction

| Read-only source | SHA-256 |
|---|---|
| `runs/pilot_v1_20260908_r3/train_blocks.json` | `e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea` |
| `reports/pilot_v1_structure_bias_20260909/per_problem.jsonl` | `7ea6f0cb0b39a2df41440c49534b036ef4440953965943c6cb91cd67fe8dbdd0` |

Run this dependency-free code from the repository root. It reads only the two
listed artifacts and does not write or solve any data.

```python
from collections import Counter
import hashlib
import json
from pathlib import Path

sources = {
    'runs/pilot_v1_20260908_r3/train_blocks.json':
        'e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea',
    'reports/pilot_v1_structure_bias_20260909/per_problem.jsonl':
        '7ea6f0cb0b39a2df41440c49534b036ef4440953965943c6cb91cd67fe8dbdd0',
}
for name, digest in sources.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
blocks = json.loads(Path(next(iter(sources))).read_text())
label_path = Path('reports/pilot_v1_structure_bias_20260909/per_problem.jsonl')
training_labels = [json.loads(line) for line in label_path.read_text().splitlines()
                   if json.loads(line)['split'] == 'train']
labels = {row['problem_id']: row for row in training_labels}
assert len(training_labels) == len(labels) == 256
counts, seen = Counter(), set()
for block_id, block in enumerate(blocks):
    for item in block['problems']:
        problem = item['problem']
        pid = problem['problem_id']
        assert pid not in seen
        seen.add(pid)
        label = labels[pid]
        assert label['block_id'] == block_id
        assert all(problem[k] == label[k] for k in ('numbers', 'target', 'prompt'))
        assert len(item['paths']) == len(label['paths']) == 4
        assert len({p['path_id'] for p in item['paths']}) == 4
        assert {p['path_id'] for p in item['paths']} == {
            p['path_id'] for p in label['paths']}
        count = sum(p['has_identity_operation'] for p in label['paths'])
        assert count == label['reference_identity_path_count']
        counts[count] += 1
assert seen == set(labels)
assert sum(counts.values()) == 256
assert sum(k*v for k, v in counts.items()) == 695
print('identity_path_count_histogram:', {i: counts[i] for i in range(5)})
print('at_least_one_each:', sum(counts[i] for i in (1, 2, 3)))
print('at_least_two_each:', counts[2])
```

Expected output:

```text
identity_path_count_histogram: {0: 72, 1: 0, 2: 0, 3: 41, 4: 143}
at_least_one_each: 41
at_least_two_each: 0
```
