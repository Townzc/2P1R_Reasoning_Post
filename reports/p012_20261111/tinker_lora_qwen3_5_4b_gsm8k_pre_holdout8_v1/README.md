# Tinker4B GSM8K holdout sampling: existing outputs scored

pass@1 66.275%; pass@8 93.20%. Correctdraws 2651/4000.

40.5%ofoutputsareanswer-only. These pass@1/pass@8 numbers are descriptive measurements of this output-format-affected run and are not used as pretraining capability. The4B GSM8K training reference is4-shot1216/1319=92.19%; the0-shotbaseline contains543/1319answer-only outputs.

46e98da5 authorized scoring the existing4000outputs. All4000samplingseeds andsequenceIDs aredistinct;12/500questions haveeightidentical sequences. The80%diversityguard applies only to the threeMATHv2repair endpoints. Rawoutputsha isunchanged; no sampling or training call was repeated. Independent score review is pending in the next batch.
