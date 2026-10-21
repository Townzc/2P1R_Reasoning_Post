"""B-only question-paired interaction and original-temperature contrasts."""


def contrast(vectors,ids,metric):
    import numpy as np
    from analyses.p010_paired_questions import checked_vector,DRAWS,SEED
    names={'B1','B3','T08_K1','T08_K8'}
    if set(vectors)!=names or len(ids)!=500:raise ValueError('All four complete fixed B/T08 vectors required')
    values={n:checked_vector(vectors[n],ids,metric) for n in names}
    diffs={'temperature_x_K':(values['B3']-values['B1'])-(values['T08_K8']-values['T08_K1']),
        'B1_minus_T08_K1':values['B1']-values['T08_K1'],
        'B3_minus_T08_K8':values['B3']-values['T08_K8']}
    sample=np.random.default_rng(SEED).integers(0,500,size=(DRAWS,500))
    result=[]
    for name,delta in diffs.items():
        draws=delta[sample].mean(axis=1)*100
        lo,hi=np.quantile(draws,[.025,.975],method='linear')
        result.append(dict(name=name,difference_pp=float(delta.mean()*100),pointwise95_ci_pp=[float(lo),float(hi)]))
    return dict(metric=metric,contrasts=result,draws=DRAWS,seed=SEED,numpy_version=np.__version__,
        percentile_method='linear',question_resampling=True,training_seed_population=False,
        old_statistics_recomputed=False,old_Boolean_scores_reused_without_scoring=True,
        mechanism_or_equivalence_claim=False)
