# GT7 Suspension Tuner — GUI

PyQt6 desktop GUI over the existing physics core: pick a car, enter your
in-game slider ranges and (optionally) measured G-forces, click **Compute
Setup**, and get the full suspension sheet with copy-to-clipboard. Compute
runs on a worker `QThread`, so the UI never blocks.

## Launch

```bash
./run_gui.sh
```

The launcher `cd`s to the project root, creates `.venv/` + installs
`PyQt6>=6.7,<7` if missing, then runs `.venv/bin/python -m gui`
(**Qt binding used: PyQt6 6.12.0**, Python 3.15 — the plan's PySide6
fallback was not needed, the wheel installs fine).

## Input tiers

| # | Tier | Example (MR2) | Source |
|---|------|---------------|--------|
| 1 | **Required** — car + in-game slider ranges | car 207; DF 50–200 / 120–310; height 90–160 / 90–160; fn 1.50–3.50 / 1.50–3.50 | You (car setup page) |
| 2 | **Auto-from-DB** — prefills everything else | mass 1270 kg, 241 hp, 304 Nm, 42:58 balance, tire SS | DB; any field overridable via "use DB" checkboxes |
| 3 | **Optional build overrides** | power 630, mass 1289, balance 42:58 | You |
| 4 | **Optional calibration/session** | G @ 60/120/240 = 1.04/1.19/1.38 + ref DF 200/310, solve `balanced`, tire SS, speed 240 | You (track session) |

A range pair left at `0/0` means "use saved/preseeded DB values"; G-force
calibration unlocks the Solve dropdown (the solver anchors to your tires).
**Save ranges to DB** merges the current form values into the car's saved
`slider_ranges` in `data/cars_master.json`, shadowing any preseeded values.

## MR2 worked example

1. Pick **Toyota MR2 GT-S '97** (car `207`) — DB info shows
   241 hp / 304 Nm / 42:58 / MR.
2. Select the **BYH-R8** swap → power/torque prefill (420 hp / 429.5 Nm).
3. Tutorial build: power **630**, mass **1289**, balance **42/58**.
4. Ranges: DF **50–200 / 120–310**, height **90–160 / 90–160**,
   fn **1.50–3.50 / 1.50–3.50**.
5. Calibration: G **1.04 / 1.19 / 1.38**, ref DF **200 / 310**,
   solve **balanced**, tire **SS**.
6. **Compute Setup** → sheet renders (with QUICK-TRIM); **Copy sheet**
   puts the raw sheet on the clipboard.

## Theme

Dark cockpit chrome + white "paper spec sheet" (Design Spec tokens in
`gui/theme.py`, token-guarded by `tests/test_gui_smoke.py`). Spin/combo
arrow glyphs come from tiny PNGs generated at start-up (OS temp dir,
`gt7-suspension-tuner/`): QSS cannot draw glyphs and Qt's QSS `url()`
rejects `data:` URIs. No design tokens changed in the polish pass.

## Troubleshooting

- **`externally-managed-environment` (PEP 668)** — never `pip install`
  into system Python; use the `.venv/` that `run_gui.sh` creates.
- **No display / CI** — `QT_QPA_PLATFORM=offscreen` builds the UI headless
  (what the test suite uses); also `GT7_GUI_AUTO_QUIT_MS=<ms>` auto-quits.
- **PyQt6 wheel fails on your Python** — plan-allowed fallback: PySide6
  6.12, same API, only the import prefix changes (`PyQt6` → `PySide6`)
  in `gui/*.py`.
