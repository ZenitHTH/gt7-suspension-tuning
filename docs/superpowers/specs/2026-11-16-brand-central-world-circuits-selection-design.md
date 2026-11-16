# Brand Central & World Circuits Selection Design

**Date:** 2026-11-16
**Target App:** GT7 Suspension Tuner Desktop GUI (`PyQt6`)

## 1. Intent & Why

Currently, choosing a car or circuit in the tuner's left form (`SetupForm` in `gui/form.py`) requires typing into a filter box or scrolling through flat `QComboBox` lists containing 590 cars and 123 track layouts. Gran Turismo 7 players naturally navigate cars by **Brand Central** (`Continent -> Country-grouped Brand -> Car`) and tracks by **World Circuits** (`Continent -> Circuit -> Layout`).

Adding pop-out, text-only step-by-step picker dialogs that mirror GT7's navigation hierarchy—while keeping the existing search inputs and long dropdowns intact as a fast backup choice—gives users familiar visual-free button navigation without sacrificing quick typing or breaking existing GUI tests.

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- Add a **Brand Central…** button in the `Vehicle` group (`SetupForm`) that opens a modal step-by-step car picker:
  `Continent (Americas / Europe / Asia-Pacific)` → `Brands grouped by Country` → `Cars in Brand`.
- Add a **World Circuits…** button in the `Session` group (`SetupForm`) that opens a modal step-by-step circuit picker:
  `Continent (Americas / Europe / Asia-Oceania)` → `Circuits in Continent` → `Layouts of Circuit`.
- Keep the existing `car_search` + `car_combo` and `track_search` + `track_combo` (including `— (no track)`) on `SetupForm` as the backup choice, synced whenever a selection is confirmed in either pop-out dialog.
- Reach all 590 cars (including older Used/Legend Cars models) and all 123 layouts across all 42 base circuits.
- Normalize catalog anomalies so the region/country/brand lists match GT7:
  - Merge `Citroen` and `Citroën` under one `Citroën` brand in `France`.
  - Move `Gran Turismo` from `Others` into `Japan` (`Asia-Pacific`), matching in-game Brand Central.
  - Move `Bugatti` from `Germany` into `France` (`Europe`), matching in-game Brand Central.
  - Omit partner-only entries with zero cars (e.g., `Fanatec`, `Brembo`, `BBS`, `Sony AI`).
  - Backfill `country` on all tracks from `data/csv/course.csv` + `data/csv/country.csv`, and map `SUGO International Racing Course` (not present in `course.csv`) to `Japan` (`Asia-Oceania`).
- Match the app's existing dark-cockpit styling (`#1b1d23`, `#23262e`, `#14161a`, `#3a3f4d`, `#e5484d`, `#ffffff`).

### Non-Goals
- **No game imagery:** No world-map graphics, background photos, country flags, brand logos, or circuit map thumbnails—text buttons only.
- **No Used / Legend Car dealership split:** All cars appear under their Brand Central region, country, and manufacturer.
- **No solver / CLI / formatter changes:** `cli.py`, `setup.py`, `lib/`, and `sheet_formatter.py` remain unchanged.

### Anti-Goals
- Do not remove or break `car_search`, `car_combo`, `track_search`, `track_combo`, or `SetupForm.on_car_selected` behavior tested by `tests/test_gui_form.py` and `tests/test_gui_app.py`.
- Do not leave unmapped `"Others"` buckets or duplicate accented/unaccented brand buttons (`Citroen` vs `Citroën`) in the UI.
- Do not inflate `gui/theme.py`'s `QSS` string beyond the 70-line guard enforced by `tests/test_gui_smoke.py`.
- Do not violate `tests/test_import_hygiene.py` (all `typing` names used in annotations must be imported).

## 3. Constraints

- **Platform & GUI Stack:** PyQt6 (`PyQt6>=6.7,<7`), Python 3.12+ annotation hygiene (`tests/test_import_hygiene.py`), headless testability under `QT_QPA_PLATFORM=offscreen`.
- **Theme Guard:** `gui/theme.py` `QSS` must remain `<= 70` non-empty lines and preserve `#1b1d23`, `#14161a`, `#e5484d`, `monospace`, and `#ffffff` text. Dialog-specific button styles can live in a dedicated dialog helper/style constant or concise object-named rules without tripping the `gui/theme.py` line limit.
- **Clean Code Rules:** Modular separation between catalog indexing (`db/`) and UI widgets (`gui/`), files under 200 lines, small single-responsibility functions (under 20 lines), no boolean flag parameters, and shared navigation chrome rather than duplicating Brand Central and World Circuits dialog scaffolding.
- **Data Integrity:** Updating track metadata must never overwrite user-saved `slider_ranges` in `data/cars_master.json`.

## 4. Decided Behavior & User Flow

### 4.1 Main Form Integration (`gui/form.py`)
- **`Vehicle` group:** Keeps `car_search` and `car_combo` as the backup selector, plus a **Brand Central…** `QPushButton` positioned cleanly with the vehicle controls.
- **`Session` group:** Keeps `track_search` and `track_combo` (with `— (no track)` at index 0) as the backup selector, plus a **World Circuits…** `QPushButton`.
- **Bidirectional Sync:**
  - Confirming a car in Brand Central sets `car_search` to `''` only if the current filter text hides the chosen `car_id`, then selects `car_id` in `car_combo` so `on_car_selected(car_id)` prefills DB specs, swaps, and slider ranges identically to choosing from the dropdown.
  - Confirming a layout in World Circuits sets `track_search` to `''` only if the current filter text hides the chosen `track_id`, then selects `track_id` in `track_combo`.
  - Canceling/closing either dialog (`Esc` or window close) leaves the form's current car/track untouched.

### 4.2 Shared Pop-Out Dialog Navigation (Option A — Step-by-Step)
Both **Brand Central** and **World Circuits** open as modal `QDialog` windows (generously sized, e.g., ~780×560, resizable) using a `QStackedWidget` with three steps:
- **Top Header Bar:**
  - `← Back` button (disabled on Step 1; navigates one step back—or clears active search if currently viewing search results).
  - Clickable breadcrumb trail (e.g., `Brand Central › Asia-Pacific › Toyota` or `World Circuits › Europe › Nurburgring`), allowing one-click return to Step 1 or Step 2.
  - Live quick-search `QLineEdit` in the top-right to jump straight to matching cars or track layouts by text; clearing the search returns to the step the user was on.
- **Scrollable Step Body:** Each step lives inside a scroll area so large lists (e.g., Europe brands or Lago Maggiore's 12 layouts) never clip or force cramped buttons.

### 4.3 Brand Central Flow (Cars)
1. **Step 1 — Continent:** Three horizontal pill/card text buttons:
   - `Americas`
   - `Europe`
   - `Asia-Pacific`
2. **Step 2 — Brands Grouped by Country:**
   - Horizontal rows per country inside the selected continent, with the country name in a fixed-width left column (`Japan`, `Korea`, `China` / `United Kingdom`, `Germany`, `Italy`, `France`, etc.) and a multi-column grid of text brand buttons on the right.
   - Each brand button displays `Brand Name (N)` where `N` is the number of cars under that brand.
3. **Step 3 — Cars in Brand:**
   - Multi-column grid of text card-buttons for all cars in the chosen brand.
   - Each car button shows two lines of text:
     - Line 1 (primary): `short_name` (all 590 cars have `short_name`, avoiding redundant maker prefixes like `Nissan 180SX Type X '96` -> `180SX Type X '96`).
     - Line 2 (secondary): `Group · Drivetrain · {power} hp · {mass} kg` (appending `· PP {stock_pp}` when `stock_pp` is present).
   - Clicking a car button immediately accepts the dialog and selects that car in `SetupForm`.

### 4.4 World Circuits Flow (Tracks)
1. **Step 1 — Continent:** Three horizontal pill/card text buttons:
   - `Americas`
   - `Europe`
   - `Asia-Oceania`
2. **Step 2 — Circuits in Continent:**
   - Multi-column grid of circuit buttons (listed directly under the continent without country sub-headers, matching in-game World Circuits).
   - Each circuit button shows two lines of text:
     - Line 1 (primary): `base_circuit` (e.g., `Suzuka Circuit`, `Nurburgring`).
     - Line 2 (secondary): `{Country} · {N} layout(s)`.
3. **Step 3 — Layouts of Circuit:**
   - Button list/grid of every layout belonging to the chosen `base_circuit` (all circuits pass through Step 3—including single-layout circuits—so users confirm the exact layout and see its specs consistently).
   - Each layout button shows two lines of text:
     - Line 1 (primary): layout `name` (e.g., `Suzuka Circuit East Course`, `Nurburgring Nordschleife`).
     - Line 2 (secondary): `{length_km} km · {num_corners} turns` plus surface/rain/oval tags where relevant (e.g., `Rain`, `Oval`, `Dirt` / `Snow`).
   - Clicking a layout button immediately accepts the dialog and selects that layout in `SetupForm`.

### 4.5 Catalog Taxonomy & Data Enrichment
- **Brand Central Region Mapping (all 590 cars covered):**
  - `Americas`: `United States`
  - `Europe`: `United Kingdom`, `Germany`, `Italy`, `France` (with `Bugatti` normalized to `France`, and `Citroen` merged into `Citroën`), `Sweden`, `Austria`, `Czech Republic`
  - `Asia-Pacific`: `Japan` (with `Gran Turismo` normalized from `Others` to `Japan`), `Korea`, `China`
- **World Circuits Region Mapping (all 42 base circuits / 123 layouts covered):**
  - `Americas`: `United States`, `Canada`, `Brazil`
  - `Europe`: `United Kingdom`, `Germany`, `Italy`, `France`, `Spain`, `Belgium`, `Austria`, `Switzerland`, `Croatia`
  - `Asia-Oceania`: `Japan` (including `SUGO International Racing Course`), `Australia`, `UAE` (`Yas Marina Circuit`)
- **Track Country Source:** Update `scripts/build_database.py` (which currently reads `course.csv` and `country.csv` but omits `country` from `tracks_master.json`) and backfill `country` into `data/tracks_master.json`, while keeping runtime fallback mapping in the catalog query module so both CSV-derived and static lookups stay resilient.

## 5. What's Left to the Builder

- **Module & File Layout (Clean Code `< 200` lines/file):**
  - Catalog query/tree builder (e.g., `db/catalog.py`) + service methods on `TuningService` (`gui/service.py`) so Qt code never accesses raw JSON/CSV schemas directly.
  - Shared step-by-step picker dialog shell + Brand Central and World Circuits step builders (e.g., `gui/picker_dialog.py` + `gui/brand_central.py` / `gui/world_circuits.py` or a small `gui/pickers/` package).
- **Pre-selection / Highlighting Polish:** Optionally highlighting the currently active car's continent/brand/car or track's continent/circuit/layout when opening the dialog, or jumping directly to Step 1 every time.
- **Exact Layout Sizing, Column Counts, and Sorting:** Exact column counts (`2–4` columns), button padding, sort order of countries/brands/cars (e.g., alphabetical vs group/year), and keyboard shortcuts (`Esc` to close/go back).
- **Dialog Stylesheet Placement:** Keeping dialog button/pill/breadcrumb styles local to the picker module (using the exact `gui/theme.py` color tokens) so `gui/theme.py` stays well below its 70-line QSS cap.
