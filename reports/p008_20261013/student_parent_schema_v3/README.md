# P008 parent-to-student metadata adapter

Second local builder39991 stopped before output creation because the legacy SFT converter expects group_id. Frozen P008 eligible parents have exactlyid/problem/answer/reference. A new copy-only adapter suppliesgroup_id=id for each GSM8K question, leaves all original fields/teacher text unchanged, and delegates all score/attempt/duplicate/full-answer checks to the unchanged converter. No scientific filtering, dose, source runtime, teacher call or student call changed.

Five targeted new checks passed. Both prior local failures and their zero-output scopes are retained. v3 preparation source incorporates the physical-JSONL reader correction and this explicit schema adapter; it is the sole successor that should create actual all-draw plans. Eventual exact numerical G1 must review every derived inventory/plan, with this source.
