from __future__ import annotations

import base64
import tempfile
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


def test_prompt_audio_b64_preferred_over_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOXTREAM_OUTPUT_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("VOXTREAM_LOG_DIR", str(tmp_path / "logs"))
    config = ExperimentConfig.from_env()
    runtime = ProviderRuntime(config)

    with tempfile.NamedTemporaryFile(suffix=".wav") as bad_path:
        b64 = base64.b64encode(b"RIFFxxxxWAVEfmt ").decode("ascii")
        resolved_path, temp_path = runtime._resolve_prompt_audio(
            prompt_audio_path=bad_path.name,
            prompt_audio_b64=b64,
        )
        assert temp_path is not None
        assert resolved_path == temp_path
        assert Path(temp_path).exists()
        Path(temp_path).unlink(missing_ok=True)
