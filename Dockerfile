FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

ARG VOXTREAM_PACKAGE_SPEC="voxtream>=0.2,<0.3"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git sox libsndfile1 espeak-ng python3.12 python3.12-venv python3.12-dev \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -sf /root/.local/bin/uv /usr/local/bin/uv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN uv sync --python /usr/bin/python3.12 \
    && uv pip install --python /app/.venv/bin/python "${VOXTREAM_PACKAGE_SPEC}"

CMD ["/app/.venv/bin/python", "-m", "voxtream_experiments.provider_server"]
