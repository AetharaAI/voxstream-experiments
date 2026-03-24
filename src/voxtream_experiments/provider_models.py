from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProviderModelInfo(BaseModel):
    id: str
    label: str
    supports_batch: bool = False
    supports_streaming: bool = True
    default_voice: str


class ProviderVoiceInfo(BaseModel):
    id: str
    label: str
    language: str = "multi"
    tags: list[str] = Field(default_factory=list)


class ProviderSpeechRequest(BaseModel):
    model: str
    input: str
    voice: str
    response_format: Literal["wav"] = "wav"
    language: str = "English"
    instructions: str | None = None
    prompt_audio_path: str | None = None
    prompt_audio_b64: str | None = None
    prompt_text: str | None = None
    speaking_rate: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderSpeechResponse(BaseModel):
    model: str
    format: Literal["wav"] = "wav"
    sample_rate: int
    audio_b64: str
    timings: dict[str, int] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class ProviderStreamStartRequest(BaseModel):
    session_id: str
    model: str
    voice: str
    sample_rate: int = 24000
    format: Literal["wav"] = "wav"
    context_mode: str = "conversation"
    prompt_audio_path: str | None = None
    prompt_audio_b64: str | None = None
    prompt_text: str | None = None
    instructions: str | None = None
    speaking_rate: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderTextChunkRequest(BaseModel):
    text: str


class ProviderTextEventsResponse(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


class ProviderStreamEndResponse(BaseModel):
    model: str
    format: Literal["wav"] = "wav"
    duration_ms: int
    sample_rate: int
    audio_b64: str
    timings: dict[str, int] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class ProviderWarmupResponse(BaseModel):
    status: str
    model: str
    ready: bool
    elapsed_ms: float
