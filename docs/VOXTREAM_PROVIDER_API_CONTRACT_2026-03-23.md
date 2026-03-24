# Voxtream Provider API Contract - 2026-03-23

## Purpose

This contract defines the modular HTTP provider boundary between `voxtream-experiments` and the production `AetherVoice-X` stack.

The provider runs independently and joins the shared Docker network:

- `aether-voice-mesh`

The production stack talks to it over HTTP instead of embedding runner logic directly.

## Current scope

Intended experiment lanes:

- `voxtream_realtime` via a dedicated `voxtream==0.1.5` container
- `voxtream2_realtime` via a dedicated `voxtream>=0.2` container

Current implementation state:

- health: implemented
- model discovery: implemented
- stream endpoint shapes: implemented
- native `Voxtream2` loading path: implemented
- original `Voxtream` native runner: not yet implemented in this provider code

## Endpoints

### `GET /health`

Returns provider liveness and dependency truth.

This route should return `200` only when the provider can actually attempt native runtime work.

### `GET /v1/models`

Returns available provider models.

Current result includes the single model lane served by that container instance.

### `GET /v1/voices`

Returns the provider’s current voice contract.

For now this is intentionally minimal because Voxtream expects prompt-audio-driven voice identity, not a large built-in preset catalog.

### `POST /v1/warmup`

Forces dependency and model-path checks and returns readiness metadata.

### `POST /v1/audio/speech`

Optional batch generation endpoint.

This is intentionally non-primary for now. The telephony question here is stream-first behavior.

### `POST /v1/stream/start`

Starts a stream session.

Expected payload shape:

```json
{
  "session_id": "sess_123",
  "model": "voxtream2_realtime",
  "voice": "Dispatch Clone",
  "sample_rate": 24000,
  "format": "wav",
  "context_mode": "conversation",
  "prompt_audio_path": "/abs/path/to/reference.wav",
  "prompt_text": "Required for original Voxtream lane.",
  "speaking_rate": 2.0,
  "metadata": {
    "extra": {
      "reference_audio_path": "/abs/path/to/reference.wav"
    }
  }
}
```

Notes:

- `prompt_text` is required by the original `Voxtream` runtime line.
- `speaking_rate` applies to `Voxtream2`.

### `POST /v1/stream/{session_id}/text`

Pushes incremental text into the active stream.

### `POST /v1/stream/{session_id}/complete`

Flushes the current text segment.

### `POST /v1/stream/{session_id}/end`

Ends the session and returns the final WAV artifact plus timing metadata.

## Integration rule

`AetherVoice-X` should rely only on the provider HTTP contract.

The main repo should not call internal runner modules directly.
