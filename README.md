# Chrono Trigger: Jets of Time — YAML Editor

A small Flask webapp that builds Archipelago YAMLs for the
[Chrono Trigger: Jets of Time](https://github.com/ArchipelagoMW/Archipelago)
apworld through a friendly form, instead of hand-editing ~120 fields.

The webapp emits YAML only — ROM generation runs at apply time on the
player's machine, inside the apworld. The webapp host never touches a
Chrono Trigger ROM.

## Live deployment

Deployed on [Render](https://render.com) free tier. The service
auto-deploys on every push to `main`.

## Workflow

1. User opens the webapp, fills in flags, clicks Generate.
2. Webapp returns a `.yaml` download.
3. User drops the YAML into their Archipelago install's `Players/`
   folder.
4. AP `Generate.py` runs the bundled apworld, which emits per-player
   `.apctjot` patches.
5. Each player double-clicks their `.apctjot`; AP's launcher prompts
   for their vanilla CT ROM, then patches and launches SNI + emulator.

## Local development

```bash
pip install -r requirements.txt
python -m webapp.app
```

Binds to `127.0.0.1:5000` by default. Override via `CTJOT_HOST` /
`CTJOT_PORT` env vars.

## Deployment to Render

The repo includes [`render.yaml`](render.yaml). Connect the repo to
Render via GitHub OAuth and Render reads the file automatically.

- Free tier: web service spins down after 15 min of no requests; cold
  start ~30s.
- Starter tier ($7/mo): always-on, no cold starts.

## Files

- `webapp/` — Flask app, templates, static assets, data files
- `requirements.txt` — pinned Python deps
- `render.yaml` — Render service definition
- `.gitignore` — excludes the local-only AP install, cjot-beta, and
  workspace artifacts not relevant to the deploy

## License

MIT (webapp code only). The bundled apworld and cjot-beta source live
in a separate workspace and are not included in this deploy repo.
