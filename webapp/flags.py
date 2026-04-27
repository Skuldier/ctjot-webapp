"""
Canonical flag/option registry for the Jets of Time beta web app.

Each entry maps a form field to:
  - its HTML input metadata (type, label, default, help)
  - the section it belongs to on the options page
  - the CLI argument(s) to pass to the beta randomizer when set

Source of truth: beta.ctjot.com's form (kebab-case names) cross-checked
against the beta randomizer's cli/arguments.py (GameFlags / CosmeticFlags
enums in sourcefiles/randosettings.py).

Flag entries that cannot be represented as simple CLI switches (notably
the bucket-list objective strings) are collected by the caller into a
multi-value --bucket-objectiveN form; see BUCKET_OBJECTIVE_ARG_NAMES.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class FlagDef:
    # Form field name (kebab-case, matches beta.ctjot.com).
    name: str
    # One of: checkbox, select, range, number, text, multiselect.
    input_type: str
    label: str
    # Display section on the options page.
    section: str
    # Default value (boolean for checkbox, string for select, int for range).
    default: Any = False
    # For select/multiselect: list of (value, display) tuples.
    choices: tuple[tuple[str, str], ...] = ()
    # For range/number: bounds.
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    # Tooltip / help text.
    help_text: str = ""
    # CLI argument to emit when this flag is set. For checkboxes, emitted
    # only if checked. For selects/ranges, emitted with the chosen value.
    # If None, the flag is passthrough-only (e.g. bucket objective text).
    cli_arg: Optional[str] = None
    # For checkbox flags: if True, emit cli_arg alone (a bare switch).
    # If False, emit cli_arg followed by the value.
    cli_bare_switch: bool = True


# --- Game Mode / difficulty / shop / tech ---
GAME_MODE = FlagDef(
    name="game-mode",
    input_type="select",
    label="Game Mode",
    section="General",
    default="std",
    choices=(
        ("std", "Standard"),
        ("lw", "Lost Worlds"),
        ("ia", "Ice Age"),
        ("loc", "Legacy of Cyrus"),
        ("van", "Vanilla Rando"),
    ),
    cli_arg="--mode",
    cli_bare_switch=False,
)

ENEMY_DIFFICULTY = FlagDef(
    name="enemy-difficulty",
    input_type="select",
    label="Enemy Difficulty",
    section="General",
    default="normal",
    choices=(("normal", "Normal"), ("hard", "Hard")),
    cli_arg="--enemy-difficulty",
    cli_bare_switch=False,
)

ITEM_DIFFICULTY = FlagDef(
    name="item-difficulty",
    input_type="select",
    label="Item Difficulty",
    section="General",
    default="normal",
    choices=(("easy", "Easy"), ("normal", "Normal"), ("hard", "Hard")),
    cli_arg="--item-difficulty",
    cli_bare_switch=False,
)

TECH_RANDO = FlagDef(
    name="tech-randomization",
    input_type="select",
    label="Tech Randomization",
    section="General",
    default="normal",
    choices=(
        ("normal", "Normal"),
        ("balanced", "Balanced Random"),
        ("random", "Random"),
    ),
    cli_arg="--tech-order",
    cli_bare_switch=False,
)

SHOP_PRICES = FlagDef(
    name="shop-prices",
    input_type="select",
    label="Shop Prices",
    section="General",
    default="normal",
    choices=(
        ("normal", "Normal"),
        ("free", "Free"),
        ("mostrandom", "Mostly Random"),
        ("random", "Fully Random"),
    ),
    cli_arg="--shop-prices",
    cli_bare_switch=False,
)


# --- Basic flags (GameFlags) ---
# cli_arg values sourced from sourcefiles/cli/constants.py / arguments.py.
_BASIC_FLAGS = [
    FlagDef("disable-glitches", "checkbox", "Disable Glitches", "General",
            cli_arg="--fix-glitch"),
    FlagDef("boss-scaling", "checkbox", "Boss Scaling", "General",
            cli_arg="--boss-scale"),
    FlagDef("early-pendant", "checkbox", "Early Pendant Charge", "General",
            cli_arg="--fast-pendant"),
    FlagDef("unlocked-magic", "checkbox", "Unlocked Magic", "General",
            cli_arg="--unlocked-magic"),
    FlagDef("chronosanity", "checkbox", "Chronosanity", "General",
            cli_arg="--chronosanity"),
    FlagDef("randomize-healing", "checkbox", "Randomize Healing Items",
            "General", cli_arg="--healing-item-rando"),
    FlagDef("mystery-seed", "checkbox", "Mystery Seed", "General",
            cli_arg="--mystery"),
    FlagDef("zeal-2-last", "checkbox", "Zeal 2 Counts As Last Boss",
            "General", cli_arg="--zeal-end"),
    FlagDef("locked-characters", "checkbox", "Locked Characters",
            "General", cli_arg="--locked-chars"),
    FlagDef("make-tabs", "checkbox", "All Treasures Are Tabs", "General",
            cli_arg="--tab-treasures"),
    FlagDef("randomize-bosses", "checkbox", "Randomize Bosses", "General",
            cli_arg="--boss-randomization"),
    FlagDef("randomize-characters", "checkbox", "Randomize Characters",
            "General", cli_arg="--char-rando"),
    FlagDef("randomize-gear", "checkbox", "Randomize Gear", "General",
            cli_arg="--gear-rando"),
    FlagDef("epoch-fail", "checkbox", "Epoch Fail", "General",
            cli_arg="--epoch-fail"),
]


# --- Character rando ---
_CHAR_RANDO_FLAGS = [
    FlagDef("duplicate-characters", "checkbox", "Duplicate Characters",
            "Character Rando", cli_arg="--duplicate-characters"),
    FlagDef("duplicate-dual-techs", "checkbox", "Duplicate Dual Techs",
            "Character Rando", cli_arg="--duplicate-techs"),
]

# Character-can-be multiselects (7 fields, Crono..Magus). Beta options
# allow any subset of the seven PCs. We model as multiselect.
_CHAR_CAN_BE_PCS = ("crono", "marle", "lucca", "robo", "frog", "ayla", "magus")
_CHAR_CAN_BE_FLAGS = [
    FlagDef(
        name=f"{pc}-can-be",
        input_type="multiselect",
        label=f"{pc.title()} can be",
        section="Character Rando",
        default=",".join(_CHAR_CAN_BE_PCS),
        choices=tuple((p, p.title()) for p in _CHAR_CAN_BE_PCS),
        cli_arg=f"--{pc}-choices",
        cli_bare_switch=False,
    )
    for pc in _CHAR_CAN_BE_PCS
]


# --- Boss rando sub-options ---
_BOSS_RANDO_FLAGS = [
    FlagDef("legacy-boss-placement", "checkbox", "Legacy Boss Placement",
            "Boss Rando", cli_arg="--legacy-boss-placement"),
    FlagDef("boss-spot-hps", "checkbox", "Boss Spot HPs", "Boss Rando",
            cli_arg="--boss-spot-hp"),
]


# --- Quality of Life ---
_QOL_FLAGS = [
    FlagDef("sightscope-always-on", "checkbox", "Sightscope Always On (visible health)",
            "Quality of Life", cli_arg="--visible-health"),
    FlagDef("boss-sightscope", "checkbox", "Boss Sightscope",
            "Quality of Life", cli_arg="--boss-sightscope"),
    FlagDef("fast-tabs", "checkbox", "Fast Tabs", "Quality of Life",
            cli_arg="--fast-tabs"),
    FlagDef("free-menu-glitch", "checkbox", "Free Menu Glitch",
            "Quality of Life", cli_arg="--free-menu-glitch"),
    FlagDef("visible-techlist", "checkbox", "Visible Techlist",
            "Quality of Life", cli_arg="--visible-techlist"),
    FlagDef("ap-classification-markers", "checkbox",
            "AP Classification Markers (red trap / purple prog / blue useful / brown filler)",
            "Quality of Life", default=True, cli_arg=None),
]


# --- Extra flags ---
_EXTRA_FLAGS = [
    FlagDef("starters-sufficient", "checkbox", "Starters Sufficient",
            "Extra", cli_arg="--starters-sufficient"),
    FlagDef("tech-damage-rando", "checkbox", "Tech Damage Rando",
            "Extra", cli_arg="--tech-damage-rando"),
    FlagDef("element-rando", "checkbox", "Element Rando", "Extra",
            cli_arg="--element-randomization"),
    FlagDef("tackle-on-hit", "checkbox", "Tackle On-Hit Effects",
            "Extra", cli_arg="--tackle-on-hit-effects"),
    FlagDef("use-anti-life", "checkbox", "Use Anti-Life", "Extra",
            cli_arg="--use-antilife"),
]


# --- Logic tweaks (new beta key-item-spot flags) ---
_LOGIC_TWEAK_FLAGS = [
    FlagDef("restore-johnny-race", "checkbox", "Restore Johnny Race",
            "Logic Tweaks", cli_arg="--restore-johnny-race"),
    FlagDef("restore-tools", "checkbox", "Restore Tools",
            "Logic Tweaks", cli_arg="--restore-tools"),
    FlagDef("add-bekkler-spot", "checkbox", "Add Bekkler Spot",
            "Logic Tweaks", cli_arg="--add-bekkler-spot"),
    FlagDef("add-cyrus-grave-spot", "checkbox", "Add Cyrus Grave Spot",
            "Logic Tweaks", cli_arg="--add-cyrus-spot"),
    FlagDef("add-ozzie-fort-spot", "checkbox", "Add Ozzie's Fort Spot",
            "Logic Tweaks", cli_arg="--add-ozzie-spot"),
    FlagDef("add-race-log-spot", "checkbox", "Add Race Log Spot",
            "Logic Tweaks", cli_arg="--add-racelog-spot"),
    FlagDef("add-sun-keep-spot", "checkbox", "Add Sun Keep Spot",
            "Logic Tweaks", cli_arg="--add-sunkeep-spot"),
    FlagDef("split-arris-dome", "checkbox", "Split Arris Dome",
            "Logic Tweaks", cli_arg="--split-arris-dome"),
    FlagDef("vanilla-robo-ribbon", "checkbox", "Vanilla Robo Ribbon",
            "Logic Tweaks", cli_arg="--vanilla-robo-ribbon"),
    FlagDef("vanilla-desert", "checkbox", "Vanilla Desert",
            "Logic Tweaks", cli_arg="--vanilla-desert"),
    FlagDef("remove-black-omen-spot", "checkbox", "Remove Black Omen Spot",
            "Logic Tweaks", cli_arg="--remove-black-omen-spot"),
    FlagDef("unlocked-skyways", "checkbox", "Unlocked Skyways",
            "Logic Tweaks", cli_arg="--unlocked-skyways"),
    FlagDef("rocksanity", "checkbox", "Rocksanity",
            "Logic Tweaks", cli_arg="--rocksanity"),
]


# --- Bucket list ---
_BUCKET_FLAGS = [
    FlagDef("bucket-list", "checkbox", "Enable Bucket List", "Bucket",
            cli_arg="--bucket-list"),
    FlagDef(
        name="num-objectives",
        input_type="range",
        label="Number of Objectives",
        section="Bucket",
        default=5, min_value=1, max_value=8,
        cli_arg="--bucket-objective-count", cli_bare_switch=False,
    ),
    FlagDef(
        name="num-required",
        input_type="range",
        label="Objectives Required",
        section="Bucket",
        default=4, min_value=1, max_value=8,
        cli_arg="--bucket-objective-needed-count", cli_bare_switch=False,
    ),
    FlagDef("disable-other-go-modes", "checkbox", "Disable Other Go Modes",
            "Bucket", cli_arg="--bucket-disable-other-go"),
    FlagDef("objectives-auto-win", "checkbox", "Objectives Auto-Win",
            "Bucket", cli_arg="--bucket-objectives-win"),
]

# Per-objective free-text specs. Emitted as --bucket-objective1..8.
BUCKET_OBJECTIVE_ARG_NAMES = tuple(f"--bucket-objective{i}" for i in range(1, 9))
_BUCKET_OBJECTIVE_FLAGS = [
    FlagDef(
        name=f"objective-{i}",
        input_type="text",
        label=f"Objective {i}",
        section="Bucket",
        default="",
        cli_arg=BUCKET_OBJECTIVE_ARG_NAMES[i - 1],
        cli_bare_switch=False,
    )
    for i in range(1, 9)
]


# --- Tab ranges ---
_TAB_FLAGS = [
    FlagDef("power-tab-min", "number", "Power Tab Min", "Tabs",
            default=1, min_value=1, max_value=9,
            cli_arg="--min-power-tab", cli_bare_switch=False),
    FlagDef("power-tab-max", "number", "Power Tab Max", "Tabs",
            default=1, min_value=1, max_value=9,
            cli_arg="--max-power-tab", cli_bare_switch=False),
    FlagDef("magic-tab-min", "number", "Magic Tab Min", "Tabs",
            default=1, min_value=1, max_value=9,
            cli_arg="--min-magic-tab", cli_bare_switch=False),
    FlagDef("magic-tab-max", "number", "Magic Tab Max", "Tabs",
            default=1, min_value=1, max_value=9,
            cli_arg="--max-magic-tab", cli_bare_switch=False),
    FlagDef("speed-tab-min", "number", "Speed Tab Min", "Tabs",
            default=1, min_value=1, max_value=9,
            cli_arg="--min-speed-tab", cli_bare_switch=False),
    FlagDef("speed-tab-max", "number", "Speed Tab Max", "Tabs",
            default=1, min_value=1, max_value=9,
            cli_arg="--max-speed-tab", cli_bare_switch=False),
]


# --- Cosmetic ---
_COSMETIC_FLAGS = [
    FlagDef("autorun", "checkbox", "Auto-run (run button walks)",
            "Cosmetic", cli_arg="--autorun"),
    FlagDef("quiet-mode", "checkbox", "Quiet Mode", "Cosmetic",
            cli_arg="--quiet"),
    FlagDef("reduce-flash", "checkbox", "Reduce Flashing", "Cosmetic",
            cli_arg="--reduce-flashes"),
    FlagDef("death-peak-alt-music", "checkbox", "Death Peak Alt Music",
            "Cosmetic", cli_arg="--death-peak-alt-music"),
    FlagDef("zenan-alt-music", "checkbox", "Zenan Alt Music",
            "Cosmetic", cli_arg="--zenan-alt-music"),
]


# --- Character names ---
# Each PC (plus Epoch) has a --{name}-name CLI arg. Beta enforces length
# limits internally; we pass the raw value through.
_CHAR_NAMES_ORDER = ("crono", "marle", "lucca", "robo", "frog", "ayla",
                     "magus", "epoch")
_CHAR_NAME_FLAGS = [
    FlagDef(
        name=f"{c}-name",
        input_type="text",
        label=f"{c.title()} name",
        section="Character Names",
        default=c.title(),
        cli_arg=f"--{c}-name",
        cli_bare_switch=False,
        help_text="Max 5 characters (beta limit).",
    )
    for c in _CHAR_NAMES_ORDER
]


# --- Mystery seed sub-controls ---
# All only take effect when --mystery is set; harmless otherwise.
_MYSTERY_MODE_FLAGS = [
    FlagDef("mystery-mode-std",  "number", "Mystery: Standard weight",
            "Mystery", default=75, min_value=0, max_value=100,
            cli_arg="--mystery-mode-std",  cli_bare_switch=False),
    FlagDef("mystery-mode-lw",   "number", "Mystery: Lost Worlds weight",
            "Mystery", default=25, min_value=0, max_value=100,
            cli_arg="--mystery-mode-lw",   cli_bare_switch=False),
    FlagDef("mystery-mode-loc",  "number", "Mystery: LoC weight",
            "Mystery", default=0,  min_value=0, max_value=100,
            cli_arg="--mystery-mode-loc",  cli_bare_switch=False),
    FlagDef("mystery-mode-ia",   "number", "Mystery: Ice Age weight",
            "Mystery", default=0,  min_value=0, max_value=100,
            cli_arg="--mystery-mode-ia",   cli_bare_switch=False),
    FlagDef("mystery-mode-van",  "number", "Mystery: Vanilla Rando weight",
            "Mystery", default=0,  min_value=0, max_value=100,
            cli_arg="--mystery-mode-van",  cli_bare_switch=False),
]

_MYSTERY_DIFFICULTY_FLAGS = [
    FlagDef("mystery-item-easy",  "number", "Mystery: Item easy weight",
            "Mystery", default=15, min_value=0, max_value=100,
            cli_arg="--mystery-item-easy",  cli_bare_switch=False),
    FlagDef("mystery-item-norm",  "number", "Mystery: Item normal weight",
            "Mystery", default=70, min_value=0, max_value=100,
            cli_arg="--mystery-item-norm",  cli_bare_switch=False),
    FlagDef("mystery-item-hard",  "number", "Mystery: Item hard weight",
            "Mystery", default=15, min_value=0, max_value=100,
            cli_arg="--mystery-item-hard",  cli_bare_switch=False),
    FlagDef("mystery-enemy-norm", "number", "Mystery: Enemy normal weight",
            "Mystery", default=75, min_value=0, max_value=100,
            cli_arg="--mystery-enemy-norm", cli_bare_switch=False),
    FlagDef("mystery-enemy-hard", "number", "Mystery: Enemy hard weight",
            "Mystery", default=25, min_value=0, max_value=100,
            cli_arg="--mystery-enemy-hard", cli_bare_switch=False),
]

_MYSTERY_TECH_SHOP_FLAGS = [
    FlagDef("mystery-tech-norm",          "number", "Mystery: Tech normal weight",
            "Mystery", default=10, min_value=0, max_value=100,
            cli_arg="--mystery-tech-norm",          cli_bare_switch=False),
    FlagDef("mystery-tech-balanced",      "number", "Mystery: Tech balanced weight",
            "Mystery", default=10, min_value=0, max_value=100,
            cli_arg="--mystery-tech-balanced",      cli_bare_switch=False),
    FlagDef("mystery-tech-rand",          "number", "Mystery: Tech random weight",
            "Mystery", default=80, min_value=0, max_value=100,
            cli_arg="--mystery-tech-rand",          cli_bare_switch=False),
    FlagDef("mystery-prices-norm",        "number", "Mystery: Prices normal weight",
            "Mystery", default=70, min_value=0, max_value=100,
            cli_arg="--mystery-prices-norm",        cli_bare_switch=False),
    FlagDef("mystery-prices-mostly-rand", "number", "Mystery: Prices mostly-random weight",
            "Mystery", default=10, min_value=0, max_value=100,
            cli_arg="--mystery-prices-mostly-rand", cli_bare_switch=False),
    FlagDef("mystery-prices-rand",        "number", "Mystery: Prices random weight",
            "Mystery", default=10, min_value=0, max_value=100,
            cli_arg="--mystery-prices-rand",        cli_bare_switch=False),
    FlagDef("mystery-prices-free",        "number", "Mystery: Prices free weight",
            "Mystery", default=10, min_value=0, max_value=100,
            cli_arg="--mystery-prices-free",        cli_bare_switch=False),
]

# Per-flag probabilities: beta wants floats in [0.0, 1.0]. Use text
# inputs so users can enter decimal probabilities.
_MYSTERY_PROB_FLAGS = [
    FlagDef("mystery-flag-tab-treasures",   "text", "Mystery: P(Tab Treasures)",
            "Mystery", default="0.10",
            cli_arg="--mystery-flag-tab-treasures",   cli_bare_switch=False),
    FlagDef("mystery-flag-unlocked-magic",  "text", "Mystery: P(Unlocked Magic)",
            "Mystery", default="0.50",
            cli_arg="--mystery-flag-unlocked-magic",  cli_bare_switch=False),
    FlagDef("mystery-flag-bucket-list",     "text", "Mystery: P(Bucket List)",
            "Mystery", default="0.15",
            cli_arg="--mystery-flag-bucket-list",     cli_bare_switch=False),
    FlagDef("mystery-flag-chronosanity",    "text", "Mystery: P(Chronosanity)",
            "Mystery", default="0.50",
            cli_arg="--mystery-flag-chronosanity",    cli_bare_switch=False),
    FlagDef("mystery-flag-boss-rando",      "text", "Mystery: P(Boss Rando)",
            "Mystery", default="0.50",
            cli_arg="--mystery-flag-boss-rando",      cli_bare_switch=False),
    FlagDef("mystery-flag-boss-scaling",    "text", "Mystery: P(Boss Scaling)",
            "Mystery", default="0.10",
            cli_arg="--mystery-flag-boss-scaling",    cli_bare_switch=False),
    FlagDef("mystery-flag-locked-chars",    "text", "Mystery: P(Locked Chars)",
            "Mystery", default="0.25",
            cli_arg="--mystery-flag-locked-chars",    cli_bare_switch=False),
    FlagDef("mystery-flag-char-rando",      "text", "Mystery: P(Char Rando)",
            "Mystery", default="0.50",
            cli_arg="--mystery-flag-char-rando",      cli_bare_switch=False),
    FlagDef("mystery-flag-duplicate-chars", "text", "Mystery: P(Duplicate Chars)",
            "Mystery", default="0.25",
            cli_arg="--mystery-flag-duplicate-chars", cli_bare_switch=False),
    FlagDef("mystery-flag-epoch-fail",      "text", "Mystery: P(Epoch Fail)",
            "Mystery", default="0.50",
            cli_arg="--mystery-flag-epoch-fail",      cli_bare_switch=False),
    FlagDef("mystery-flag-gear-rando",      "text", "Mystery: P(Gear Rando)",
            "Mystery", default="0.25",
            cli_arg="--mystery-flag-gear-rando",      cli_bare_switch=False),
    FlagDef("mystery-flag-heal-rando",      "text", "Mystery: P(Heal Rando)",
            "Mystery", default="0.25",
            cli_arg="--mystery-flag-heal-rando",      cli_bare_switch=False),
]

_MYSTERY_FLAGS = (
    _MYSTERY_MODE_FLAGS
    + _MYSTERY_DIFFICULTY_FLAGS
    + _MYSTERY_TECH_SHOP_FLAGS
    + _MYSTERY_PROB_FLAGS
)


# --- Multiworld-only additions ---
# This local generator targets multiworld play exclusively. The webapp
# emits a YAML; ROM generation happens at apply-time on the player's
# machine (see Archipelago-0.0.4/worlds/ctjot/), so there's no
# spoiler-log option here -- AP's own Generate.py emits a multiworld
# spoiler alongside the patch when needed.
_MULTIWORLD_FLAGS = [
    FlagDef(
        name="player-name",
        input_type="text",
        label="Player Name (multiworld slot)",
        section="Multiworld",
        default="Player1",
        help_text="Your slot name in the multiworld.",
    ),
    FlagDef(
        name="progression-balancing",
        input_type="range",
        label="Progression Balancing",
        section="Multiworld",
        default=50, min_value=0, max_value=99,
        help_text=(
            "Algorithm for moving progression items into earlier spheres to "
            "prevent getting stuck or bored early. A lower setting means more "
            "getting stuck; a higher setting means less. "
            "0 = disabled, 50 = normal (default), 99 = extreme."
        ),
    ),
    FlagDef(
        name="priority-ki-locations",
        input_type="checkbox",
        label="Prioritize Key Item Locations",
        section="Multiworld",
        default=False,
        help_text=(
            "Marks every Key Item spot in this seed as a priority location, "
            "forcing progression items onto them when AP fills the multiworld. "
            "Progression items without a deprioritized flag are used first; "
            "deprioritized progression items are used next. Useful when your "
            "slot has few checks compared to others -- guarantees the checks "
            "you do have hold meaningful items."
        ),
    ),
    FlagDef(
        name="accessibility",
        input_type="select",
        label="Accessibility",
        section="Multiworld",
        default="full",
        choices=(("full", "Full"), ("minimal", "Minimal")),
        help_text=(
            "Sets rules for reachability of your items/locations. "
            "Full: ensure everything can be reached and acquired. "
            "Minimal: ensure only what is needed to reach your goal "
            "can be acquired."
        ),
    ),
]


ALL_FLAGS: tuple[FlagDef, ...] = tuple(
    [GAME_MODE, ENEMY_DIFFICULTY, ITEM_DIFFICULTY, TECH_RANDO, SHOP_PRICES]
    + _BASIC_FLAGS
    + _TAB_FLAGS
    + _CHAR_RANDO_FLAGS
    + _CHAR_CAN_BE_FLAGS
    + _BOSS_RANDO_FLAGS
    + _QOL_FLAGS
    + _EXTRA_FLAGS
    + _LOGIC_TWEAK_FLAGS
    + _BUCKET_FLAGS
    + _BUCKET_OBJECTIVE_FLAGS
    + _COSMETIC_FLAGS
    + _CHAR_NAME_FLAGS
    + _MYSTERY_FLAGS
    + _MULTIWORLD_FLAGS
)


FLAGS_BY_NAME: dict[str, FlagDef] = {f.name: f for f in ALL_FLAGS}


# Ordered list of sections for template rendering.
SECTIONS: tuple[str, ...] = (
    "General",
    "Tabs",
    "Character Rando",
    "Boss Rando",
    "Quality of Life",
    "Extra",
    "Logic Tweaks",
    "Bucket",
    "Cosmetic",
    "Character Names",
    "Mystery",
    "Multiworld",
)


def flags_for_section(section: str) -> list[FlagDef]:
    return [f for f in ALL_FLAGS if f.section == section]


def coerce_form_value(flag: FlagDef, raw: Optional[str]) -> Any:
    """Coerce a raw form string to the flag's typed value."""
    if flag.input_type == "checkbox":
        return raw is not None and raw not in ("", "0", "off", "false")
    if flag.input_type in ("range", "number"):
        if raw is None or raw == "":
            return flag.default
        try:
            return int(raw)
        except (TypeError, ValueError):
            return flag.default
    if flag.input_type == "multiselect":
        if not raw:
            return list(flag.default.split(",")) if isinstance(flag.default, str) else []
        return [v for v in raw.split(",") if v]
    return raw if raw is not None else flag.default


def build_cli_args(values: dict[str, Any]) -> list[str]:
    """Convert the validated form `values` dict into beta randomizer CLI args.

    Skips web-app-only flags (player-name, seed) whose cli_arg is None.
    """
    args: list[str] = []
    for flag in ALL_FLAGS:
        if flag.cli_arg is None:
            continue
        v = values.get(flag.name, flag.default)
        if flag.input_type == "checkbox":
            if v:
                args.append(flag.cli_arg)
            continue
        if flag.input_type == "multiselect":
            # Beta splits character-choice values on whitespace, not commas.
            # When every PC is selected we emit nothing (that's the default);
            # otherwise emit the space-joined selection.
            if not v:
                continue
            sel = v if isinstance(v, list) else [s for s in str(v).split(",") if s]
            if set(sel) == set(_CHAR_CAN_BE_PCS):
                continue  # default: all seven => no arg
            args.extend([flag.cli_arg, " ".join(sel)])
            continue
        if flag.input_type == "text" and not v:
            continue
        # select / range / number / non-empty text
        args.extend([flag.cli_arg, str(v)])
    return args
