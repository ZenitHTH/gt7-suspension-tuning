# Task 7 Report — Theme polish, launcher, docs, full-suite green

**Status:** DONE — commit `f055f33` (`gui: theme polish, launcher, docs, full suite green`).

## 1. Automated theme-check (Design Spec conformance)

Method: throwaway offscreen script (`/tmp/gt7_theme_check.py`, NOT committed). Built
`MainWindow(TuningService())` at 1400x900, selected car 207 (MR2 GT-S '97), set the
MR2 tutorial values (df 50–200/120–310, height 90–160 both, fn 1.5–3.5 both,
G 1.04/1.19/1.38, ref DF 200/310, solve balanced, power 630, mass 1289,
balance 42/58), called `_on_compute()`, spun `processEvents()` until the button
re-enabled (solve finished in ~0.2s; status `OK`; sheet contains MR2 + QUICK-TRIM),
then `win.grab()` → `/tmp/gt7_theme_check.png` and sampled pixels programmatically.

### Sampled results (final, post-fix)

| Region | Sampled | Design Spec | Verdict |
|---|---|---|---|
| Left pane (form side) | 89% dark, 8% white, 2% other over 12–380 x 60–700 | dark near `#1b1d23`/`#23262e` | PASS |
| Splitter | sizes `[400, 978]` | form side ~400px, sheet dominates | PASS |
| Right sheet | 90% white over 600–1350 x 100–700 | `#ffffff` sheet-bg | PASS |
| Right pane bottom bar | 99% dark | dark chrome (not light leak) | PASS |
| Compute button | `#e5484d` (center-right), `#ed7d81`/`#f4b1b4` (text AA) | accent `#e5484d` | PASS |
| Status bar | `#1b1d23` | bg-window | PASS |
| Input fields (df_f min, car search, tire combo) | `#14161a` | bg-field | PASS |
| Combo text / placeholder | light `#e6e8ee`-ish / `#55575c` | text-primary / secondary | PASS (readable) |
| Spinbox up/down arrows (pre-fix) | `#070709`/`#17191e` on `#14161a` | visible affordance | **FAIL → FIXED** |
| Spinbox up/down arrows (post-fix) | `#e6e8ee` glyphs on `#1b1d23` button | text-primary glyphs | PASS |
| Group-box / window bg | `#1b1d23` behind groups | bg-window | PASS |
| Checked checkbox indicator | `#e5484d` | accent | PASS |

Typography (13px UI, bold group titles, 12.5px monospace sheet, 12px status) and
focus ring (2px `#e5484d`), disabled 50% opacity, amber `#ffb454` bold warnings
label — all present in QSS (token-guarded by `tests/test_gui_smoke.py`); QSS is
37 non-empty lines (limit 70).

### QSS gap found + fix (theme.py only, NO token changes)

**Gap:** default platform style draws QSpinBox up/down (and QComboBox down) arrows
near-black on the dark `bg-field` → invisible (sampled `#070709` on `#14161a`).

**Fix (in `gui/theme.py`):**
- Generate two 14x14 RGBA PNG triangles (`text-primary` `#e6e8ee`, transparent
  bg) at start-up with stdlib only (`struct`+`zlib`), idempotently written to the
  OS temp dir `gt7-suspension-tuner/`.
- QSS now styles `QSpinBox/QDoubleSpinBox ::up-button`/`::down-button` (18px,
  `border` divider, `bg-window` backdrop), `::line-edit` (`bg-field`), and
  `::up-arrow`/`::down-arrow` + `QComboBox::down-arrow` with `image: url(...)`,
  substituting the PNG paths at `apply()` time via `__ARROW_UP__`/`__ARROW_DOWN__`
  placeholders (token literals stay in `QSS` for the smoke guard).
- Why file paths: Qt QSS `url()` does not accept `data:` URIs (tested), and
  PyQt6's `qRegisterResourceData` cannot register raw bytes (tested, all arg
  orders return False). Recorded in `docs/GUI.md` (Theme section).

No other QSS gaps found. No Design Spec token changed; the arrow-glyph mechanism
is noted in `docs/GUI.md` per the brief. Deferred minors (a) no try/except around
`collect()`/Worker, (b) e2e timing print, (c) no closeEvent/thread-stop —
intentionally untouched (out of polish scope).

## 2. Deliverables created

- **`run_gui.sh`** (executable, 100755) — verbatim from the brief: `cd` to its
dir, create `.venv` + `pip install --upgrade pip 'PyQt6>=6.7,<7'` if missing,
`exec .venv/bin/python -m gui`. Verified: `GT7_GUI_AUTO_QUIT_MS=500
QT_QPA_PLATFORM=offscreen ./run_gui.sh` → exit 0.
- **`docs/GUI.md`** (exactly 60 lines) — what it is; `./run_gui.sh` launch;
4-input-tier table (required / auto-from-DB / build overrides / calibration+session)
with MR2 values; MR2 worked example (car 207, BYH-R8, tutorial values, expected
241 hp / 42:58 / MR, QUICK-TRIM, copy); **Qt binding: PyQt6 6.12.0** (Python 3.15,
PySide6 fallback not needed); troubleshooting (PEP 668/venv, offscreen +
`GT7_GUI_AUTO_QUIT_MS`, PySide6 fallback note, temp-dir arrows).

## 3. Full suite

```
$ QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
... (full log at /tmp/gt7_suite.log)

----------------------------------------------------------------------
Ran 116 tests in 1.748s

OK
  [e2e] solve finished in 0.1s
```

116 tests, exit 0, no skips/errors — 13 tracked modules + untracked
`test_grip.py` (14 modules). Pre-existing GUI smoke guards (token literals,
QSS ≤ 70 lines, offscreen launch) all pass with the modified `theme.py`.
The `[e2e]` timing print is the known deferred minor (b) — left as-is.

## 4. Files changed (commit f055f33)

| File | Change |
|---|---|
| `run_gui.sh` | new (launcher, executable) |
| `docs/GUI.md` | new (60 lines) |
| `gui/theme.py` | arrow-glyph PNG generation + subcontrol QSS rules + `apply()` substitution (+66/-2) |

Untracked throwaway artifacts (NOT committed): `/tmp/gt7_theme_check.py`,
`/tmp/gt7_theme_check.png`, `/tmp/gt7_suite.log`, OS temp dir
gt7-suspension-tuner/arrow_*.png, other `/tmp` probe scripts. Unrelated dirty
files (pycache, .DS_Store, lib/grip.py, tests/test_grip.py, lib/__init__.py,
plan/progress edits) untouched.

## 5. Rulings

1. **Arrow-glyph mechanism** — chose temp-file PNGs over (a) `data:` URIs
(unsupported by Qt QSS) and (b) `qRegisterResourceData` (PyQt6 binding
rejects raw-byte registration); keeps the fix fully inside `gui/theme.py`,
respecting the commit-scope constraint (no new repo files).
2. **No QPalette override** — testing showed a custom app palette makes the
platform style ignore QSS backgrounds on spinbox line-edits (native light
`#dee0e6` leaked in); kept the default palette and fixed only what was broken
(arrows). Verified line-edit field bg stayed `#14161a` in the full app.
3. **Combo arrows** also given explicit glyph images for desktop
style-independence (offscreen probe showed a visible white native arrow, but
desktop QMacStyle is not verifiable here; the explicit image is deterministic).
4. Solve completes in ~0.2s in this environment (e2e test's "tens of seconds"
comment is stale) — no action taken (out of scope).

## 6. Self-review findings

- `run_gui.sh` matches the brief script byte-for-byte; `chmod +x` confirmed.
- `docs/GUI.md` = 60 lines (`wc -l`), all brief bullet points covered.
- `gui/theme.py`: all Design Spec tokens intact; smoke-test literals
(`#1b1d23`, `#e5484d`, `monospace`) present in `QSS`; 37 QSS lines ≤ 70.
- Commit contains exactly the 3 in-scope paths (`git show --stat` verified);
plan/ledger/report docs not committed.
- Suite run after the theme change: 116/116 OK.
- Residual risk: pixel checks ran offscreen (generic style); on the desktop
QMacStyle the arrow PNGs and all QSS backgrounds should render identically
(QSS-driven), but native-style compositing cannot be verified here — covered
by the manual smoke below.

## 7. User-facing manual smoke checklist (desktop)

1. `./run_gui.sh` → window titled **GT7 Suspension Tuner** (dark chrome, white
   sheet pane dominates; form side ~400px).
2. Pick **Toyota MR2 GT-S '97** → DB info label shows **241 hp / 42:58 / MR**
   (plus mass 1270 kg, 304 Nm, 3S-GTE).
3. Select the **BYH-R8** swap → power/torque **prefill 420** hp (429.5 Nm).
4. Enter the tutorial values: power 630, mass 1289, balance 42/58;
   ranges DF 50–200/120–310, height 90–160/90–160, fn 1.50–3.50/1.50–3.50;
   G 1.04/1.19/1.38, ref DF 200/310; tire SS; solve **balanced**.
5. **Compute Setup** → button disables during solve, sheet renders with
   QUICK-TRIM; status turns green `OK` (or amber if warnings).
6. **Copy sheet** → clipboard holds the full raw sheet.
Also glance at: spin/combo arrows visible (light triangles), focus ring red on
any input, scroll the form — ranges/calibration panels below the fold.
