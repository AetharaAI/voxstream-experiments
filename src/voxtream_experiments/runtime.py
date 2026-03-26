from __future__ import annotations

import base64
import io
import os
import queue
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException
import numpy as np

from .config import ExperimentConfig
from .event_log import EventLogger
from .native_voxtream2 import QueueTextIterator, Voxtream2NativeRunner
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
    prompt_audio_path: str | None = None
    prompt_audio_temp_path: str | None = None
    prompt_text: str | None = None
    speaking_rate: float | None = None
    audio_queue: queue.Queue[tuple[np.ndarray | None, float | None, str | None]] | None = None
    text_queue: queue.Queue[str | None] | None = None
    worker: threading.Thread | None = None
    finished: bool = False
    closed_text: bool = False
    first_chunk_ms: int | None = None
    chunk_sequence: int = 0
    inference_ms_total: int = 0
    audio_frames: list[np.ndarray] = field(default_factory=list)


class ProviderRuntime:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.event_logger = EventLogger(config.log_dir / "voxtream-provider.jsonl")
        self.sessions: dict[str, ProviderStreamState] = {}
        self._native_runner: Voxtream2NativeRunner | None = None

    def _model_descriptor(self, model_alias: str) -> dict[str, str]:
        for descriptor in self.config.model_descriptors():
            if descriptor["alias"] == model_alias or descriptor["id"] == model_alias:
                return descriptor
        raise HTTPException(status_code=400, detail=f"Unsupported model '{model_alias}'.")

    def _native_runtime_implemented(self) -> bool:
        return self.config.provider_family == "voxtream2"

    def _get_native_runner(self) -> Voxtream2NativeRunner:
        if self.config.provider_family != "voxtream2":
            raise HTTPException(
                status_code=501,
                detail="Original Voxtream requires a separate 0.1.5 runtime lane and is not implemented in this provider yet.",
            )
        if self._native_runner is None:
            self._native_runner = Voxtream2NativeRunner(self.config, self.event_logger)
        return self._native_runner

    @staticmethod
    def _encode_wav(audio: np.ndarray, sample_rate: int) -> bytes:
        import soundfile as sf

        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV")
        return buffer.getvalue()

    @staticmethod
    def _drain_audio_events(
        state: ProviderStreamState,
        *,
        wait_timeout_seconds: float,
        until_finished: bool,
    ) -> list[dict[str, Any]]:
        if state.audio_queue is None:
            return []
        events: list[dict[str, Any]] = []

        def _consume(item: tuple[np.ndarray | None, float | None, str | None]) -> str | None:
            frame, gen_time, err = item
            if err:
                raise HTTPException(status_code=500, detail=err)
            if frame is None:
                state.finished = True
                return "done"
            state.audio_frames.append(frame)
            state.chunk_sequence += 1
            state.inference_ms_total += int(round((gen_time or 0.0) * 1000))
            if state.first_chunk_ms is None:
                state.first_chunk_ms = int((time.perf_counter() - state.started_at) * 1000)
            events.append(
                {
                    "type": "audio_chunk",
                    "session_id": state.session_id,
                    "sequence": state.chunk_sequence,
                    "audio_b64": base64.b64encode(ProviderRuntime._encode_wav(frame, state.sample_rate)).decode("ascii"),
                    "format": state.output_format,
                    "metadata": {
                        "provider_gen_time_ms": int(round((gen_time or 0.0) * 1000)),
                        "provider_family": state.metadata.get("provider_family"),
                    },
                }
            )
            return None

        try:
            first = state.audio_queue.get(timeout=wait_timeout_seconds)
        except queue.Empty:
            return events

        result = _consume(first)
        if result == "done" and not until_finished:
            return events

        while True:
            if until_finished and state.finished:
                break
            try:
                item = state.audio_queue.get_nowait()
            except queue.Empty:
                if until_finished and not state.finished:
                    try:
                        item = state.audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        continue
                else:
                    break
            result = _consume(item)
            if result == "done" and not until_finished:
                break
        return events

    def _resolve_prompt_audio(
        self,
        *,
        prompt_audio_path: str | None,
        prompt_audio_b64: str | None,
    ) -> tuple[str, str | None]:
        if prompt_audio_path:
            return prompt_audio_path, None
        if not prompt_audio_b64:
            raise HTTPException(status_code=400, detail="Voxtream requires prompt_audio_path or prompt_audio_b64.")
        payload = prompt_audio_b64
        if "," in prompt_audio_b64 and prompt_audio_b64.lower().startswith("data:audio/"):
            payload = prompt_audio_b64.split(",", 1)[1]
        raw = base64.b64decode(payload)
        suffix = ".wav"
        fd, temp_path = tempfile.mkstemp(prefix="voxtream_prompt_", suffix=suffix)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        return temp_path, temp_path

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
        runtime_implemented = self._native_runtime_implemented()
        native_ready = runtime_enabled and runtime_implemented and voxtream_pkg and espeak_ok and all(model["present"] for model in models)
        return {
            "provider_family": self.config.provider_family,
            "runtime_enabled": runtime_enabled,
            "native_runtime_implemented": runtime_implemented,
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
        if not report["native_runtime_implemented"]:
            raise HTTPException(
                status_code=501,
                detail=f"{route} is not implemented for provider family '{self.config.provider_family}'.",
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
        resolved_model = model_alias or self.config.model_alias
        self._require_native_runtime(route="warmup", model_alias=resolved_model)
        self._get_native_runner().load()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        self.event_logger.emit("provider_warmup_completed", model=resolved_model, elapsed_ms=elapsed_ms)
        return ProviderWarmupResponse(status="ready", model=resolved_model, ready=True, elapsed_ms=elapsed_ms)

    def synthesize(self, payload: ProviderSpeechRequest) -> ProviderSpeechResponse:
        self._require_native_runtime(route="synthesize", model_alias=payload.model)
        prompt_audio_path, temp_path = self._resolve_prompt_audio(
            prompt_audio_path=payload.prompt_audio_path,
            prompt_audio_b64=payload.prompt_audio_b64,
        )
        runner = self._get_native_runner()
        started = time.perf_counter()
        try:
            frames: list[np.ndarray] = []
            inference_ms_total = 0
            for frame, gen_time in runner.generate_stream(
                prompt_audio_path=Path(prompt_audio_path),
                text=payload.input,
                speaking_rate=payload.speaking_rate,
            ):
                frames.append(frame)
                inference_ms_total += int(round(gen_time * 1000))
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
        if not frames:
            raise HTTPException(status_code=500, detail="Voxtream native runner did not return audio.")
        audio = np.concatenate(frames)
        audio_bytes = self._encode_wav(audio, runner.sample_rate())
        total_ms = int(round((time.perf_counter() - started) * 1000))
        return ProviderSpeechResponse(
            model=payload.model,
            format=payload.response_format,
            sample_rate=runner.sample_rate(),
            audio_b64=base64.b64encode(audio_bytes).decode("ascii"),
            timings={
                "inference_ms": inference_ms_total,
                "total_ms": total_ms,
            },
            artifacts={
                "provider_family": self.config.provider_family,
                "prompt_audio_path": payload.prompt_audio_path or "",
                "prompt_text": payload.prompt_text or "",
                "speaking_rate": payload.speaking_rate,
            },
        )

    def start_stream(self, payload: ProviderStreamStartRequest) -> dict[str, Any]:
        self._require_native_runtime(route="stream.start", model_alias=payload.model)
        prompt_audio_path, temp_path = self._resolve_prompt_audio(
            prompt_audio_path=payload.prompt_audio_path,
            prompt_audio_b64=payload.prompt_audio_b64,
        )
        runner = self._get_native_runner()
        runner.load()
        text_queue: queue.Queue[str | None] = queue.Queue()
        audio_queue: queue.Queue[tuple[np.ndarray | None, float | None, str | None]] = queue.Queue(maxsize=16)
        state = ProviderStreamState(
            session_id=payload.session_id,
            model=payload.model,
            voice=payload.voice,
            sample_rate=payload.sample_rate,
            output_format=payload.format,
            context_mode=payload.context_mode,
            metadata={**dict(payload.metadata or {}), "provider_family": self.config.provider_family},
            prompt_audio_path=prompt_audio_path,
            prompt_audio_temp_path=temp_path,
            prompt_text=payload.prompt_text,
            speaking_rate=payload.speaking_rate,
            text_queue=text_queue,
            audio_queue=audio_queue,
        )
        text_iter = QueueTextIterator(text_queue)

        def worker() -> None:
            err: str | None = None
            try:
                for frame, gen_time in runner.generate_stream(
                    prompt_audio_path=Path(prompt_audio_path),
                    text=text_iter,
                    speaking_rate=payload.speaking_rate,
                ):
                    audio_queue.put((frame, gen_time, None))
            except Exception as exc:  # pragma: no cover - native path
                err = str(exc)
            finally:
                audio_queue.put((None, None, err))

        state.worker = threading.Thread(target=worker, daemon=True, name=f"voxtream-stream-{payload.session_id}")
        state.worker.start()
        self.sessions[payload.session_id] = state
        self.event_logger.emit(
            "provider_stream_started",
            session_id=payload.session_id,
            model=payload.model,
            voice=payload.voice,
            sample_rate=payload.sample_rate,
            provider_family=self.config.provider_family,
        )
        return {
            "session_id": payload.session_id,
            "model": payload.model,
            "expires_in_seconds": 3600,
            "provider_family": self.config.provider_family,
        }

    def push_stream_text(self, session_id: str, text: str) -> ProviderTextEventsResponse:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail=f"Unknown stream session '{session_id}'.")
        state = self.sessions[session_id]
        if state.closed_text or state.text_queue is None:
            raise HTTPException(status_code=409, detail=f"Stream session '{session_id}' is already finalized.")
        state.text_fragments.append(text)
        state.text_queue.put(text)
        return ProviderTextEventsResponse(events=self._drain_audio_events(state, wait_timeout_seconds=0.2, until_finished=False))

    def complete_stream_text(self, session_id: str) -> ProviderTextEventsResponse:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail=f"Unknown stream session '{session_id}'.")
        state = self.sessions[session_id]
        if not state.closed_text and state.text_queue is not None:
            state.closed_text = True
            state.text_queue.put(None)
        return ProviderTextEventsResponse(events=self._drain_audio_events(state, wait_timeout_seconds=0.25, until_finished=True))

    def end_stream(self, session_id: str) -> ProviderStreamEndResponse:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail=f"Unknown stream session '{session_id}'.")
        state = self.sessions.pop(session_id)
        if not state.closed_text and state.text_queue is not None:
            state.closed_text = True
            state.text_queue.put(None)
        self._drain_audio_events(state, wait_timeout_seconds=0.25, until_finished=True)
        if state.worker is not None:
            state.worker.join(timeout=1.0)
        if state.prompt_audio_temp_path:
            Path(state.prompt_audio_temp_path).unlink(missing_ok=True)
        if not state.audio_frames:
            raise HTTPException(status_code=500, detail="Voxtream native runner did not produce final audio.")
        audio = np.concatenate(state.audio_frames)
        audio_bytes = self._encode_wav(audio, state.sample_rate)
        duration_ms = int(round((audio.shape[0] / max(state.sample_rate, 1)) * 1000))
        total_ms = int(round((time.perf_counter() - state.started_at) * 1000))
        return ProviderStreamEndResponse(
            model=state.model,
            format=state.output_format,
            duration_ms=duration_ms,
            sample_rate=state.sample_rate,
            audio_b64=base64.b64encode(audio_bytes).decode("ascii"),
            timings={
                "first_chunk_ms": state.first_chunk_ms or 0,
                "inference_ms": state.inference_ms_total,
                "total_ms": total_ms,
            },
            artifacts={
                "provider_family": self.config.provider_family,
                "text_fragments": len(state.text_fragments),
                "chunk_events": state.chunk_sequence,
                "prompt_text": state.prompt_text or "",
                "speaking_rate": state.speaking_rate,
            },
        )
