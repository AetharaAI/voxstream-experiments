# Voxtream Provider API Contract - 2026-03-23

## Purpose

This contract defines the modular HTTP provider boundary between `voxtream-experiments` and the production `AetherVoice-X` stack.

The provider runs independently and joins the shared Docker network:

- `aether-voice-mesh`

The production stack talks to it over HTTP instead of embedding runner logic directly.

## Current scope

Intended experiment lanes:

- `voxtream_realtime`
- `voxtream2_realtime`

Current implementation state:

- health: implemented
- model discovery: implemented
- stream endpoint shapes: implemented
- native inference: not yet proven

## Endpoints

### `GET /health`

Returns provider liveness and dependency truth.

This route should return `200` only when the provider can actually attempt native runtime work.

### `GET /v1/models`

Returns available provider models.

Current result includes:

- `voxtream_realtime`
- `voxtream2_realtime`

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
  "metadata": {
    "extra": {
      "reference_audio_path": "/abs/path/to/reference.wav",
      "reference_text": "Optional prompt text for original Voxtream.",
      "generation_prompt": "Optional instruction prompt.",
      "realtime_profile": {
        "speaking_rate": 2.0
      }
    }
  }
}
```

### `POST /v1/stream/{session_id}/text`

Pushes incremental text into the active stream.

### `POST /v1/stream/{session_id}/complete`

Flushes the current text segment.

### `POST /v1/stream/{session_id}/end`

Ends the session and returns the final WAV artifact plus timing metadata.

## Integration rule

`AetherVoice-X` should rely only on the provider HTTP contract.

The main repo should not call internal runner modules directly.
