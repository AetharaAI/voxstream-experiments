from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .config import ExperimentConfig
from .event_log import EventLogger
from .provider_models import (
    ProviderModelInfo,
    ProviderSpeechRequest,
    ProviderSpeechResponse,
    ProviderStreamEndResponse,
    ProviderStreamStartRequest,
    ProviderTextEventsResponse,
    ProviderVoiceInfo,
    ProviderWarmupResponse,
)


@dataclass(slots=True)
class ProviderStreamState:
    session_id: str
    model: str
    voice: str
    sample_rate: int
    output_format: str
    context_mode: str
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.perf_counter)
    text_fragments: list[str] = field(default_factory=list)


class ProviderRuntime:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.event_logger = EventLogger(config.log_dir / "voxtream-provider.jsonl")
        self.sessions: dict[str, ProviderStreamState] = {}

    def _model_descriptor(self, model_alias: str) -> dict[str, str]:
        for descriptor in self.config.model_descriptors():
            if descriptor["alias"] == model_alias:
                return descriptor
        raise HTTPException(status_code=400, detail=f"Unsupported model '{model_alias}'.")

    def dependency_report(self) -> dict[str, Any]:
        models = []
        for descriptor in self.config.model_descriptors():
            model_path = Path(descriptor["path"])
            models.append(
                {
                    "alias": descriptor["alias"],
                    "model_id": descriptor["id"],
                    "path": str(model_path),
                    "present": model_path.exists(),
                }
            )
        voxtream_pkg = self.config.voxtream_import_available()
        espeak_ok = self.config.espeak_available()
        runtime_enabled = self.config.provider_enable_native_runtime
        native_ready = runtime_enabled and voxtream_pkg and espeak_ok and all(model["present"] for model in models)
        return {
            "runtime_enabled": runtime_enabled,
            "voxtream_package_installed": voxtream_pkg,
            "espeak_ng_installed": espeak_ok,
            "models": models,
            "native_ready": native_ready,
        }

    def health_payload(self) -> dict[str, Any]:
        report = self.dependency_report()
        status = "ready" if report["native_ready"] else "staged"
        return {
            "status": status,
            "service": "voxtream-provider",
            "dependencies": report,
        }

    def model_info(self) -> list[ProviderModelInfo]:
        return [
            ProviderModelInfo(
                id=descriptor["alias"],
                label=f"{descriptor['alias']} ({descriptor['id']})",
                default_voice=self.config.default_voice,
            )
            for descriptor in self.config.model_descriptors()
        ]

    def voice_info(self) -> list[ProviderVoiceInfo]:
        return [
            ProviderVoiceInfo(
                id="reference_audio_required",
                label="Reference Audio Required",
                tags=["zero-shot", "prompt-audio", "voxtream"],
            )
        ]

    def _require_native_runtime(self, *, route: str, model_alias: str) -> None:
        report = self.dependency_report()
        if not report["runtime_enabled"]:
            raise HTTPException(
                status_code=503,
                detail=f"{route} is disabled until VOXTREAM_PROVIDER_ENABLE_NATIVE_RUNTIME=true and native proof exists.",
            )
        if not report["voxtream_package_installed"]:
            raise HTTPException(status_code=503, detail="Python package 'voxtream' is not installed.")
        if not report["espeak_ng_installed"]:
            raise HTTPException(status_code=503, detail="Dependency 'espeak-ng' is not installed.")
        descriptor = self._model_descriptor(model_alias)
        if not Path(descriptor["path"]).exists():
            raise HTTPException(status_code=503, detail=f"Model path is missing: {descriptor['path']}")

    def warmup(self, model_alias: str | None = None) -> ProviderWarmupResponse:
        started = time.perf_counter()
        resolved_model = model_alias or self.config.model2_alias
        self._require_native_runtime(route="warmup", model_alias=resolved_model)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        self.event_logger.emit("provider_warmup_completed", model=resolved_model, elapsed_ms=elapsed_ms)
        return ProviderWarmupResponse(status="ready", model=resolved_model, ready=True, elapsed_ms=elapsed_ms)

    def synthesize(self, payload: ProviderSpeechRequest) -> ProviderSpeechResponse:
        self._require_native_runtime(route="synthesize", model_alias=payload.model)
        raise HTTPException(status_code=501, detail="Native Voxtream batch synthesis is not implemented in this scaffold yet.")

    def start_stream(self, payload: ProviderStreamStartRequest) -> dict[str, Any]:
        self._require_native_runtime(route="stream.start", model_alias=payload.model)
        self.sessions[payload.session_id] = ProviderStreamState(
            session_id=payload.session_id,
            model=payload.model,
            voice=payload.voice,
            sample_rate=payload.sample_rate,
            output_format=payload.format,
            context_mode=payload.context_mode,
            metadata=dict(payload.metadata or {}),
        )
        self.event_logger.emit(
            "provider_stream_started",
            session_id=payload.session_id,
            model=payload.model,
            voice=payload.voice,
            sample_rate=payload.sample_rate,
        )
        raise HTTPException(status_code=501, detail="Native Voxtream streaming is not implemented in this scaffold yet.")

    def push_stream_text(self, session_id: str, text: str) -> ProviderTextEventsResponse:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail=f"Unknown stream session '{session_id}'.")
        self.sessions[session_id].text_fragments.append(text)
        raise HTTPException(status_code=501, detail="Native Voxtream streaming is not implemented in this scaffold yet.")

    def complete_stream_text(self, session_id: str) -> ProviderTextEventsResponse:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail=f"Unknown stream session '{session_id}'.")
        raise HTTPException(status_code=501, detail="Native Voxtream streaming is not implemented in this scaffold yet.")

    def end_stream(self, session_id: str) -> ProviderStreamEndResponse:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail=f"Unknown stream session '{session_id}'.")
        self.sessions.pop(session_id, None)
        raise HTTPException(status_code=501, detail="Native Voxtream streaming is not implemented in this scaffold yet.")
