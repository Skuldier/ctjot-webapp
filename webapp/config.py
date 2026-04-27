"""
Configuration for the Jets of Time web app.

Values can be overridden via environment variables of the same name,
prefixed with CTJOT_ (e.g. CTJOT_PORT=8080).

The webapp is now stateless -- it builds an Archipelago YAML from
form input and returns it as a download. There is no per-seed
storage, no ROM generation, and no apworld-checkout dependency.
"""
from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    return os.environ.get(f"CTJOT_{name}", default)


# --- App behavior ---

HOST = _env("HOST", "127.0.0.1")
PORT = int(_env("PORT", "5000"))
DEBUG = _env("DEBUG", "0") == "1"

# Maximum accepted POST size in bytes. The webapp doesn't accept
# uploads (it's a YAML editor); we keep a small ceiling so large
# accidental form payloads still fail-fast in Flask.
MAX_UPLOAD_BYTES = int(_env("MAX_UPLOAD_BYTES", str(1 * 1024 * 1024)))
