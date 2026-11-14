# A7-1: frozen concise rewriting construction

Two unfinetuned teachers each rewrite their own512 frozen long answers. The template is byte-exact to22890560, including its final newline. Literal insertion preserves mathematical braces and placeholder text inside inputs. Target word counts use half-up rounding to10,minimum20. Nine contract tests and all1024 actual prompt/render/context checks passed.

Each teacher hasUSD2 reserved inside theA7USD60 cap. Every wave uses measured completion tokens plus actual prompt tokens, x1.5, with an additional uncached maximum bound. All returned samples are persisted before eligibility checks; every check has a UTC prediction record binding22890560 and its raw-record hash. First eligible response is retained, original long answer is the fallback after four failures; more than26 fallbacks stops before training. No per-row length filter is added.

After both constructions finish, publish all student-tokenizer statistics, ratios, hashes and fallbacks and report them to the owner before training. New construction is exempt from pre-review underA7; full posthoc audit is required.
