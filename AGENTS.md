# AGENTS

## Repo Intent

`voxtream-experiments` is a runner-validation repo.

This repo exists to prove how `Voxtream` and `Voxtream2` should be served before anything is promoted into the production voice platform.

Current focus:

- `herimor/voxtream`
- `herimor/voxtream2`

## Working Rules

- stream first
- batch is fallback only
- log every meaningful boundary
- trust runtime truth over docs
- keep the harness simple and reusable
- avoid product-specific glue unless a runner has already been proven

## Logging Rule

Every runner should expose enough logs to answer:

- did the process start
- did the model load
- did the request begin
- when did first output happen
- when did final output happen
- where did it fail

## Promotion Rule

Nothing graduates into `Aether-Voice-X` until it proves:

1. stable boot
2. stable generation
3. clear logs
4. acceptable latency
5. acceptable quality
