"""Local admission guard for the sole current P008 final CPU entry.

Historical entry sources and evidence stay immutable. This guard is used by
the current preparation/upload workflow, before any cloud action.
"""
CURRENT_MODULE = 'experiments/sft_allocation_p008/modal_audit_t8_cap.py'
CURRENT_ENTRY = 'experiments.sft_allocation_p008.modal_audit_t8_cap::main'


def require_current_entry(module, source_files):
    entries = {name for name in source_files
               if name.startswith('experiments/sft_allocation_p008/modal_')}
    if module != CURRENT_MODULE or entries != {CURRENT_MODULE}:
        raise ValueError('Only the exact final CPU entry with T8 operational-cap checks may be admitted')
    return CURRENT_ENTRY
