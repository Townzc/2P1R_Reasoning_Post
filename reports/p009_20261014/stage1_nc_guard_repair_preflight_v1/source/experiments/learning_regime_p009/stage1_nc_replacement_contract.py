"""One explicitly owner-approved replacement; original failed run is immutable."""
from experiments.learning_regime_p009.stage1_nc_contract import (
    slot as original_slot, forecast, transport_checked, cents)

CAMPAIGN = 'p009-stage1-nc-replacement-20261015-r1'
RUN = 'nc_s17_n3200_replacement_r1'
RUNS = (RUN,)
PARENT_CAMPAIGN = 'p009-stage1-nc-20261015-r1'
PARENT_RUN = 'nc_s17_n3200'
ORIGINAL_NC400 = 'nc_s17_n400'
PARENT_TARGET = 'ab271a94749570308690b3eda2ee6a5c68c3618c'
PARENT_SPEC_SHA = '748a7ab00a4fa9cd0b7efd126750f96e323837e672532c89bf42c65bc88f9db4'
PARENT_MANIFEST_SHA = '74c4590c8b112ba1b2623824c0bc2bb82facc3c7a590fe59a0ba1bb9eecec609'
PARENT_PRESERVED_SHA = '75f29c7560e963f8e28777906158762b30c449de688fc2d2e7726a1eb4fa9b8b'
PARENT_FAILURE_DIGEST = 'bcf8475473a491a5a638938423afeba23555cfbeda72aaf10865deb63344b5d9'
NC400_STATE_SHA = 'f9aca4bf01e944528e723d252b16d7229b3057d18ee1544d81c7e0d25815e209'
OWNER_FILE_SHA = '108c82f933990473119f48b186223057f1ab3a0f92769e666bbe2b34be8e0ae3'
OWNER_CANONICAL = 'c9625dacdb11d1fe2101eb965416bbafcc030682249b9ce0b116e7d9bfb582b5'
SCOPE = 'p009-stage1-NC3200-independent-replacement-runtime-and-numeric'
PARENT_SCOPE = 'p009-stage1-NC-preemption-and-complete-n400-A4-disposition'
STAGE1_CAP_CENTS = 5000
PRIOR_RESERVED_CENTS = 1310
NEW_RESERVED_CENTS = 655


def slot(run):
    if run != RUN:
        raise ValueError('Only one new physical NC3200 replacement is authorized')
    return original_slot(PARENT_RUN)
