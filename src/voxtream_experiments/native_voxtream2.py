from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

from .config import ExperimentConfig
from .event_log import EventLogger


class QueueTextIterator:
    def __init__(self, queue: "queue.Queue[str | None]") -> None:
        self._queue = queue

    def __iter__(self) -> "QueueTextIterator":
        return self

    def __next__(self) -> str:
        item = self._queue.get()
        if item is None:
            raise StopIteration
        return item


class Voxtream2NativeRunner:
    def __init__(self, config: ExperimentConfig, event_logger: EventLogger) -> None:
        self.config = config
        self.event_logger = event_logger
        self._generator: Any | None = None
        self._generator_config: Any | None = None
        self._speaking_rate_config: dict[str, Any] | None = None
        self._load_lock = threading.Lock()

    def load(self) -> None:
        if self._generator is not None:
            return
        with self._load_lock:
            if self._generator is not None:
                return

            import voxtream.utils.generator.setup as setup_mod
            from voxtream.config import SpeechGeneratorConfig
            from voxtream.generator import SpeechGenerator
            from voxtream.utils.generator import set_seed

            original_download = setup_mod.hf_hub_download

            def local_or_hub_download(repo_id: str, filename: str, *args: Any, **kwargs: Any) -> str:
                repo_path = Path(repo_id)
                if repo_path.exists():
                    local_file = repo_path / filename
                    if not local_file.exists():
                        raise FileNotFoundError(f"Expected local model artifact is missing: {local_file}")
                    return str(local_file)
                return original_download(repo_id, filename, *args, **kwargs)

            setup_mod.hf_hub_download = local_or_hub_download

            with self.config.generator_config_path.open() as fh:
                generator_params = json.load(fh)
            generator_params["model_repo"] = self.config.model_path

            self._generator_config = SpeechGeneratorConfig(**generator_params)
            if self.config.speaking_rate_config_path.exists():
                with self.config.speaking_rate_config_path.open() as fh:
                    self._speaking_rate_config = json.load(fh)
            else:
                self._speaking_rate_config = {}

            set_seed()
            started = time.perf_counter()
            self._generator = SpeechGenerator(self._generator_config)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self.event_logger.emit(
                "native_voxtream2_loaded",
                model_path=self.config.model_path,
                elapsed_ms=elapsed_ms,
            )

    def sample_rate(self) -> int:
        self.load()
        return int(self._generator_config.mimi_sr)

    def _resolve_speaking_rate(self, speaking_rate: float | None) -> tuple[list[int] | None, float | None, float | None]:
        if speaking_rate is None:
            return None, None, None
        from voxtream.utils.generator import interpolate_speaking_rate_params

        if not self._speaking_rate_config:
            return None, None, None
        return interpolate_speaking_rate_params(
            self._speaking_rate_config,
            speaking_rate,
            logger=getattr(self._generator, "logger", None),
        )

    def generate_stream(
        self,
        *,
        prompt_audio_path: Path,
        text: str | Iterator[str],
        speaking_rate: float | None = None,
    ) -> Iterator[tuple[np.ndarray, float]]:
        self.load()
        target_spk_rate_cnt, spk_rate_weight, cfg_gamma = self._resolve_speaking_rate(speaking_rate)
        stream = self._generator.generate_stream(
            prompt_audio_path=prompt_audio_path,
            text=text,
            target_spk_rate_cnt=target_spk_rate_cnt,
            spk_rate_weight=spk_rate_weight,
            cfg_gamma=cfg_gamma,
        )
        for audio_frame, gen_time in stream:
            yield np.asarray(audio_frame, dtype=np.float32), float(gen_time or 0.0)
