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
6. Pick the runtime lane you are actually testing first:
   - `voxtream2-provider` for `voxtream>=0.2`
   - `voxtream-provider` for original `voxtream==0.1.5`
7. Build the provider container:
   - `docker compose build voxtream2-provider`
8. Start the provider:
   - `docker compose up -d voxtream2-provider`
9. Inspect health:
   - `curl http://127.0.0.1:8075/health`
10. If health reports dependency failures, fix them before touching the production stack.

## Runtime truth

The upstream codebase currently forces a split:

- original `Voxtream` and `Voxtream2` ship under the same package name
- they do not share the same Python API
- they should not be treated as one interchangeable in-process model family

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
