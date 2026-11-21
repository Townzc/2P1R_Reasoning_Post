# A10 S1 first batch and overlength decision

S1 has stopped after its first complete600-question batch. All4800 model outputs, labels, qualification records, input identities and hashes are bound in INPUT_MANIFEST.json.501questions qualify, with2004 selected solutions. All seeds and sequence IDs are distinct; no question has eight identical outputs. The818 saved outputs from the connection-failed attempt match the complete retry in both text and tokens. Token cost of the complete attempt:USD4.435845321; the original attempt retains itsUSD24.3112068reserve pending API settlement.

Four selected solutions on three questions exceed A10section1.3training length4096:

| Source record | Draw | Full training tokens |
|---|---:|---:|
| logiqa/train/00091 | 6 | 4276 |
| logiqa/train/02851 | 0 | 4236 |
| logiqa/train/07270 | 4 | 4115 |
| logiqa/train/07270 | 5 | 4185 |

No frozen selection, label or output has been altered. No second batch or A10training has started. Generation and evaluation remain at4096 output tokens.

Recommendation for owner/Claude: allow an8192 training-length guard only for LogiQA, preserving the frozen first-four-distinct-correct rule. Proposed source is isolated and unapplied. CPU rendering of all2004selected solutions passes; the2000already within4096 produce identical tokens and masks. The maximum frozen available prompt is578tokens, so prompt plus4096generated tokens is at most4674. The proposal raises the local validation bound, without padding or truncating the stored sequences. Other tasks retain4096.

Alternative diagnostic, not applied: choosing the first four correct unique solutions that fit4096 would drop two of the three affected questions and change the selected draws for the third. Full eight-draw length/label evidence is in DIAGNOSTIC.json. This would change the frozen selection rule.

Please independently review the complete first batch and the overlap comparison, and give the length-policy decision or amendment. The eventual complete selected data, nesting/dose checks and training-path diff still go through the planned combined pretraining review. A9queues continue independently.

A publication-only path bug after generation was fixed before scoring; it caused zero extra model calls. Both failed-attempt and publication-fix evidence are retained. All results remain exploratory outside H0–H3.
