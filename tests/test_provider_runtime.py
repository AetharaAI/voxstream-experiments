from __future__ import annotations

from pathlib import Path

from voxtream_experiments.config import ExperimentConfig
from voxtream_experiments.runtime import ProviderRuntime


def test_health_payload_stays_staged_without_native_runtime(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOXTREAM_OUTPUT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("VOXTREAM_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("VOXTREAM_PROVIDER_ENABLE_NATIVE_RUNTIME", "false")

    config = ExperimentConfig.from_env()
    runtime = ProviderRuntime(config)

    payload = runtime.health_payload()

    assert payload["status"] == "staged"
    assert payload["dependencies"]["native_ready"] is False
    assert payload["dependencies"]["provider_family"] == "voxtream2"
    assert payload["dependencies"]["native_runtime_implemented"] is True
    assert len(payload["dependencies"]["models"]) == 1


def test_model_descriptor_accepts_alias(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOXTREAM_OUTPUT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("VOXTREAM_LOG_DIR", str(tmp_path / "logs"))
    config = ExperimentConfig.from_env()
    runtime = ProviderRuntime(config)

    descriptor = runtime._model_descriptor("voxtream2_realtime")
    assert descriptor["alias"] == "voxtream2_realtime"


def test_model_descriptor_accepts_model_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOXTREAM_OUTPUT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("VOXTREAM_LOG_DIR", str(tmp_path / "logs"))
    config = ExperimentConfig.from_env()
    runtime = ProviderRuntime(config)

    descriptor = runtime._model_descriptor("herimor/voxtream2")
    assert descriptor["id"] == "herimor/voxtream2"
