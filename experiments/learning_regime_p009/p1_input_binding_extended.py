"""Owner-authorized local-window successor; original input/scorer bytes unchanged."""
from experiments.learning_regime_p009.p1_input_binding import (
    bind_complete_generations, DATASET_ORDER, GENERATION_SPEC_SHA, GENERATION_TARGET,
    SOURCE_PATHS as ORIGINAL_SOURCE_PATHS,
)

SOURCE_PATHS=ORIGINAL_SOURCE_PATHS+(
    'experiments/learning_regime_p009/p1_input_binding_extended.py',
    'scripts/p009_p1_driver_extended.py',
)
OWNER_WINDOW_AMENDMENT_SHA256='de0ca58c2cb44877f210f4060f99cadcc9b447e53367ab6130c0ad2f4016b7b0'
