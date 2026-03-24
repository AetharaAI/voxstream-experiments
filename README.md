# Voxtream Experiments

This directory is intentionally outside of `Aether-Voice-X`.

It exists to prove how `Voxtream` and `Voxtream2` should be served before either lane is treated as production-worthy inside the main voice platform.

Current purpose:

- validate `herimor/voxtream`
- validate `herimor/voxtream2`
- compare original `Voxtream` versus `Voxtream2` under the same L4 host
- expose a modular HTTP provider boundary for the production stack
- keep runner decisions outside the live platform until runtime truth is clear

Ground rules:

- stream first
- batch is optional and secondary
- log every meaningful handshake and state transition
- do not trust model cards until the L4 proves them
- do not edit the main platform to fit an unproven runner

Primary questions:

- which branch boots more reliably on the target L4
- which branch produces better first-chunk latency
- whether the original `Voxtream` prompt-text flow matters in telephony practice
- whether `Voxtream2` dynamic speaking-rate control is materially useful in live agent turns

The answer must come from runtime truth:

- boot reliability
- dependency pain
- actual first-audio latency
- chunk cadence
- audio continuity
- voice quality
- repeatability
- failure clarity
- GPU behavior

The main repo stays clean until one runner clearly wins.

## Runtime split

Upstream runtime truth matters here:

- original `Voxtream` uses the older `voxtream==0.1.5` line and requires `prompt_text`
- `Voxtream2` uses the newer `voxtream>=0.2` line and supports dynamic speaking-rate control
- both lines use the same package name but expose different APIs

So this repo treats them as separate container lanes, not one shared Python runtime.

## Provider boundary

This repo is meant to expose a modular Voxtream provider container surface:

- HTTP contract doc: `docs/VOXTREAM_PROVIDER_API_CONTRACT_2026-03-23.md`
- FastAPI app: `src/voxtream_experiments/provider_server.py`
- container build: `Dockerfile`
- shared network compose: `docker-compose.yml`

This lets `Aether-Voice-X` call Voxtream over a shared Docker network instead of embedding runner logic directly.

## First commands

From the repo root:

- `cp .env.example .env`
- `./scripts/run_doctor.sh`
- `docker compose build voxtream2-provider`
- `docker compose up -d voxtream2-provider`
- `curl http://127.0.0.1:8075/health`

## Current status

This repo is scaffolded first.

Current implemented surfaces:

- config loading
- split container plan for `voxtream` and `voxtream2`
- provider models and request schemas
- event logging
- first-run dependency doctor
- health and model discovery endpoints
- native `Voxtream2` local-snapshot loading path
- stream contract shape

Current non-goals:

- pretending the runtime is ready before native proof exists
- hiding missing dependencies
- marking the provider healthy when it cannot actually serve traffic

## Environment

This workspace is managed with `uv`.

Target Python:

- `3.12`

Expected dependency lanes:

- base harness and logging utilities
- optional `native` extras for `voxtream`
- `dev` tools for linting and tests

## License

This experiment repo is released under the MIT license in `LICENSE`.

Upstream model weights, runtime packages, and third-party assets keep their own licenses.
