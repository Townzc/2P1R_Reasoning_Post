"""Adds exact owner/quota binding without weakening joint G1 or lineage."""
from .lineage_student_binding import validate_student_binding as validate_lineage
from .student_concurrency import validate_quota


def validate_student_binding(plan, cfg, release, spec):
    validate_lineage(plan, cfg, release, spec)
    validate_quota(spec, release['gates'])
    return True
