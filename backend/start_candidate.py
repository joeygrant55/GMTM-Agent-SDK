"""Explicit candidate launcher; no installation, dotenv loading or schema work."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from collections.abc import Mapping


def command(environment: Mapping[str, str]) -> list[str]:
    port = environment.get("PORT", "8000")
    if not isinstance(port, str) or not port.isascii() or not port.isdecimal() or len(port) > 5 or not 1 <= int(port) <= 65535:
        raise ValueError("PORT must be an integer between 1 and 65535")
    return [
        sys.executable, "-m", "uvicorn", "candidate_app:app",
        "--app-dir", str(Path(__file__).resolve().parent),
        "--host", "0.0.0.0", "--port", str(int(port)),
        "--workers", "1", "--loop", "asyncio", "--http", "h11",
        "--lifespan", "on", "--no-access-log", "--no-proxy-headers",
    ]


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("Candidate launch options are fixed; configure PORT through the environment")
    try:
        args = command(os.environ)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    # Uvicorn's Click command reads UVICORN_* for unspecified options (including
    # reload and env-file). Keep application configuration, but fix server options.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("UVICORN_")}
    # Replace the launcher so Uvicorn receives process signals directly.
    os.execve(sys.executable, args, environment)


if __name__ == "__main__":
    main()
