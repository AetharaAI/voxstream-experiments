from __future__ import annotations

import logging
import os
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .config import ExperimentConfig
from .provider_models import (
    ProviderSpeechRequest,
    ProviderStreamStartRequest,
    ProviderTextChunkRequest,
)
from .runtime import ProviderRuntime

logger = logging.getLogger("voxtream_provider")
def create_app(config: ExperimentConfig | None = None) -> FastAPI:
    resolved_config = config or ExperimentConfig.from_env()
    runtime = ProviderRuntime(resolved_config)
    app = FastAPI(default_response_class=ORJSONResponse, title="Voxtream Provider")

    @app.get("/health")
    async def health() -> ORJSONResponse:
        payload = runtime.health_payload()
        status_code = 200 if payload["status"] == "ready" else 503
        return ORJSONResponse(payload, status_code=status_code)

    @app.get("/v1/models")
    async def list_models() -> dict[str, list[dict[str, Any]]]:
        return {"models": [entry.model_dump() for entry in runtime.model_info()]}

    @app.get("/v1/voices")
    async def list_voices() -> dict[str, list[dict[str, Any]]]:
        return {"voices": [entry.model_dump() for entry in runtime.voice_info()]}

    @app.post("/v1/warmup")
    async def warmup(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        model_alias = str((payload or {}).get("model") or resolved_config.model2_alias)
        result = runtime.warmup(model_alias)
        return result.model_dump()

    @app.post("/v1/audio/speech")
    async def synthesize(payload: ProviderSpeechRequest) -> dict[str, Any]:
        result = runtime.synthesize(payload)
        return result.model_dump()

    @app.post("/v1/stream/start")
    async def start_stream(payload: ProviderStreamStartRequest) -> dict[str, Any]:
        return runtime.start_stream(payload)

    @app.post("/v1/stream/{session_id}/text")
    async def push_stream_text(session_id: str, payload: ProviderTextChunkRequest) -> dict[str, Any]:
        result = runtime.push_stream_text(session_id, payload.text)
        return result.model_dump()

    @app.post("/v1/stream/{session_id}/complete")
    async def complete_stream_text(session_id: str) -> dict[str, Any]:
        result = runtime.complete_stream_text(session_id)
        return result.model_dump()

    @app.post("/v1/stream/{session_id}/end")
    async def end_stream(session_id: str) -> dict[str, Any]:
        result = runtime.end_stream(session_id)
        return result.model_dump()

    return app


app = create_app()


def main() -> None:
    config = ExperimentConfig.from_env()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(
        create_app(config),
        host=config.provider_host,
        port=config.provider_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
