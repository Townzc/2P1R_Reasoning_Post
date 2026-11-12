import pytest
from experiments.p012.training_config import training_config, grid_dose, CELLS


@pytest.mark.parametrize("cell", list(CELLS))
def test_registered_exposure_and_batch(cell):
    dose = grid_dose(cell)
    assert dose["presentations"] == (1024 if cell == "L" else 8192)
    assert dose["expected_updates"] == (128 if cell == "L" else 1024)
    config = training_config("fixed-model", "fixed-sha", "qwen", "frozen-data", "inputs", "new-output", 17, cell)
    assert config["per_device_train_batch_size"] * config["gradient_accumulation_steps"] == 8
    assert (config["per_device_train_batch_size"], config["gradient_accumulation_steps"]) == (8, 1)
    assert config["val_size"] == 0
    assert config["num_train_epochs"] == dose["epochs"]
    assert config["packing"] is False and config["train_on_prompt"] is False
    assert config["save_strategy"] == "no"


def test_reproduction_keeps_published_validation_split():
    config = training_config("model", "sha", "llama3", "uw", "inputs", "new", long_cot=True)
    assert config["cutoff_len"] == 16384
    assert config["val_size"] == 0.01
    assert config["eval_steps"] == 100
    assert config["learning_rate"] == 1e-5
    assert config["seed"] == 42 and config["data_seed"] is None
    assert "save_strategy" not in config and config["save_steps"] == 1000


def test_long_grid_cannot_be_enabled_accidentally():
    with pytest.raises(ValueError):
        training_config("model", "sha", "qwen", "uw", "inputs", "new", 17, cell="P", long_cot=True)


def test_short_reproduction_uses_model_card_global16():
    config = training_config("model", "sha", "qwen", "uw", "inputs", "new")
    assert (config["per_device_train_batch_size"], config["gradient_accumulation_steps"]) == (2, 8)
    assert config["save_steps"] == 1000 and config["val_size"] == 0.01
