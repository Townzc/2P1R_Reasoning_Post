"""Exact final CPU binding including the approved operational T8 supplement."""
from .audit_replacement_binding import (
    CONFIG, PARENT_LABEL, PARENT_ARCHIVE, CHILD_RUN, ARCHIVES, FAILED_STUDENTS,
    REPLACEMENTS, REPLACEMENT_CAMPAIGN, physical_roster, source_key,
    validate as validate_original, validate_label as validate_original_label,
    validate_all_labels as validate_original_all_labels)
from .audit_t8_cap_records import validate_cap_inputs, validate_cap_numeric, validate_cap_label


def validate(binding, spec, release):
    roster = validate_original(binding, spec, release)
    validate_cap_numeric(binding)
    return roster


def validate_label(binding, name, label):
    validate_original_label(binding, name, label)
    return validate_cap_label(binding, name, label)


def validate_all_labels(binding, labels):
    validate_original_all_labels(binding, labels)
    validate_cap_inputs(binding)
    for name, label in labels.items():
        validate_cap_label(binding, name, label)
    return labels
