from __future__ import annotations

from pathlib import Path

from voxtream_experiments.config import ExperimentConfig


def test_config_model_descriptors_include_both_lanes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOXTREAM_OUTPUT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("VOXTREAM_LOG_DIR", str(tmp_path / "logs"))
    config = ExperimentConfig.from_env()

    descriptors = config.model_descriptors()

    assert config.provider_family == "voxtream2"
    assert len(descriptors) == 1
    assert descriptors[0]["alias"] == "voxtream2_realtime"
