# Accepted46e98da5 implementation

All12b97b8bebendpoints and theE8export-only recovery are accepted inACCEPTANCE.json. Auditstatus is additive; originalRESULTS,inputmanifest,rawoutputs andlabels remain byte-identical. The87GSMlabel differences retain the frozen percent-stripping scoring convention.

The existing4BGSMpass@8outputs were scored once after release,with no newmodelcall. The result is published separately and marked ineligible for pretraining capability. T_GSM_INTERPRETATION.json selects4-shot92.19%as the4BGSMreference and records543/1319answer-only0-shotoutputs and40.5%answer-onlyholdoutoutputs. Metadata/README annotations are applied to allnine4BGSMtrainingresults after publication; numeric results are unchanged.

Storage gating now uses APIrate and aggregateusage only; ownerstorageflags are documentary. CHECKS_final.json records16passing checks. No newexport was attempted. Account andbillingchanges are owner-only: if an account change is required,the assistant stops and reports; no UI/APIsettingmutation is allowed.

Budgetpolicy: the first owneranswer transfersUSD2fromA6-2,setting its cap48; the later explicitA6-3cap38 supersedes the proposed37. OriginalT340,storage30andcombined485stay fixed. L64is admitted andrunning through unchanged scientific paths. current_budget.py is the authoritative cap-overlay over existingcost calculations. LiveGSMhelpers remain unchanged and continue enforcing theirGSM105/T340/combined485caps; their old subcap metadata is historical.
