"""
Archipelago YAML emitter for the Jets of Time local web app.

The modified ctjot apworld is YAML-driven: given a YAML with the right
shape, it creates AP Items and Locations and runs AP's placement logic.
This module produces such a YAML from the web-form values.

Schema the apworld expects (see Archipelago-0.0.4/worlds/ctjot/Options.py):

    Chrono Trigger Jets of Time:
      <player_name>:
        game_mode:        str   # "Standard" | "Lost worlds" | "Ice Age" |
                                # "Legacy of cyrus" | "Vanilla rando"
        item_difficulty:  str   # "Easy" | "Normal" | "Hard"
        tab_treasures:    int   # 0/1
        bucket_fragments: int   # 0/1
        fragment_count:   int
        bucket_list:      int   # 0/1 (new, beta)
        bucket_objectives_win:          int  # new, beta
        bucket_disable_other_go_modes:  int  # new, beta
        bucket_num_objectives:          int  # new, beta
        bucket_num_objectives_needed:   int  # new, beta
        bucket_objective_hints:         list[str]  # new, beta
        items:            list[{id: int}]
        region_list:      dict[str, list[str]]
        char_locations:   list[{name: str, character: str}]
        rules:            dict[str, list[list[str]]]
        victory:          list[list[str]]

LOGIC PRESET
------------
Rather than invoking the beta's logicfactory (its access rules are Python
lambdas, not serializable data), this emitter groups KI locations into
*time-period regions* and assigns each region a conservative set of
alternative access rules as lists of required items. The rules match
standard Chrono Trigger gating:

  - Open 1000 AD / 600 AD / Prehistory start areas -- sphere 1, no reqs.
  - Future (2300 AD) -- requires Pendant (canonical gate) OR Gate Key.
  - Mt Woe / Dark Ages -- requires Pendant + Clone (to trigger Dark Ages
    via the Mt Woe event chain, paired with Mid-Ages access).
  - Black Omen -- requires Pendant (for sphere 2) + a late-game marker.
  - Sidequests (Bekkler/Cyrus/Ozzie/Sun Keep) -- each gated by its own
    specific KI per the experimental flag semantics.

This is stricter than "open" but deliberately conservative -- it will
occasionally reject placements that multiworld.ctjot.com would permit.
For the tightest possible logic, keep using multiworld.ctjot.com.
"""
from __future__ import annotations

import json
from typing import Any

import yaml  # PyYAML


# --- apworld data files ---
# Mirrored copies of Archipelago-0.0.4/worlds/ctjot/data/{item,location}_data.json.
# Kept inside the webapp package so the webapp is self-contained and can
# be deployed (e.g. to Fly.io / Render) without the apworld checkout
# sitting alongside it. If the apworld's data ever changes shape, refresh
# the copies in webapp/data/ to match.

def _load_apworld_json(name: str) -> dict[str, int]:
    import pkgutil
    data = pkgutil.get_data(__package__, f"data/{name}")
    if data is None:
        raise RuntimeError(
            f"webapp/data/{name} missing; the webapp package was built incorrectly."
        )
    return json.loads(data.decode("utf-8"))


def _load_item_data() -> dict[str, int]:
    return _load_apworld_json("item_data.json")


def _load_location_data() -> dict[str, int]:
    return _load_apworld_json("location_data.json")


# --- True Random resolution ---

# Fallback when the user disables every Random Pool category. Mirrors
# cjot-beta's built-in "Random" alias so we never emit an empty hint.
_TRUE_RANDOM_FALLBACK = "65:quest_gated, 30:boss_nogo, 15:recruit_gated"


def _resolve_true_random_pool(values: dict[str, Any]) -> str:
    """Build a cjot-beta weighted-hint string from the Random Pool tab.

    Reads the 7 categories defined in flags.TRUE_RANDOM_CATEGORIES.
    For each, if the user enabled it AND its weight is > 0, include
    "{weight}:{cjot_type}" in the comma-joined output. If no category
    is enabled, fall back to cjot-beta's default Random distribution.

    cjot-beta normalizes the weights, so they don't need to sum to 100.
    """
    from . import flags as _flags

    parts: list[str] = []
    for suffix, _label, ctype, _enabled_default, _weight_default, _tip in \
            _flags.TRUE_RANDOM_CATEGORIES:
        enabled = bool(values.get(f"true-random-{suffix}-enabled"))
        if not enabled:
            continue
        try:
            weight = int(values.get(f"true-random-{suffix}-weight") or 0)
        except (TypeError, ValueError):
            weight = 0
        if weight <= 0:
            continue
        parts.append(f"{weight}:{ctype}")
    return ", ".join(parts) if parts else _TRUE_RANDOM_FALLBACK


# --- name maps ---

# Map beta game-mode CLI values to the apworld's game_mode strings.
_GAME_MODE_DISPLAY = {
    "std": "Standard",
    "lw": "Lost worlds",
    "ia": "Ice Age",
    "loc": "Legacy of cyrus",
    "van": "Vanilla rando",
}

_ITEM_DIFFICULTY_DISPLAY = {
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
}


# Core KI items the apworld treats as progression. This list controls what
# ends up in the YAML `items` field for items that are *always* in the
# pool regardless of flag selection. Flag-conditional KIs go in
# _FLAG_CONDITIONAL_KIS below.
#
# Keep in sync with Items.py `_progression_items`.
_CORE_KEY_ITEMS = (
    "Bent Sword", "Bent Hilt", "Dreamstone", "Ruby Knife", "Gate Key",
    "Pendant", "Moon Stone", "Sun Stone", "PrismShard", "C. Trigger",
    "Hero Medal", "Grand Leon", "Clone", "Jerky", "Toma's Pop",
    "Robo's Rbn",
)

# KIs whose existence in the pool is gated on a beta flag. Without the
# matching flag, cjot-beta does not produce a KI location for that item
# (the corresponding quest is removed entirely), so AP would otherwise
# place these as "free" items at unrelated chests and the player would
# receive them despite never opting into the mechanic.
#
# Each tuple: (form_flag, item_name).
_FLAG_CONDITIONAL_KIS = (
    ("restore-tools",        "Tools"),
    ("epoch-fail",           "JetsOfTime"),
    ("split-arris-dome",     "Seed"),
    ("restore-johnny-race",  "Bike Key"),
    ("add-race-log-spot",    "Race Log"),
)

_ROCK_ITEMS = (
    "Black Rock", "Blue Rock", "SilverRock", "White Rock", "Gold Rock",
)


# --- Location classification ---
#
# These are the chronosanity treasure spots considered KI-eligible. For
# non-chronosanity seeds, AP will only place KIs at the named "KI spots"
# below; filler locations are handled by the apworld's add_filler_locations.

# Regions organized by time period / gating. Each entry holds:
#   (region_name, access_rules, location_names)
# access_rules is a list of alternatives; each alternative is a list of
# required item names (AND within alternative, OR between alternatives).
#
# `[]` as the only alternative means sphere-1 / always accessible.
#
# Items referenced here must be spelled exactly as in item_data.json so
# the apworld's rule evaluator (_get_access_rule in __init__.py) can
# resolve them via state.has(...).
_REGIONS: tuple[tuple[str, list[list[str]], tuple[str, ...]], ...] = (
    # Sphere 1 -- accessible from game start; no requirements.
    ("Open", [[]], (
        # 600 AD / 1000 AD open areas
        "Zenan Bridge Key", "Denadoro Mts Key", "Frogs Burrow Left",
        "Snail Stop Key", "Lazy Carpenter", "Taban Key", "Melchior Key",
        # Prehistory open (Dactyl/Forest Maze/Reptite)
        "Reptite Lair Key",
    )),

    # Requires opening the 600/1000 AD Fiona's Forest area (Robo).
    # Fiona's Shrine is in 600 AD but requires Robo (a recruit) to plant
    # trees; we gate on Robo as a stand-in.
    ("Fionas Shrine", [["Robo"]], (
        "Fiona Key",
    )),

    # Requires the Hero Medal (via Frog's Burrow) to reach King's Trial.
    ("Kings Trial", [["Hero Medal"]], (
        "Kings Trial Key",
    )),

    # Giants Claw: requires Tomas Pop (or Jerky to unblock the cave).
    ("Giants Claw", [["Toma's Pop"], ["Jerky"]], (
        "Giants Claw Key",
    )),

    # 2300 AD (Future): canonical gating is Pendant (opens sealed doors
    # including the Proto Dome exit) OR Gate Key (via Bangor / Factory).
    ("Future", [["Pendant"], ["Gate Key"]], (
        "Arris Dome Key", "Sun Palace Key", "Geno Dome Key",
    )),

    # Dark Ages: in standard play reached via Mt Woe after Zeal gate.
    # Requires Pendant (to open sealed doors into Zeal) + Clone (to get
    # past Pre-history → Zeal chain). Conservative rule; real logic is
    # richer.
    ("Dark Ages", [["Pendant", "Clone"], ["Gate Key", "Clone"]], (
        "Mt Woe Key",
    )),
)

# Flag-gated KI spots. Each tuple is (form_flag, region_name,
# access_rules, location_name). They're added only when the user
# enabled the matching experimental flag.
_FLAG_GATED_REGIONS: tuple[
    tuple[str, str, list[list[str]], str], ...
] = (
    # Bekkler: gated on C. Trigger (vanilla rando Bekkler cloning quest).
    ("add-bekkler-spot",
     "Bekklers Lab", [["C. Trigger"]], "Bekkler Key"),
    # Cyrus's Grave: gated on Frog being recruited.
    ("add-cyrus-grave-spot",
     "Northern Ruins Frog", [["Frog"]], "Cyrus Grave Key"),
    # Ozzie's Fort: requires Mt Woe clear in vanilla logic; approximate
    # with the same Dark Ages gate.
    ("add-ozzie-fort-spot",
     "Ozzies Fort", [["Pendant", "Clone"], ["Gate Key", "Clone"]],
     "Ozzies Fort Key"),
    # Race Log (Lab 32): requires Pendant + Bike Key.
    ("add-race-log-spot",
     "Lab 32 Race", [["Pendant", "Bike Key"], ["Gate Key", "Bike Key"]],
     "Lab 32 Race Log"),
    # Sun Keep 2300: requires Pendant + Gate Key + Moon Stone (grown sunstone).
    ("add-sun-keep-spot",
     "Sun Keep 2300", [["Pendant", "Moon Stone"], ["Gate Key", "Moon Stone"]],
     "Sun Keep 2300"),
    # Split Arris Dome (Seed corpse): same Future gating as the baseline
    # Arris Dome Key.
    ("split-arris-dome",
     "Arris Food Locker", [["Pendant"], ["Gate Key"]],
     "Arris Dome Food Locker Key"),
)

# Rocksanity spots (only when --rocksanity is enabled).
_ROCKSANITY_REGIONS: tuple[
    tuple[str, list[list[str]], str], ...
] = (
    # Denadoro Rock: open in the Denadoro Mts (sphere 1).
    ("Denadoro Rock",        [[]],                    "Denadoro Rock"),
    # Giants Claw Rock: inside Giants Claw -- same gate as Giants Claw Key.
    ("Giants Claw Rock",     [["Toma's Pop"], ["Jerky"]], "Giants Claw Rock"),
    # Kajar Rock: Dark Ages.
    ("Kajar Rock",           [["Pendant", "Clone"], ["Gate Key", "Clone"]],
     "Kajar Rock"),
    # Laruba Rock: Prehistory (Dactyl / Ruins), reachable once Ayla is
    # recruited via the standard Reptite Lair / Dactyl Nest path.
    ("Laruba Rock",          [["Ayla"]],              "Laruba Rock"),
    # Black Omen Rock: late-game. Require C. Trigger + Clone as a
    # reasonable proxy for the standard Black Omen gate.
    ("Black Omen Rock",      [["C. Trigger", "Clone"]],
     "Black Omen Terra Rock"),
)


# --- Character recruitment (always present) ---

# The seven default recruit spots with their canonical character. The web
# generator is expected to emit this list; the apworld consumes it as-is
# and creates event locations that auto-give the character.
# These mirror cjot-beta's base recruit dict (see
# characters/pcrecruit.get_base_recruit_dict). cjot-beta's recruit-spot
# enum has 7 slots and they don't all line up with vanilla CT
# (STARTER_2 = Magus, CATHEDRAL = Lucca, no NORTH_CAPE / no
# MILLENNIAL_FAIR). Names below are AP event-location names; cjot-beta
# only uses them via the apworld so they're free to be friendly.
_DEFAULT_CHAR_LOCATIONS = (
    {"name": "Crono's House",        "character": "Crono"},   # STARTER_1
    {"name": "Starter 2",            "character": "Magus"},   # STARTER_2
    {"name": "Manoria Cathedral",    "character": "Lucca"},   # CATHEDRAL
    {"name": "Guardia Castle",       "character": "Marle"},   # CASTLE
    {"name": "Frogs Burrow",         "character": "Frog"},    # FROGS_BURROW
    {"name": "Dactyl Nest",          "character": "Ayla"},    # DACTYL_NEST
    {"name": "Proto Dome",           "character": "Robo"},    # PROTO_DOME
)


# --- Emitter ---

def build_yaml(values: dict[str, Any]) -> str:
    """Produce an Archipelago YAML string from form values.

    `values` is the coerced dict produced by flags.coerce_form_value for
    every known field (see flags.ALL_FLAGS).
    """
    player_name = (values.get("player-name") or "Player1").strip() or "Player1"
    game_mode_raw = values.get("game-mode", "standard")
    item_diff_raw = values.get("item-difficulty", "normal")
    game_mode = _GAME_MODE_DISPLAY.get(game_mode_raw, "Standard")
    item_difficulty = _ITEM_DIFFICULTY_DISPLAY.get(item_diff_raw, "Normal")

    # --- Items list (YAML `items` field) ---
    item_data = _load_item_data()
    key_items = list(_CORE_KEY_ITEMS)
    for flag_name, item_name in _FLAG_CONDITIONAL_KIS:
        if values.get(flag_name):
            key_items.append(item_name)
    if values.get("rocksanity"):
        key_items.extend(_ROCK_ITEMS)

    yaml_items: list[dict[str, int]] = []
    for ki in key_items:
        if ki in item_data:
            yaml_items.append({"id": item_data[ki]})
        # else: silently skip -- guards against apworld/item mismatch

    # --- Region / rules construction ---
    location_data = _load_location_data()

    region_list: dict[str, list[str]] = {}
    rules: dict[str, list[list[str]]] = {}

    def _add_region(name: str, access: list[list[str]], locs: tuple[str, ...] | list[str]):
        known = [loc for loc in locs if loc in location_data]
        if not known:
            return
        region_list[name] = known
        rules[name] = access

    for region_name, access, locs in _REGIONS:
        _add_region(region_name, access, locs)

    for form_flag, region_name, access, loc_name in _FLAG_GATED_REGIONS:
        if not values.get(form_flag):
            continue
        # Bekkler & Cyrus are VR-exclusive unless the matching experimental
        # flag is set (which the outer condition already guarantees here).
        _add_region(region_name, access, (loc_name,))

    if values.get("rocksanity"):
        for region_name, access, loc_name in _ROCKSANITY_REGIONS:
            _add_region(region_name, access, (loc_name,))

    # Character locations use default names and each gets its own access
    # rule. Recruit spots are reachable in sphere 1 except a couple that
    # require late-game items.
    _CHAR_ACCESS: dict[str, list[list[str]]] = {
        # Sphere-1 starts: both starters spawn in your party from the
        # cold-boot Crono's-house intro.
        "Crono's House":     [[]],
        "Starter 2":         [[]],
        # Sphere-1 recruits: reachable in 1000 / 600 AD without KIs.
        "Manoria Cathedral": [[]],
        "Guardia Castle":    [[]],
        "Frogs Burrow":      [[]],
        "Dactyl Nest":       [[]],
        # Future-gated: Proto Dome needs Pendant or Gate Key.
        "Proto Dome":        [["Pendant"], ["Gate Key"]],
    }
    char_locations = [dict(d) for d in _DEFAULT_CHAR_LOCATIONS]
    for cl in char_locations:
        rules[cl["name"]] = _CHAR_ACCESS.get(cl["name"], [[]])

    # Items vs locations balance: when items > locations, AP fill errors
    # with "no more spots to place items" -- it doesn't silently drop. We
    # need to trim the item pool to match the location count BEFORE
    # emitting the YAML.
    #
    # Naive trim ("yaml_items[:total_ki_locs]") drops items from the END
    # of the list, which removes flag-conditional KIs (Bike Key, Race
    # Log) that are required by access rules. That breaks flag-gated
    # locations -- e.g. Lab 32 Race needs Bike Key, but the naive trim
    # dropped it, leaving the location unreachable.
    #
    # Smart trim: identify items REFERENCED by any access rule (those
    # are gate items the fill MUST be able to place); never trim those.
    # Trim filler-eligible items (those not in any rule) from the end
    # until items <= locations.
    #
    # The opposite case (items < locations) is handled by the apworld's
    # v1.4.7 top-up in create_items, which appends junk-fill items to
    # match yaml location count.
    total_ki_locs = sum(len(v) for v in region_list.values())
    if len(yaml_items) > total_ki_locs:
        # Build the set of item-IDs that any access rule references.
        rule_item_names: set[str] = set()
        for rule_alts in rules.values():
            for alt in rule_alts:
                rule_item_names.update(alt)
        rule_item_ids = {
            item_data[name] for name in rule_item_names if name in item_data
        }
        # Keep all rule-required items; trim non-required from the end.
        excess = len(yaml_items) - total_ki_locs
        new_items = list(yaml_items)
        # Walk from the end, removing non-required entries until we've
        # dropped `excess` of them. If we run out of non-required items
        # and still have excess, we fall through with items > locations
        # and fill will error -- but that means the user's access rules
        # genuinely require more items than they have locations for,
        # which is a YAML configuration problem we can't paper over.
        idx = len(new_items) - 1
        while excess > 0 and idx >= 0:
            if new_items[idx]["id"] not in rule_item_ids:
                del new_items[idx]
                excess -= 1
            idx -= 1
        yaml_items = new_items

    # Victory: require C. Trigger. This is a pragmatic single-item win
    # condition that avoids the brittle "collect every KI" rule and works
    # across all game modes (C. Trigger is always present as a KI).
    victory: list[list[str]] = [["C. Trigger"]]

    # --- Bucket-list passthrough ---
    # Bucket-list is in cjot-beta's forced-off list for LW/IA/LoC; mirror
    # the auto-drop here so downstream computations (fragments, objective
    # hints) reflect what cjot-beta will actually do.
    bucket_list_on = bool(values.get("bucket-list")) and game_mode_raw not in ("lw", "ia", "loc")
    bucket_fragments_on = not bucket_list_on and game_mode_raw != "lw"

    # Collect bucket objective free-text lines.
    #
    # Special handling for "Random (Custom)": resolve to a weighted hint
    # string assembled from the Random Pool tab's enabled categories.
    # cjot-beta natively parses the resulting "30:quest_gated, ..."
    # format (see _objective_hint_aliases in objectivehints.py).
    custom_random_str = _resolve_true_random_pool(values)
    objective_hints: list[str] = []
    if bucket_list_on:
        for i in range(1, 9):
            v = (values.get(f"objective-{i}") or "").strip()
            if not v:
                continue
            if v == "Random (Custom)":
                v = custom_random_str
            objective_hints.append(v)

    # --- TextChoice index mapping (matches apworld Options.py) ---
    _ENEMY_DIFF_INDEX = {"normal": 0, "hard": 1}
    _TECH_RANDO_INDEX = {"normal": 0, "balanced": 1, "fully_random": 2,
                         "random": 2}
    _SHOP_PRICES_INDEX = {"normal": 0, "fully_random": 1, "random": 1,
                          "mostly_random": 2, "free": 3}

    def _bool(name: str) -> int:
        return 1 if values.get(name) else 0

    # cjot-beta's ForcedFlags table (randosettings.py:148) silently
    # turns these off when the corresponding mode/flag is set. Mirror
    # the auto-drop here so the YAML reflects what cjot-beta will
    # actually use, even if a hand-edited form payload set both.
    _MODE_FORCED_OFF: dict[str, set[str]] = {
        "lw":  {"boss-scaling", "bucket-list", "epoch-fail",
                "add-bekkler-spot", "add-cyrus-grave-spot",
                "add-ozzie-fort-spot", "add-race-log-spot",
                "add-sun-keep-spot", "restore-johnny-race",
                "split-arris-dome", "restore-tools",
                "unlocked-skyways", "vanilla-desert",
                "vanilla-robo-ribbon", "rocksanity",
                "remove-black-omen-spot"},
        "ia":  {"zeal-2-last", "boss-scaling", "bucket-list",
                "add-bekkler-spot"},
        "loc": {"zeal-2-last", "bucket-list", "boss-scaling",
                "add-ozzie-fort-spot", "add-sun-keep-spot",
                "restore-tools", "restore-johnny-race",
                "split-arris-dome", "add-race-log-spot",
                "add-bekkler-spot"},
        "van": {"boss-scaling"},
    }
    _forced_off = _MODE_FORCED_OFF.get(game_mode_raw, set())
    if _bool("chronosanity"):
        _forced_off = _forced_off | {"boss-scaling"}

    def _bool_clamped(name: str) -> int:
        if name in _forced_off:
            return 0
        return _bool(name)

    def _int(name: str, default: int) -> int:
        try:
            return int(values.get(name, default))
        except (TypeError, ValueError):
            return default

    def _float_pct_to_pct100(name: str, default: int) -> int:
        """Convert webapp's "0.50"-style fields to a 0-100 int (apworld
        Range expects 0-100)."""
        raw_v = values.get(name, default)
        try:
            f = float(raw_v)
        except (TypeError, ValueError):
            return default
        if f <= 1.0:
            f = f * 100
        return max(0, min(100, int(round(f))))

    def _can_be_set(name: str, all_pcs: tuple[str, ...]) -> list[str]:
        sel = values.get(name)
        if not sel:
            return list(all_pcs)
        if isinstance(sel, str):
            sel = [s.strip() for s in sel.split(",") if s.strip()]
        try:
            return [s.lower() for s in sel if s]
        except TypeError:
            return list(all_pcs)

    pcs = ("crono", "marle", "lucca", "robo", "frog", "ayla", "magus")

    # If the user opted in, mark every Key Item spot present in this
    # seed as a priority location. region_list is already filtered by
    # the user's flag selection (15 baseline + each flag-gated extra
    # the user enabled + 5 rocks if rocksanity is on), so concatenating
    # its values gives exactly the KI spots that exist.
    priority_locations: list[str] = []
    if values.get("priority-ki-locations"):
        for region_locs in region_list.values():
            priority_locations.extend(region_locs)

    apworld_payload: dict[str, Any] = {
        # --- AP common options (PerGameCommonOptions) ---
        "progression_balancing": _int("progression-balancing", 50),
        "priority_locations": priority_locations,
        "accessibility": values.get("accessibility") or "full",
        # --- Game mode + difficulty (string-valued for apworld FreeText) ---
        "game_mode": game_mode,
        "item_difficulty": item_difficulty,
        # --- TextChoice options (integer indices) ---
        "enemy_difficulty":   _ENEMY_DIFF_INDEX.get(values.get("enemy-difficulty"), 0),
        "tech_randomization": _TECH_RANDO_INDEX.get(values.get("tech-randomization"), 0),
        "shop_prices":        _SHOP_PRICES_INDEX.get(values.get("shop-prices"), 0),
        # --- General toggles ---
        "tab_treasures":          _bool("make-tabs"),
        "disable_glitches":       _bool("disable-glitches"),
        "boss_scaling":           _bool_clamped("boss-scaling"),
        "early_pendant":          _bool("early-pendant"),
        "unlocked_magic":         _bool("unlocked-magic"),
        "chronosanity":           _bool("chronosanity"),
        "randomize_healing":      _bool("randomize-healing"),
        "mystery_seed":           _bool("mystery-seed"),
        "randomize_bosses":       _bool("randomize-bosses"),
        "zeal_2_last_boss":       _bool_clamped("zeal-2-last"),
        "locked_characters":      _bool("locked-characters"),
        "randomize_characters":   _bool("randomize-characters"),
        "randomize_gear":         _bool("randomize-gear"),
        "epoch_fail":             _bool_clamped("epoch-fail"),
        # --- Char rando ---
        "duplicate_characters":   _bool("duplicate-characters"),
        "duplicate_dual_techs":   _bool("duplicate-dual-techs"),
        # --- Boss rando ---
        "legacy_boss_placement":  _bool("legacy-boss-placement"),
        "boss_spot_hps":          _bool("boss-spot-hps"),
        # --- QoL ---
        "sightscope_always_on":   _bool("sightscope-always-on"),
        "boss_sightscope":        _bool("boss-sightscope"),
        "fast_tabs":              _bool("fast-tabs"),
        "free_menu_glitch":       _bool("free-menu-glitch"),
        "visible_techlist":       _bool("visible-techlist"),
        "ap_classification_markers": _bool("ap-classification-markers"),
        # --- Extra ---
        "starters_sufficient":    _bool("starters-sufficient"),
        "tech_damage_rando":      _bool("tech-damage-rando"),
        "element_rando":          _bool("element-rando"),
        "tackle_on_hit":          _bool("tackle-on-hit"),
        "use_anti_life":          _bool("use-anti-life"),
        # --- Logic tweaks: add KI ---
        "restore_johnny_race":    _bool_clamped("restore-johnny-race"),
        "restore_tools":          _bool_clamped("restore-tools"),
        # --- Logic tweaks: add/remove KI spot ---
        "add_bekkler_spot":       _bool_clamped("add-bekkler-spot"),
        "add_cyrus_grave_spot":   _bool_clamped("add-cyrus-grave-spot"),
        "add_ozzie_fort_spot":    _bool_clamped("add-ozzie-fort-spot"),
        "add_race_log_spot":      _bool_clamped("add-race-log-spot"),
        "vanilla_robo_ribbon":    _bool_clamped("vanilla-robo-ribbon"),
        "remove_black_omen_spot": _bool_clamped("remove-black-omen-spot"),
        # --- Logic tweaks: spot-neutral ---
        "add_sun_keep_spot":      _bool_clamped("add-sun-keep-spot"),
        "split_arris_dome":       _bool_clamped("split-arris-dome"),
        "vanilla_desert":         _bool_clamped("vanilla-desert"),
        "unlocked_skyways":       _bool_clamped("unlocked-skyways"),
        "rocksanity":             _bool_clamped("rocksanity"),
        # --- Cosmetics ---
        "auto_run":               _bool("autorun"),
        "quiet_mode":             _bool("quiet-mode"),
        "reduce_flash":           _bool("reduce-flash"),
        "death_peak_alt_music":   _bool("death-peak-alt-music"),
        "zenan_alt_music":        _bool("zenan-alt-music"),
        # --- Tab ranges ---
        # Tab min/max ranges: clamp so min <= max within each pair. The
        # randomizer would silently truncate (or reject) reversed pairs,
        # producing surprises; mirror that here so the YAML reflects
        # what cjot-beta will actually use.
        "power_tab_min": min(_int("power-tab-min", 1), _int("power-tab-max", 1)),
        "power_tab_max": max(_int("power-tab-min", 1), _int("power-tab-max", 1)),
        "magic_tab_min": min(_int("magic-tab-min", 1), _int("magic-tab-max", 1)),
        "magic_tab_max": max(_int("magic-tab-min", 1), _int("magic-tab-max", 1)),
        "speed_tab_min": min(_int("speed-tab-min", 1), _int("speed-tab-max", 1)),
        "speed_tab_max": max(_int("speed-tab-min", 1), _int("speed-tab-max", 1)),
        # --- Character names (5-char ASCII) ---
        "crono_name": str(values.get("crono-name") or "Crono")[:5],
        "marle_name": str(values.get("marle-name") or "Marle")[:5],
        "lucca_name": str(values.get("lucca-name") or "Lucca")[:5],
        "robo_name":  str(values.get("robo-name")  or "Robo")[:5],
        "frog_name":  str(values.get("frog-name")  or "Frog")[:5],
        "ayla_name":  str(values.get("ayla-name")  or "Ayla")[:5],
        "magus_name": str(values.get("magus-name") or "Magus")[:5],
        "epoch_name": str(values.get("epoch-name") or "Epoch")[:5],
        # --- Char-rando matrix (apworld OptionSet expects YAML lists) ---
        "crono_can_be": _can_be_set("crono-can-be", pcs),
        "marle_can_be": _can_be_set("marle-can-be", pcs),
        "lucca_can_be": _can_be_set("lucca-can-be", pcs),
        "robo_can_be":  _can_be_set("robo-can-be",  pcs),
        "frog_can_be":  _can_be_set("frog-can-be",  pcs),
        "ayla_can_be":  _can_be_set("ayla-can-be",  pcs),
        "magus_can_be": _can_be_set("magus-can-be", pcs),
        # --- Mystery weights ---
        "mystery_mode_std":  _int("mystery-mode-std",  75),
        "mystery_mode_lw":   _int("mystery-mode-lw",   25),
        "mystery_mode_loc":  _int("mystery-mode-loc",   0),
        "mystery_mode_ia":   _int("mystery-mode-ia",    0),
        "mystery_mode_van":  _int("mystery-mode-van",   0),
        "mystery_item_easy": _int("mystery-item-easy", 15),
        "mystery_item_norm": _int("mystery-item-norm", 70),
        "mystery_item_hard": _int("mystery-item-hard", 15),
        "mystery_enemy_norm": _int("mystery-enemy-norm", 75),
        "mystery_enemy_hard": _int("mystery-enemy-hard", 25),
        "mystery_tech_norm":     _int("mystery-tech-norm",     10),
        "mystery_tech_balanced": _int("mystery-tech-balanced", 10),
        "mystery_tech_rand":     _int("mystery-tech-rand",     80),
        "mystery_prices_norm":         _int("mystery-prices-norm",         70),
        "mystery_prices_mostly_rand":  _int("mystery-prices-mostly-rand",  10),
        "mystery_prices_rand":         _int("mystery-prices-rand",         10),
        "mystery_prices_free":         _int("mystery-prices-free",         10),
        # --- Mystery per-flag probabilities (form has "0.50" style;
        # apworld Range stores 0-100 percents) ---
        "mystery_flag_tab_treasures":   _float_pct_to_pct100("mystery-flag-tab-treasures",   10),
        "mystery_flag_unlocked_magic":  _float_pct_to_pct100("mystery-flag-unlocked-magic",  50),
        "mystery_flag_bucket_list":     _float_pct_to_pct100("mystery-flag-bucket-list",     15),
        "mystery_flag_chronosanity":    _float_pct_to_pct100("mystery-flag-chronosanity",    50),
        "mystery_flag_boss_rando":      _float_pct_to_pct100("mystery-flag-boss-rando",      50),
        "mystery_flag_boss_scaling":    _float_pct_to_pct100("mystery-flag-boss-scaling",    10),
        "mystery_flag_locked_chars":    _float_pct_to_pct100("mystery-flag-locked-chars",    25),
        "mystery_flag_char_rando":      _float_pct_to_pct100("mystery-flag-char-rando",      50),
        "mystery_flag_duplicate_chars": _float_pct_to_pct100("mystery-flag-duplicate-chars", 25),
        "mystery_flag_epoch_fail":      _float_pct_to_pct100("mystery-flag-epoch-fail",      50),
        "mystery_flag_gear_rando":      _float_pct_to_pct100("mystery-flag-gear-rando",      25),
        "mystery_flag_heal_rando":      _float_pct_to_pct100("mystery-flag-heal-rando",      25),
        # --- Bucket ---
        "bucket_fragments": 1 if bucket_fragments_on else 0,
        "fragment_count": 15,
        "bucket_list": 1 if bucket_list_on else 0,
        "bucket_objectives_win":         _bool("objectives-auto-win"),
        "bucket_disable_other_go_modes": _bool("disable-other-go-modes"),
        # Clamp: needed cannot exceed total (form sliders allow it; the
        # randomizer would either error or silently truncate). Floor at
        # 1 on both sides since 0 of 0 has no valid victory condition.
        "bucket_num_objectives":         max(1, min(8, _int("num-objectives", 5))),
        "bucket_num_objectives_needed":  max(
            1,
            min(
                max(1, min(8, _int("num-objectives", 5))),
                _int("num-required", 4),
            ),
        ),
        "bucket_objective_hints": objective_hints,
        # --- YAML-driven structural data the apworld still consumes ---
        "items": yaml_items,
        "region_list": region_list,
        "char_locations": char_locations,
        "rules": rules,
        "victory": victory,
    }

    payload = {
        "description": f"Jets of Time - {player_name}",
        "name": player_name,
        "game": "Chrono Trigger Jets of Time",
        "Chrono Trigger Jets of Time": apworld_payload,
    }

    return yaml.safe_dump(payload, sort_keys=False, width=1000)
