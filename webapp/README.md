# Jets of Time - Local YAML Editor

A small Flask webapp that builds Archipelago YAMLs for the Chrono
Trigger: Jets of Time apworld through a friendly form, instead of
hand-editing ~120 fields. The webapp emits YAML only -- ROM
generation runs at apply time on the player's machine, inside the
apworld at `Archipelago-0.0.4/worlds/ctjot/`.

## Workflow

1. Start the webapp (`run.bat`, or `python -m webapp.app`).
2. Open <http://127.0.0.1:5000/options/> in your browser.
3. Pick your flags. Every option on `beta.ctjot.com` plus the
   multiworld experimental flags is here, organized by tab.
4. Submit. The webapp emits a `.yaml` you can download.
5. Drop the YAML into your Archipelago install's `Players/`
   folder. (Whoever is running `Generate.py` does this -- it does
   not need to be the same machine that built the YAML.)
6. Run AP `Generate.py`. The apworld emits a per-player `.apctjot`
   patch (a small JSON bundle, ~3 KB) plus the multidata. **No
   Chrono Trigger ROM is consulted at this step**, so the
   generator host does not need one.
7. Distribute each `.apctjot` to its player.
8. Each player double-clicks their `.apctjot`. AP's launcher
   prompts once for their vanilla CT ROM, then patches and
   launches SNI + emulator.

## Why YAML editor only

The webapp used to generate ROMs locally and try to hand them off
to AP. Two persistent problems with that approach: (a) the AP
server's placements never matched the randomizer's, so players
saw "Got 1 Aeon Blade" while the server announced "Tester found
Kali Blade"; (b) every multidata reroll needed a fresh ROM. The
fix moved ROM generation inside the apworld at apply time: AP
runs Fill first, the apworld's `generate_output()` records every
placement decision into the `.apctjot`, and then on each player's
machine the apply-time procedure runs cjot-beta against their own
vanilla ROM and writes the AP placements selectively (own-slot
items use the real CT item byte, other-slot items use an
`AP Item` placeholder).

## Prerequisites

- Python 3.10+ (tested on 3.12).
- Flask + PyYAML (the webapp installs these on first run via
  `run.bat`).
- The bundled apworld at `Archipelago-0.0.4/worlds/ctjot/` --
  used at AP `Generate.py` time. The apworld carries its own
  pinned snapshot of cjot-beta at `worlds/ctjot/_beta/`, so the
  generator and player neither need a separate cjot-beta install.

## Run

From the workspace root:

```bash
python -m webapp.app
```

…or double-click `run.bat`.

The app binds to `127.0.0.1:5000` by default.
