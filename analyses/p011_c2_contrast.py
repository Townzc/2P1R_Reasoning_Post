"""Prepared fixed C2 common-support contrast, unchanged question bootstrap."""


def contrast(vectors,ids,metric):
    import numpy as np
    from analyses.p010_paired_questions import checked_vector,DRAWS,SEED
    if set(vectors)!={'C2a','C2b'} or len(ids)!=500:
        raise ValueError('Two complete original500 C2 vectors required')
    a=checked_vector(vectors['C2a'],ids,metric);b=checked_vector(vectors['C2b'],ids,metric)
    delta=b-a
    sample=np.random.default_rng(SEED).integers(0,500,size=(DRAWS,500))
    means=delta[sample].mean(axis=1)*100;lo,hi=np.quantile(means,[.025,.975],method='linear')
    return {'metric':metric,'contrast':'C2b_minus_C2a','difference_pp':float(delta.mean()*100),
        'pointwise95_ci_pp':[float(lo),float(hi)],'draws':DRAWS,'seed':SEED,
        'numpy_version':np.__version__,'percentile_method':'linear','question_resampling':True,
        'training_seed_population':False,'conditioned_on_both_teachers_usable':True,
        'mechanism_or_equivalence_claim':False,'new_model_or_symbolic_scoring':False}
