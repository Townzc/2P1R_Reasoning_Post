# A6-2 Base pair and 4B construction preparation

The Base pair reuses the frozen9B M512 as required. All1,024 actual arm rows passed the Base tokenizer/rendering/mask checks and fit2,300 full tokens. Dataset bytes and question order match the completed9B pair. These requests are prepared, unadmitted and unstarted until the9B A6-3 block completes and the budget is reconciled.

The unstarted4B construction request now binds the preserved overlength-filter repair used by9B. The data selection recipe is unchanged. Its existing3USD reservation must not be counted twice. No model call was made for this CPU preparation.
