# Accepted review8a8fac5c

All six endpoints/30000outputs, both concise constructions and the A7 analysis adapter passed. Original data,raw evidence and labels are unchanged. The accepted analysis commit is filled; first full execution waits only for all15endpoints.

4B M512 long.jsonl contains40 of512 rows with only a boxed answer and no reasoning;9B contains none. Interpret SC-1/SC-2 primarily using9B;4B is a repetition with this limitation. Frozen data,labels and predictions remain unchanged.

Tinker4B two-seed predictions: T1/T8 fail;T2/T2b/T3/T4/T5 pass. Values are copied from the independent audit,without rerunning statistics.
