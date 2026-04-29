/* Jets of Time - local generator
 * UI behavior: tab switching, toggle pill state, slider<->number mirroring,
 * preset application, character-matrix helpers, multiworld section gating.
 */
(function () {
  "use strict";

  // ---------- Tabs ----------
  const tabs   = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".tab-panel");
  tabs.forEach((t) => {
    t.addEventListener("click", () => {
      const target = t.dataset.tab;
      tabs.forEach((x)   => x.classList.toggle("active", x === t));
      panels.forEach((p) => p.classList.toggle("active", p.dataset.panel === target));
    });
  });

  // ---------- Slider <-> number mirror (Tabs tab + Bucket sliders) ----------
  document.querySelectorAll('input[type="range"][name]').forEach((range) => {
    const mirror = document.querySelector(`[data-mirror="${range.name}"]`);
    if (!mirror) return;
    const sync = (src, dst, asText) => {
      const v = src.value;
      if (asText && dst.dataset.suffix) dst.value = v + dst.dataset.suffix;
      else dst.value = v;
    };
    range.addEventListener("input", () => sync(range, mirror, mirror.type === "text"));
    mirror.addEventListener("input", () => {
      const clean = (mirror.value || "").replace(/[^0-9-]/g, "");
      if (clean === "") return;
      range.value = clean;
      if (mirror.type === "text" && mirror.dataset.suffix) mirror.value = clean + mirror.dataset.suffix;
    });
  });

  // ---------- Chronosanity vs Boss Scaling: mutually exclusive ----------
  // cjot-beta's ForcedFlags map (randosettings.py:149) silently drops
  // boss-scale when chronosanity is set. Both stay first-class options
  // in the UI but only one can be active at once. Auto-clearing the
  // other when one is checked makes the constraint visible without
  // greying anything out.
  (function linkChronoBossScale() {
    const chrono = document.querySelector('input[name="chronosanity"]');
    const bscale = document.querySelector('input[name="boss-scaling"]');
    if (!chrono || !bscale) return;
    chrono.addEventListener("change", () => {
      if (chrono.checked && bscale.checked) bscale.checked = false;
    });
    bscale.addEventListener("change", () => {
      if (bscale.checked && chrono.checked) chrono.checked = false;
    });
  })();

  // ---------- Rocksanity forces Unlocked Skyways on ----------
  // cjot-beta's forced_on map (randosettings.py:175) silently forces
  // UNLOCKED_SKYGATES on whenever ROCKSANITY is set, since the rocks
  // need skyway access to be reachable. One-way relationship: turning
  // rocksanity off does NOT turn skyways off (user can keep skyways
  // independently). And toggling skyways off while rocksanity is on
  // is meaningless -- cjot-beta would force it back on -- so we
  // silently re-check it to keep the form consistent.
  (function linkRocksanitySkyways() {
    const rocks = document.querySelector('input[name="rocksanity"]');
    const sky = document.querySelector('input[name="unlocked-skyways"]');
    if (!rocks || !sky) return;
    rocks.addEventListener("change", () => {
      if (rocks.checked && !sky.checked) sky.checked = true;
    });
    sky.addEventListener("change", () => {
      if (!sky.checked && rocks.checked) sky.checked = true;
    });
  })();

  // ---------- Character rando chain: dual-techs -> dup-chars -> char-rando -> unlocked-magic ----------
  // Three cjot-beta behaviors layered into one cascade:
  //   1. forced_on map (randosettings.py:177): DUPLICATE_TECHS forces
  //      CHAR_RANDO + DUPLICATE_CHARS on -- duplicate dual techs only
  //      make sense when characters can be duplicated.
  //   2. forced_on map (randosettings.py:176): DUPLICATE_CHARS forces
  //      CHAR_RANDO on -- duplicate characters require char rando to
  //      reassign slots.
  //   3. cr_telepod_exhibit.flux (randomizer.py:1100): when CHAR_RANDO
  //      is on, the Telepod Exhibit script pre-unlocks Spekkio's magic
  //      flags at game start, so unlocked_magic is *effectively* on
  //      regardless of the user's setting. We mirror this in the UI
  //      so the form value matches the in-game reality.
  // All relationships are one-way force-on (like rocksanity->skyways):
  //   - Toggling dual-techs on -> dup-chars on -> rando on -> magic on
  //   - Toggling dup-chars on -> rando on -> magic on
  //   - Toggling rando on -> magic on
  //   - Disabling a parent does NOT disable children (user can keep
  //     rando + magic without dup-chars, etc.)
  //   - Trying to uncheck a forced-on flag silently re-checks it.
  (function linkCharRandoChain() {
    const dualtech = document.querySelector('input[name="duplicate-dual-techs"]');
    const dup = document.querySelector('input[name="duplicate-characters"]');
    const rando = document.querySelector('input[name="randomize-characters"]');
    const magic = document.querySelector('input[name="unlocked-magic"]');
    if (!dup || !rando || !magic) return;
    if (dualtech) {
      dualtech.addEventListener("change", () => {
        if (dualtech.checked) {
          // Cascade: enabling dual-techs forces dup-chars, rando, AND magic on.
          if (!dup.checked) dup.checked = true;
          if (!rando.checked) rando.checked = true;
          if (!magic.checked) magic.checked = true;
        }
      });
    }
    dup.addEventListener("change", () => {
      if (dup.checked) {
        // Cascade: enabling dup-chars forces both rando AND magic on.
        if (!rando.checked) rando.checked = true;
        if (!magic.checked) magic.checked = true;
      } else if (dualtech && dualtech.checked) {
        // Can't uncheck dup-chars while dual-techs is on.
        dup.checked = true;
      }
    });
    rando.addEventListener("change", () => {
      // Force magic on when rando is checked.
      if (rando.checked && !magic.checked) magic.checked = true;
      // Can't uncheck rando while dup-chars (or transitively dual-techs) is on.
      if (!rando.checked && dup.checked) rando.checked = true;
    });
    magic.addEventListener("change", () => {
      // Can't uncheck magic while rando (or transitively dup-chars / dual-techs) is on.
      if (!magic.checked && rando.checked) magic.checked = true;
    });
  })();

  // ---------- Tab min/max: keep min <= max within each pair ----------
  // The randomizer interprets reversed min/max as "min wins" and silently
  // truncates max, so a min=5 / max=2 pair becomes min=5 / max=5. Mirror
  // that constraint live so the form value matches what the seed will
  // actually use.
  (function linkTabRanges() {
    const pairs = [
      ["power-tab-min",  "power-tab-max"],
      ["magic-tab-min",  "magic-tab-max"],
      ["speed-tab-min",  "speed-tab-max"],
    ];
    pairs.forEach(([minName, maxName]) => {
      const minEl = document.querySelector(`input[name="${minName}"]`);
      const maxEl = document.querySelector(`input[name="${maxName}"]`);
      if (!minEl || !maxEl) return;
      const sync = (which) => {
        const lo = parseInt(minEl.value, 10);
        const hi = parseInt(maxEl.value, 10);
        if (isNaN(lo) || isNaN(hi)) return;
        if (lo > hi) {
          if (which === "min") {
            maxEl.value = String(lo);
            maxEl.dispatchEvent(new Event("input", {bubbles: false}));
          } else {
            minEl.value = String(hi);
            minEl.dispatchEvent(new Event("input", {bubbles: false}));
          }
        }
      };
      minEl.addEventListener("change", () => sync("min"));
      maxEl.addEventListener("change", () => sync("max"));
    });
  })();

  // ---------- Game mode: disable flags the mode forces off ----------
  // cjot-beta's ForcedFlags table (randosettings.py:148) silently turns
  // these off when the mode is selected. Mirror it in the UI so the
  // user can see what's effectively unavailable. We disable the
  // checkbox AND clear it when a forcing mode is active; restoring the
  // mode re-enables but does not auto-recheck.
  (function linkGameModeForcedOff() {
    const modeSel = document.querySelector('select[name="game-mode"]');
    if (!modeSel) return;

    const FORCED_OFF = {
      // Standard: nothing forced off.
      std: [],
      lw: [
        "boss-scaling", "bucket-list", "epoch-fail",
        "add-bekkler-spot", "add-cyrus-grave-spot", "add-ozzie-fort-spot",
        "add-race-log-spot", "add-sun-keep-spot", "restore-johnny-race",
        "split-arris-dome", "restore-tools", "unlocked-skyways",
        "vanilla-desert", "vanilla-robo-ribbon", "rocksanity",
        "remove-black-omen-spot",
      ],
      ia: [
        "zeal-2-last-boss", "boss-scaling", "bucket-list", "add-bekkler-spot",
      ],
      loc: [
        "zeal-2-last-boss", "bucket-list", "boss-scaling",
        "add-ozzie-fort-spot", "add-sun-keep-spot", "restore-tools",
        "restore-johnny-race", "split-arris-dome", "add-race-log-spot",
        "add-bekkler-spot",
      ],
      van: ["boss-scaling"],
    };

    const allNames = new Set();
    Object.values(FORCED_OFF).forEach((arr) => arr.forEach((n) => allNames.add(n)));

    const apply = () => {
      const forced = new Set(FORCED_OFF[modeSel.value] || []);
      allNames.forEach((name) => {
        const el = document.querySelector(`input[name="${name}"]`);
        if (!el) return;
        const wrap = el.closest("label");
        if (forced.has(name)) {
          if (el.checked) el.checked = false;
          el.disabled = true;
          if (wrap) wrap.classList.add("toggle-disabled");
        } else {
          el.disabled = false;
          if (wrap) wrap.classList.remove("toggle-disabled");
        }
      });
    };
    modeSel.addEventListener("change", apply);
    apply();
  })();

  // ---------- Bucket: keep "Number Required" <= "Number of Objectives" ----------
  // The two sliders are independent in the markup; the randomizer treats
  // needed > total as nonsense (it either errors or silently truncates).
  // Mirror the constraint live so the UI can't produce an invalid pair.
  (function linkBucketSliders() {
    const total    = document.querySelector('input[name="num-objectives"]');
    const needed   = document.querySelector('input[name="num-required"]');
    if (!total || !needed) return;
    const totalMirror  = document.querySelector('[data-mirror="num-objectives"]');
    const neededMirror = document.querySelector('[data-mirror="num-required"]');

    const clampNeeded = () => {
      const tv = parseInt(total.value, 10) || 1;
      // Cap the slider's upper bound at the current total. Min stays 1.
      needed.max = String(tv);
      if ((parseInt(needed.value, 10) || 1) > tv) {
        needed.value = String(tv);
        if (neededMirror) neededMirror.value = String(tv);
      }
    };

    total.addEventListener("input", clampNeeded);
    if (totalMirror) totalMirror.addEventListener("input", clampNeeded);
    needed.addEventListener("input", clampNeeded);
    if (neededMirror) neededMirror.addEventListener("input", clampNeeded);
    clampNeeded();
  })();

  // ---------- Mystery probability sliders (0..100 pct -> 0.0..1.0 hidden) ----------
  document.querySelectorAll("input[data-prob-pct]").forEach((range) => {
    const name = range.dataset.probPct;
    const hidden = document.querySelector(`input[name="${name}"]`);
    const label  = document.querySelector(`[data-mirror-prob="${name}"]`);
    const sync = () => {
      const pct = parseInt(range.value, 10) || 0;
      if (hidden) hidden.value = (pct / 100).toFixed(2);
      if (label)  label.value = pct + "%";
    };
    range.addEventListener("input", sync);
    if (label) {
      label.addEventListener("input", () => {
        const p = parseInt((label.value || "").replace(/[^0-9]/g, ""), 10);
        if (isNaN(p)) return;
        const clamped = Math.min(100, Math.max(0, p));
        range.value = clamped;
        sync();
      });
    }
  });

  // ---------- Character matrix helpers ----------
  const matrixBoxes = () => document.querySelectorAll(".char-matrix-box");
  const setMatrix = (checked) => matrixBoxes().forEach((b) => (b.checked = checked));
  const btnAll   = document.getElementById("matrix-check-all");
  const btnNone  = document.getElementById("matrix-uncheck-all");
  if (btnAll)  btnAll.addEventListener("click",  () => setMatrix(true));
  if (btnNone) btnNone.addEventListener("click", () => setMatrix(false));

  // ---------- Helpers to set form values from a preset ----------
  function setCheckbox(name, on) {
    const el = document.querySelector(`input[type="checkbox"][name="${name}"]`);
    if (el) el.checked = !!on;
  }
  function setSelect(name, value) {
    const el = document.querySelector(`select[name="${name}"]`);
    if (el) el.value = value;
  }
  function setText(name, value) {
    const el = document.querySelector(`input[name="${name}"]`);
    if (el) el.value = value;
  }
  function resetAll() {
    // Clear every checkbox toggle
    document.querySelectorAll(".toggle input[type=checkbox]").forEach((b) => (b.checked = false));
    // Restore the two default-on toggles from the base template
    setCheckbox("disable-glitches", true);
    setCheckbox("fast-tabs", true);
    // Defaults for selects
    setSelect("game-mode", "std");
    setSelect("enemy-difficulty", "normal");
    setSelect("item-difficulty", "normal");
    setSelect("shop-prices", "normal");
    setSelect("tech-randomization", "normal");
    // Tab sliders default to 1
    ["power-tab-min","power-tab-max","magic-tab-min","magic-tab-max","speed-tab-min","speed-tab-max"]
      .forEach((n) => setText(n, "1"));
    // Bucket
    setText("num-objectives", "5");
    setText("num-required", "5");
    for (let i = 1; i <= 8; i++) setText(`objective-${i}`, "");
    // Character matrix all on
    setMatrix(true);
    // Player name default
    setText("player-name", "Player1");
    // Re-sync mirror fields
    document.querySelectorAll('input[type="range"]').forEach((r) => r.dispatchEvent(new Event("input")));
  }

  // Apply a preset: reset first, then set the preset's values
  const PRESETS = {
    gato: () => {
      setSelect("game-mode", "std");
      setSelect("item-difficulty", "easy");
      setCheckbox("unlocked-magic", true);
      setCheckbox("free-menu-glitch", true);
      setCheckbox("fast-tabs", true);
      setCheckbox("disable-glitches", true);
    },
    prix: () => {
      setSelect("game-mode", "std");
      setSelect("item-difficulty", "normal");
      setCheckbox("unlocked-magic", false);
      setCheckbox("chronosanity", true);
      setCheckbox("fast-tabs", true);
    },
    jurassic: () => {
      setSelect("game-mode", "std");
      setSelect("item-difficulty", "normal");
      setCheckbox("unlocked-magic", false);
      setCheckbox("randomize-gear", true);
      setCheckbox("randomize-healing", true);
    },
    catalack: () => {
      setSelect("game-mode", "std");
      setSelect("item-difficulty", "hard");
      setCheckbox("randomize-gear", true);
      setCheckbox("randomize-healing", true);
      setCheckbox("unlocked-magic", false);
    },
    lw: () => {
      setSelect("game-mode", "lw");
      setSelect("item-difficulty", "normal");
      setCheckbox("unlocked-magic", true);
    },
    loc: () => {
      setSelect("game-mode", "loc");
      setSelect("item-difficulty", "normal");
      setCheckbox("unlocked-magic", true);
    },
  };
  document.querySelectorAll(".preset-card").forEach((card) => {
    card.addEventListener("click", () => {
      resetAll();
      const fn = PRESETS[card.dataset.preset];
      if (fn) fn();
    });
  });
  const resetBtn = document.getElementById("reset-all");
  if (resetBtn) resetBtn.addEventListener("click", resetAll);
})();
