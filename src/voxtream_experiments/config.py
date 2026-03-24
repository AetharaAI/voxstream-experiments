from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class ExperimentConfig:
    provider_host: str
    provider_port: int
    provider_public_base_url: str
    provider_timeout_seconds: float
    provider_default_response_format: str
    provider_enable_native_runtime: bool
    provider_network_name: str
    model_alias: str
    model_id: str
    model_path: str
    model2_alias: str
    model2_id: str
    model2_path: str
    device: str
    dtype: str
    output_dir: Path
    log_dir: Path
    default_sample_rate: int
    default_voice: str

    @classmethod
    def from_env(cls, env_file: str | None = None) -> "ExperimentConfig":
        if env_file:
            load_dotenv(env_file, override=False)
        else:
            load_dotenv(override=False)

        output_dir = Path(os.getenv("VOXTREAM_OUTPUT_DIR", "results"))
        log_dir = Path(os.getenv("VOXTREAM_LOG_DIR", "logs"))
        output_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            provider_host=os.getenv("VOXTREAM_PROVIDER_HOST", "0.0.0.0"),
            provider_port=int(os.getenv("VOXTREAM_PROVIDER_PORT", "8074")),
            provider_public_base_url=os.getenv("VOXTREAM_PROVIDER_PUBLIC_BASE_URL", "http://voxtream-provider:8074"),
            provider_timeout_seconds=float(os.getenv("VOXTREAM_PROVIDER_TIMEOUT_SECONDS", "180")),
            provider_default_response_format=os.getenv("VOXTREAM_PROVIDER_DEFAULT_RESPONSE_FORMAT", "wav"),
            provider_enable_native_runtime=os.getenv("VOXTREAM_PROVIDER_ENABLE_NATIVE_RUNTIME", "false").lower() in {"1", "true", "yes", "on"},
            provider_network_name=os.getenv("VOXTREAM_PROVIDER_NETWORK_NAME", "aether-voice-mesh"),
            model_alias=os.getenv("VOXTREAM_MODEL_ALIAS", "voxtream_realtime"),
            model_id=os.getenv("VOXTREAM_MODEL_ID", "herimor/voxtream"),
            model_path=os.getenv("VOXTREAM_MODEL_PATH", "/mnt/aetherpro/models/voice/herimor/voxtream"),
            model2_alias=os.getenv("VOXTREAM2_MODEL_ALIAS", "voxtream2_realtime"),
            model2_id=os.getenv("VOXTREAM2_MODEL_ID", "herimor/voxtream2"),
            model2_path=os.getenv("VOXTREAM2_MODEL_PATH", "/mnt/aetherpro/models/voice/herimor/voxtream2"),
            device=os.getenv("VOXTREAM_DEVICE", "cuda:0"),
            dtype=os.getenv("VOXTREAM_DTYPE", "float16"),
            output_dir=output_dir,
            log_dir=log_dir,
            default_sample_rate=int(os.getenv("VOXTREAM_DEFAULT_SAMPLE_RATE", "24000")),
            default_voice=os.getenv("VOXTREAM_DEFAULT_VOICE", "reference_audio_required"),
        )

    def model_descriptors(self) -> list[dict[str, str]]:
        return [
            {"alias": self.model_alias, "id": self.model_id, "path": self.model_path},
            {"alias": self.model2_alias, "id": self.model2_id, "path": self.model2_path},
        ]

    def espeak_available(self) -> bool:
        return shutil.which("espeak-ng") is not None

    def voxtream_import_available(self) -> bool:
        try:
            import voxtream  # noqa: F401
        except Exception:
            return False
        return True
