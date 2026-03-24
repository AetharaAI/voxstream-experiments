# Voxtream First Run Plan - 2026-03-23

## Goal

Bring up a runner-validation repo for:

- `herimor/voxtream`
- `herimor/voxtream2`

without disturbing the live `AetherVoice-X` platform.

## Expected VM truth

Model snapshots currently live at:

- `/mnt/aetherpro/models/voice/herimor/voxtream`
- `/mnt/aetherpro/models/voice/herimor/voxtream2`

## First run checklist

1. Create the sibling repo on the VM:
   - `~/aetherpro/voice-x/experiments/voxtream-experiments`
2. Copy the scaffolded repo contents there.
3. Create `.env` from `.env.example`.
4. Run first-pass dependency truth:
   - `./scripts/run_doctor.sh`
5. Confirm prerequisites:
   - `espeak-ng`
   - Python `3.12`
   - CUDA-visible GPU
6. Build the provider container:
   - `docker compose build`
7. Start the provider:
   - `docker compose up -d`
8. Inspect health:
   - `curl http://127.0.0.1:8074/health`
9. If health reports dependency failures, fix them before touching the production stack.

## Proof targets

Do not call the lane successful until runtime proof includes:

- process boots consistently
- health endpoint is truthful
- warmup succeeds
- first chunk latency is measured
- final audio is returned
- failures are logged clearly

## Promotion rule

Nothing from this repo should become a production default until it beats the current frozen `Voxtral ASR + Kokoro TTS` lane on real operator timing and quality tests.
