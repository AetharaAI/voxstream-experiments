from __future__ import annotations

import json

import typer

from .config import ExperimentConfig

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Voxtream experiments CLI root."""


@app.command("doctor")
def doctor(
    env_file: str | None = typer.Option(None, help="Optional .env file path."),
) -> None:
    from .runtime import ProviderRuntime

    config = ExperimentConfig.from_env(env_file)
    runtime = ProviderRuntime(config)
    typer.echo(json.dumps(runtime.health_payload(), indent=2, sort_keys=True))


@app.command("serve")
def serve(
    env_file: str | None = typer.Option(None, help="Optional .env file path."),
) -> None:
    if env_file:
        ExperimentConfig.from_env(env_file)
    from .provider_server import main as provider_main

    provider_main()


if __name__ == "__main__":
    app()
