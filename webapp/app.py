"""
Jets of Time web app -- Flask entry point.

Run (local dev):
    python -m webapp.app
or:
    python webapp/app.py

Run (production, e.g. on Render):
    gunicorn webapp.app:app -b 0.0.0.0:$PORT --workers 2

YAML editor for the bundled ctjot apworld. Provides full
beta.ctjot.com flag parity plus the multiworld experimental flags;
emits an Archipelago YAML the player drops into AP's Players/
folder. ROM generation lives inside the apworld
(Archipelago-0.0.4/worlds/ctjot/) and runs at AP Generate.py time
on the player's side, not here.

Stateless: the webapp builds the YAML from form input and returns
it directly as a download. No per-seed storage, no share links,
no apworld-checkout dependency at runtime.

Routes:
    GET  /            landing
    GET  /options/    options form (every YAML-tweakable apworld field)
    POST /generate/   build YAML from form values, return as a download
    GET  /healthz     health check (200 OK) for load balancers / Render
"""
from __future__ import annotations

# Allow `python webapp/app.py` to import the package cleanly.
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "webapp"

import logging
import os
import re
import secrets

from flask import Flask, Response, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf

from . import config as cfg
from . import flags as flag_registry
from . import yaml_emitter


app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = cfg.MAX_UPLOAD_BYTES

# Secret key for CSRF + Flask sessions. Pulled from env in production
# (Render generates one via render.yaml `generateValue: true`); falls
# back to a fresh random key in local dev so reloads don't need a
# pre-set value.
app.config["SECRET_KEY"] = (
    os.environ.get("FLASK_SECRET_KEY")
    or os.environ.get("CTJOT_SECRET_KEY")
    or secrets.token_hex(32)
)

# Trust X-Forwarded-* headers from Render's edge proxy so request.url_for
# generates https URLs and rate limits key on the real client IP rather
# than the proxy. ProxyFix(x_for=1) honors a single trusted proxy hop.
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# CSRF protection on all POST forms. Flask-WTF reads the token from a
# hidden field or X-CSRFToken header; rejects requests missing/invalid
# tokens with a 400.
csrf = CSRFProtect(app)

# Rate limiting. In-memory backend (Render free tier has no persistent
# Redis); resets on every deploy / instance restart, which is fine for
# spam mitigation since the IP key still bounds a single user. Defaults
# are conservative -- generation is cheap so 30/min is plenty.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["120 per hour", "30 per minute"],
    storage_uri="memory://",
)


# Make a CSRF token available to every template (forms render
# `<input name="csrf_token" value="{{ csrf_token() }}">`).
@app.context_processor
def _inject_csrf():
    return {"csrf_token": generate_csrf}


# Security headers added to every response. CSP is moderately tight:
# allows inline styles and scripts (the form uses both today) but
# forbids any external script/frame source.
@app.after_request
def _add_security_headers(resp: Response) -> Response:
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'",
    )
    # HSTS only meaningful when actually served over HTTPS. Render
    # terminates TLS at the edge; X-Forwarded-Proto tells us we're https.
    if request.headers.get("X-Forwarded-Proto") == "https":
        resp.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return resp


# Logging: route Flask's logger through standard logging so Render
# captures stdout/stderr lines as structured log events.
if not app.debug:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_yaml_filename(player_name: str) -> str:
    """Make a download filename out of a player's slot name.

    Strips anything that isn't alphanumeric / `_` / `.` / `-` so we
    don't emit a Content-Disposition header that's vulnerable to
    header-injection or filesystem traversal on the client side.
    """
    cleaned = _SAFE_FILENAME_CHARS.sub("_", (player_name or "").strip())
    cleaned = cleaned.strip("._") or "Player"
    return f"{cleaned}.yaml"


# -------- Routes --------

@app.get("/")
@limiter.exempt
def landing():
    return render_template(
        "index.html",
        multiworld_url=url_for("options_page"),
    )


@app.get("/options/")
@limiter.exempt
def options_page():
    defaults = {f.name: f.default for f in flag_registry.ALL_FLAGS}
    return render_template(
        "options.html",
        sections=flag_registry.SECTIONS,
        flags_for_section=flag_registry.flags_for_section,
        defaults=defaults,
    )


@app.post("/generate/")
@limiter.limit("10 per minute")
def generate():
    """Build a Jets of Time YAML from the form values and return it
    directly as an attachment. No server-side persistence."""
    # 1. Coerce form values through the flag registry.
    raw = request.form
    values: dict = {}
    for flag in flag_registry.ALL_FLAGS:
        if flag.input_type == "multiselect":
            values[flag.name] = raw.getlist(flag.name) or \
                (flag.default.split(",") if isinstance(flag.default, str) else [])
        else:
            values[flag.name] = flag_registry.coerce_form_value(flag, raw.get(flag.name))

    player_name = (values.get("player-name") or "Player1").strip() or "Player1"

    # 2. Emit the YAML.
    try:
        yaml_text = yaml_emitter.build_yaml(values)
    except Exception as exc:
        app.logger.exception("YAML generation failed")
        return render_template(
            "error.html",
            message=f"YAML generation failed: {exc}",
        ), 500

    # 3. Return as a download. No state stored.
    filename = _safe_yaml_filename(player_name)
    return Response(
        yaml_text,
        mimetype="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/healthz")
@limiter.exempt
def healthz():
    """Liveness probe for Render's load balancer. 200 = service up."""
    return Response("ok", mimetype="text/plain")


@app.errorhandler(413)
def _too_large(_e):
    return render_template(
        "error.html",
        message=f"Upload exceeds limit of {cfg.MAX_UPLOAD_BYTES} bytes.",
    ), 413


@app.errorhandler(404)
def _not_found(_e):
    return render_template("error.html", message="Not found."), 404


@app.errorhandler(429)
def _rate_limited(_e):
    return render_template(
        "error.html",
        message="Too many requests; slow down and try again in a minute.",
    ), 429


def main() -> None:
    app.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)


if __name__ == "__main__":
    main()
