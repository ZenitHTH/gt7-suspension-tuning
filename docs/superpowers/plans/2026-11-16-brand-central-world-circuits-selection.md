# Brand Central & World Circuits Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add modal, text-only, step-by-step **Brand Central** (`Continent -> Country-grouped Brand -> Car`) and **World Circuits** (`Continent -> Circuit -> Layout`) picker dialogs to the PyQt6 GUI while preserving the existing search boxes and dropdowns as synced backup selectors.

**Architecture:** Extract pure-Python region/country/brand/circuit grouping and normalization into `db/catalog.py`, expose it through `TuningService` (`gui/service.py`), and share a reusable step-by-step modal chrome (`StepPickerDialog` in `gui/picker_dialog.py`) across `BrandCentralDialog` (`gui/brand_central.py`) and `WorldCircuitsDialog` (`gui/world_circuits.py`). `SetupForm` (`gui/form.py`) launches each dialog from a button next to the backup search/combo controls and syncs confirmed selections back into `car_combo` / `track_combo`.

**Tech Stack:** Python 3.15 (runtime) / Python 3.12+ (annotation-hygiene compliant), PyQt6 ≥ 6.7, stdlib `unittest`, `.venv/bin/python -m unittest`.

**Spec:** `docs/superpowers/specs/2026-11-16-brand-central-world-circuits-selection-design.md`

## Global Constraints

- Work and commit on a feature/`dev` branch; never push or merge directly to `main`.
- Keep all new files under 200 lines and all new functions/methods under 20 lines with shallow nesting (`<= 2` indent levels) and zero boolean flag parameters.
- All `.py` files must import every typing symbol (`Optional`, `List`, `Dict`, `Tuple`, `Set`, etc.) used in annotations (`tests/test_import_hygiene.py`).
- `gui/theme.py` `QSS` must remain `<= 70` non-empty lines and preserve `#1b1d23`, `#14161a`, `#e5484d`, `monospace`, and `#ffffff` (`tests/test_gui_smoke.py`). Keep picker-specific QSS inside `gui/picker_dialog.py` using the same hex palette.
- Zero game imagery (no photos, flags, maps, or logos) — pure text buttons only.
- Do not modify `cli.py`, `setup.py`, `lib/`, `sheet_formatter.py`, or `data/cars_master.json`.
- Keep backup `car_search` + `car_combo` and `track_search` + `track_combo` (`— (no track)` at index 0) working for all existing callers and tests.
- Every GUI test file sets `QT_QPA_PLATFORM=offscreen` before Qt imports and runs via `.venv/bin/python -m unittest`.

## Review Focus

- **Filtered backup search hides dialog-selected item:** If `car_search` is `"honda"` and the user picks Toyota MR2 (`207`) from Brand Central (or `track_search` is `"monza"` and user picks Suzuka from World Circuits), `SetupForm` clears the conflicting search filter before selecting the ID in the backup combo so selection never silently fails -> tested in Task 5.
- **Accented, misplaced, and missing-CSV catalog entries:** `Citroen` and `Citroën` merge into one `Citroën` button under `France`; `Gran Turismo` maps from `Others` to `Japan` (`Asia-Pacific`); `Bugatti` maps to `France` (`Europe`); zero-car partner brands never appear; `SUGO International Racing Course` maps to `Japan` (`Asia-Oceania`) even when `country` is absent from track JSON -> tested in Task 2.
- **Dialog cancel / Escape after drilling down:** Pressing `Esc` or closing either picker mid-navigation leaves `SetupForm`'s active car, overrides, ranges, swaps, and track untouched -> tested in Task 5.
- **Search inside dialog + Back / clear recovery:** Typing a query on Step 2 switches to search results, and clicking `← Back` or clearing the query restores Step 2 (not Step 1 or a blank stack); zero-match queries show a readable empty-state message -> tested in Task 3 and Task 4.
- **Missing optional telemetry & non-destructive track enrichment:** Cars with `stock_pp=None` omit `PP` instead of printing `PP None`, single-layout circuits still step into Screen 3 to show length/corners/tags, and backfilling track `country` preserves `2005 SUGO International Racing Course` and never overwrites `data/cars_master.json` -> tested in Task 1, Task 2, and Task 4.

## File Structure

| File | Responsibility |
|---|---|
| `scripts/build_database.py` | Emit `'country'` on track entries when building `tracks_master.json` |
| `data/tracks_master.json` | Backfill `'country'` on all 123 layouts (preserving SUGO and surface fields) |
| `db/catalog.py` | Pure-Python Brand Central & World Circuits grouping, normalizations, and search dataclasses |
| `gui/service.py` | Thin `TuningService` delegation methods over `db.catalog` |
| `gui/picker_dialog.py` | Shared dark-cockpit `StepPickerDialog` (`← Back`, clickable breadcrumb, live search, `QStackedWidget`, button factory, local QSS) |
| `gui/brand_central.py` | `BrandCentralDialog(StepPickerDialog)` — Continent → Country-grouped Brands → Cars |
| `gui/world_circuits.py` | `WorldCircuitsDialog(StepPickerDialog)` — Continent → Circuits → Layouts |
| `gui/form.py` | Add `Brand Central…` / `World Circuits…` buttons and synced `select_car_by_id` / `select_track_by_id` helpers |
| `tests/test_db_catalog.py` | Unit tests for `db/catalog.py` and `tracks_master.json` coverage |
| `tests/test_picker_dialogs.py` | Headless PyQt6 tests for `StepPickerDialog`, `BrandCentralDialog`, and `WorldCircuitsDialog` |
| `tests/test_gui_form.py` | Integration tests for `SetupForm` dialog buttons, sync, backup filter clearing, and cancel preservation |

---

### Task 1: Enrich Track Country Metadata Without Clobbering Manual Track/Car Data

**Files:**
- Modify: `scripts/build_database.py:505-524`
- Modify: `data/tracks_master.json` (additive `'country'` field on all 123 entries)
- Test: `tests/test_db_catalog.py`

**Interfaces:**
- Produces: `'country': str` populated on every track dict in `data/tracks_master.json` (using `data/csv/country.csv` names + `'Japan'` for `2005` `SUGO International Racing Course`), emitted by `scripts/build_database.py`.

- [ ] **Step 1: Write the failing test in `tests/test_db_catalog.py`**

```python
class TestTrackCountryData(unittest.TestCase):
    def test_all_tracks_have_non_empty_country_and_preserve_sugo(self):
        from db.interface import TRACKS_DB
        ids = {str(t.get('id')): t for t in TRACKS_DB}
        self.assertEqual(len(ids), 123)
        self.assertIn('2005', ids)
        self.assertEqual(ids['2005'].get('country'), 'Japan')
        self.assertEqual(ids['4'].get('country'), 'United States')
        self.assertEqual(ids['10'].get('country'), 'Japan')
        missing = [t['id'] for t in TRACKS_DB if not t.get('country')]
        self.assertEqual(missing, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_db_catalog.TestTrackCountryData -v`
Expected: FAIL (`missing` contains all 123 track IDs because `'country'` is not yet in `data/tracks_master.json`).

- [ ] **Step 3: Update `scripts/build_database.py` and backfill `data/tracks_master.json` in place**

In `scripts/build_database.py:505-520`, add `'country': country_csv.get(crs.get('Country', ''), 'Others')` to each `master_tracks` dict. Then run a one-shot Python update reading `data/csv/course.csv`, `data/csv/country.csv`, and `data/tracks_master.json` to add `'country'` to every existing entry in `data/tracks_master.json` (using `'Japan'` for track `'2005'` / `SUGO International Racing Course`), preserving all 123 records and existing `grip_modifier` / `bumpiness` / `downforce_demand` values. Do not modify `data/cars_master.json`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_db_catalog.TestTrackCountryData -v`
Expected: PASS (`OK`).

- [ ] **Step 5: Commit**

```bash
git checkout -b dev 2>/dev/null || git checkout dev
git add scripts/build_database.py data/tracks_master.json tests/test_db_catalog.py
git commit -m "data(tracks): add country field to tracks_master and builder"
```

---

### Task 2: Catalog Indexing, Normalization & Service Facade (`db/catalog.py` + `gui/service.py`)

**Files:**
- Create: `db/catalog.py`
- Modify: `gui/service.py:16-89`
- Test: `tests/test_db_catalog.py`

**Interfaces:**
- Consumes: `db.interface.CARS_DB`, `db.interface.TRACKS_DB`, `db.interface.norm_str`
- Produces in `db/catalog.py`:
  - `CAR_CONTINENTS: Tuple[str, ...] = ('Americas', 'Europe', 'Asia-Pacific')`
  - `TRACK_CONTINENTS: Tuple[str, ...] = ('Americas', 'Europe', 'Asia-Oceania')`
  - `@dataclass(frozen=True)` models: `BrandSummary(name, country, car_count)`, `CountryBrands(country, brands)`, `CarEntry(id, short_name, name, manufacturer, country, continent, group, drivetrain, power_hp, mass_kg, stock_pp)`, `CircuitSummary(base_circuit, country, continent, layout_count)`, `TrackLayoutEntry(id, name, base_circuit, country, continent, length_km, num_corners, rain_supported, is_oval, category)`
  - `brand_central_continent_counts(cars=None) -> Dict[str, Tuple[int, int]]` (returns `{continent: (brand_count, car_count)}`)
  - `list_brands_by_country(continent: str, cars=None) -> List[CountryBrands]`
  - `list_cars_in_brand(continent: str, brand: str, cars=None) -> List[CarEntry]`
  - `search_catalog_cars(query: str, cars=None) -> List[CarEntry]`
  - `world_circuit_continent_counts(tracks=None) -> Dict[str, Tuple[int, int]]` (returns `{continent: (circuit_count, layout_count)}`)
  - `list_circuits_in_continent(continent: str, tracks=None) -> List[CircuitSummary]`
  - `list_layouts_for_circuit(continent: str, base_circuit: str, tracks=None) -> List[TrackLayoutEntry]`
  - `search_catalog_tracks(query: str, tracks=None) -> List[TrackLayoutEntry]`
- Produces in `gui/service.py` (`TuningService`):
  - `brand_central_continents() -> Dict[str, Tuple[int, int]]`
  - `brands_by_country(continent: str) -> List[CountryBrands]`
  - `cars_in_brand(continent: str, brand: str) -> List[CarEntry]`
  - `search_catalog_cars(query: str) -> List[CarEntry]`
  - `world_circuit_continents() -> Dict[str, Tuple[int, int]]`
  - `circuits_in_continent(continent: str) -> List[CircuitSummary]`
  - `layouts_for_circuit(continent: str, base_circuit: str) -> List[TrackLayoutEntry]`
  - `search_catalog_tracks(query: str) -> List[TrackLayoutEntry]`

- [ ] **Step 1: Write failing tests in `tests/test_db_catalog.py`**

Add tests covering:
- `test_catalog_normalizations_and_complete_coverage`:
  - Total cars summed across `CAR_CONTINENTS` equals `len(CARS_DB)` (590) with zero unmapped continents.
  - `list_brands_by_country('Europe')`: `France` contains a single `Citroën` brand (combining `Citroen` + `Citroën`, count 6, including `3613`) and `Bugatti`; `Germany` does not contain `Bugatti`.
  - `list_brands_by_country('Asia-Pacific')`: `Japan` contains `Gran Turismo` (count 8) and `Super Formula (Dallara)`; partner names (`Fanatec`, `Brembo`, `BBS`, `Sony AI`) do not appear.
  - Total track layouts summed across `TRACK_CONTINENTS` equals `len(TRACKS_DB)` (123) across 42 `CircuitSummary` circuits.
  - `list_circuits_in_continent('Asia-Oceania')` includes `SUGO International Racing Course` (`Japan`), `Mount Panorama Circuit` (`Australia`), and `Yas Marina Circuit` (`UAE`), even when tested against synthetic track dicts missing `'country'`.
- `test_catalog_search_and_service_delegation`:
  - `TuningService().search_catalog_cars('mr2 gt-s')` returns `CarEntry` with `id == '207'` and `short_name == "MR2 GT-S '97"`.
  - `TuningService().search_catalog_tracks('suzuka')` returns both Suzuka layouts (`TrackLayoutEntry`).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_db_catalog -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'db.catalog'`.

- [ ] **Step 3: Implement `db/catalog.py` and delegate in `gui/service.py`**

Keep `db/catalog.py` under 200 lines and each helper under 20 lines:
- Define explicit normalization tables:
  - `_MAKER_ALIASES = {'Citroen': 'Citroën'}`
  - `_MAKER_COUNTRY_OVERRIDES = {'Gran Turismo': 'Japan', 'Bugatti': 'France'}`
  - `_CAR_COUNTRY_CONTINENT` mapping all car countries into `Americas` / `Europe` / `Asia-Pacific`.
  - `_BASE_CIRCUIT_COUNTRY_FALLBACKS = {'SUGO International Racing Course': 'Japan'}`
  - `_TRACK_COUNTRY_CONTINENT` mapping all track countries into `Americas` / `Europe` / `Asia-Oceania`.
- Keep deterministic ordering (`_CAR_COUNTRY_ORDER` inside each continent matching GT7 regions cleanly; brands sorted case-insensitively inside each country; cars sorted by `(short_name.lower(), id)`; circuits sorted by `(base_circuit.lower())`; layouts sorted preserving `TRACKS_DB` order or full layout first).
- Update `gui/service.py` with one-line delegation methods on `TuningService`.

- [ ] **Step 4: Run tests to verify pass**

Run: `.venv/bin/python -m unittest tests.test_db_catalog tests.test_gui_service tests.test_import_hygiene -v`
Expected: PASS (`OK`).

- [ ] **Step 5: Commit**

```bash
git add db/catalog.py gui/service.py tests/test_db_catalog.py
git commit -m "feat(db): add Brand Central and World Circuits catalog indexing"
```

---

### Task 3: Shared Step-by-Step Modal Picker Chrome (`gui/picker_dialog.py`)

**Files:**
- Create: `gui/picker_dialog.py`
- Test: `tests/test_picker_dialogs.py`

**Interfaces:**
- Consumes: `PyQt6.QtWidgets` / `PyQt6.QtCore`
- Produces in `gui/picker_dialog.py`:
  - `picker_stylesheet() -> str` (uses exact dark-cockpit hex tokens `#1b1d23`, `#23262e`, `#14161a`, `#3a3f4d`, `#e5484d`, `#ffffff`, `#9aa3b5`; keeps `gui/theme.py` untouched)
  - `clear_layout(layout: QLayout) -> None`
  - `make_picker_button(title: str, subtitle: str = '', object_name: str = 'pickerCard') -> QPushButton` (single button containing cleanly stacked `QLabel` title + optional muted subtitle, or clean 2-line button layout so text wraps/aligns cleanly without truncation)
  - `StepPickerDialog(QDialog)`:
    - `__init__(self, title: str, root_crumb: str, search_placeholder: str, parent: Optional[QWidget] = None)`
    - `set_breadcrumbs(self, segments: Sequence[Tuple[str, Callable[[], None]]]) -> None`
    - `show_step(self, step_index: int) -> None` (`0`, `1`, `2` for the 3 steps; clears active search view state and updates `back_btn.setEnabled(step_index > 0)`)
    - `step_container(self, step_index: int) -> QVBoxLayout` (scrollable content layouts for steps 1–3; step 0 is non-scrollable or centered container for the 3 continent pills)
    - Protected hooks overridden by subclasses: `_on_back(self) -> None`, `_on_search_changed(self, query: str) -> None`
    - `search_results_layout: QVBoxLayout` (index `3` on the `QStackedWidget`, shown whenever `search_edit.text().strip()` is non-empty; clearing `search_edit` restores `_active_step` and breadcrumbs!)

- [ ] **Step 1: Write failing tests in `tests/test_picker_dialogs.py` for `StepPickerDialog`**

Add tests on a minimal test subclass:
- `test_step_navigation_and_breadcrumbs`: opens on step `0` (`back_btn` disabled), `show_step(1)` enables `back_btn`, `show_step(2)` renders clickable breadcrumb buttons; clicking step-0 breadcrumb returns to step `0` and disables `back_btn`.
- `test_search_and_back_navigation_recovery`: on step `1`, typing `"test"` switches `stack.currentIndex()` to `3` (search page) and keeps `back_btn` enabled; clicking `back_btn` (or clearing `search_edit`) returns `stack.currentIndex()` to `1` (the exact step before searching) rather than `0`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_picker_dialogs -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gui.picker_dialog'`.

- [ ] **Step 3: Implement `gui/picker_dialog.py`**

Keep file under 200 lines and functions under 20 lines:
- Build the header (`back_btn`, `breadcrumb_layout`, `search_edit`) + `QStackedWidget` (`step 0`, scrollable `step 1`, scrollable `step 2`, scrollable `search`).
- Track `self._active_step: int = 0` separately from search state so typing/clearing search preserves the active step seamlessly; clicking `back_btn` clears `search_edit` first if search is non-empty, otherwise calls `self._on_back()`.
- Keep `make_picker_button` clean (e.g. a `QPushButton` with an internal `QVBoxLayout` containing `QLabel(title)` + optional `QLabel(subtitle)` with `WA_TransparentForMouseEvents` so the entire card highlights and clicks like one native `QPushButton`, supporting word wrap and clean alignment).

- [ ] **Step 4: Run tests to verify pass**

Run: `.venv/bin/python -m unittest tests.test_picker_dialogs tests.test_gui_smoke tests.test_import_hygiene -v`
Expected: PASS (`OK`, including `test_theme_qss_uses_design_tokens` checking `<= 70` lines in `gui/theme.py`).

- [ ] **Step 5: Commit**

```bash
git add gui/picker_dialog.py tests/test_picker_dialogs.py
git commit -m "feat(gui): add shared StepPickerDialog shell and card button helper"
```

---

### Task 4: Brand Central & World Circuits Dialogs (`gui/brand_central.py` & `gui/world_circuits.py`)

**Files:**
- Create: `gui/brand_central.py`
- Create: `gui/world_circuits.py`
- Test: `tests/test_picker_dialogs.py`

**Interfaces:**
- Consumes: `TuningService` methods from Task 2, `StepPickerDialog`, `clear_layout`, `make_picker_button` from Task 3
- Produces in `gui/brand_central.py`:
  - `format_car_subtitle(car: CarEntry) -> str` (omits `PP` cleanly when `car.stock_pp is None`)
  - `BrandCentralDialog(StepPickerDialog)`:
    - `__init__(self, service: TuningService, parent: Optional[QWidget] = None)`
    - `selected_car_id: Optional[str]` (set before calling `accept()`)
- Produces in `gui/world_circuits.py`:
  - `format_layout_subtitle(track: TrackLayoutEntry) -> str`
  - `WorldCircuitsDialog(StepPickerDialog)`:
    - `__init__(self, service: TuningService, parent: Optional[QWidget] = None)`
    - `selected_track_id: Optional[str]` (set before calling `accept()`)

- [ ] **Step 1: Write failing tests in `tests/test_picker_dialogs.py`**

Add tests:
- `test_brand_central_three_step_flow_and_accept`:
  - Step 0 renders exactly 3 continent buttons (`Americas`, `Europe`, `Asia-Pacific`).
  - Clicking `Asia-Pacific` moves to Step 1, displays country headers (`Japan`, `Korea`, `China`) alongside brand buttons (`Toyota (...)`, `Gran Turismo (...)`), and excludes partner-only labels (`Fanatec`, `Brembo`, `BBS`, `Sony AI`).
  - Clicking `Toyota` moves to Step 2 and lists `MR2 GT-S '97`; clicking `MR2 GT-S '97` sets `dialog.selected_car_id == '207'` and `dialog.result() == QDialog.DialogCode.Accepted`.
- `test_missing_pp_formatting_and_single_layout_step3`:
  - `format_car_subtitle` on car `'3604'` (or any `stock_pp=None` `CarEntry`) does not contain `'None'` or `'PP'`.
  - In `WorldCircuitsDialog`, clicking `Asia-Oceania` -> `Tsukuba Circuit` moves to Step 2 (layout confirmation screen) showing length/corners instead of skipping Step 2; clicking the `Tsukuba Circuit` layout sets `selected_track_id` and accepts.
- `test_world_circuits_search_empty_state_and_back`:
  - Typing `'zzzz_nonexistent'` renders an empty-state `QLabel` (`No matching tracks found`) without crashing; clearing restores the previous step.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_picker_dialogs -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gui.brand_central'`.

- [ ] **Step 3: Implement `gui/brand_central.py` and `gui/world_circuits.py`**

Keep each file `< 180` lines and each helper `< 20` lines:
- **`gui/brand_central.py` (`BrandCentralDialog`)**:
  - Step 0: 3 horizontal pill buttons (`Americas`, `Europe`, `Asia-Pacific`) with brand/car count subtitle (`N brands · M cars`).
  - Step 1: For each `CountryBrands`, one horizontal row (`QLabel(country)` fixed width ~110px on left + `QGridLayout` of `Brand (N)` buttons in 3 columns on right).
  - Step 2: 3-column grid of `CarEntry` card-buttons (`short_name` + `format_car_subtitle(car)`). Clicking emits selection (`selected_car_id = car.id; self.accept()`).
  - Search: matching `CarEntry` grid (capped or all matches cleanly scrollable) with `'No matching cars found'` label when empty.
- **`gui/world_circuits.py` (`WorldCircuitsDialog`)**:
  - Step 0: 3 horizontal pill buttons (`Americas`, `Europe`, `Asia-Oceania`) with `N circuits · M layouts`.
  - Step 1: 3-column grid of `CircuitSummary` buttons (`base_circuit` + `{country} · {layout_count} layout(s)`).
  - Step 2: 2-column grid of `TrackLayoutEntry` buttons (`name` + `format_layout_subtitle(track)` showing `{length_km} km · {num_corners} turns` and `Rain` / `Oval` / `Dirt` tags when applicable). Clicking sets `selected_track_id = track.id` and calls `self.accept()`.
  - Search: matching `TrackLayoutEntry` grid with `'No matching tracks found'` label when empty.

- [ ] **Step 4: Run tests to verify pass**

Run: `.venv/bin/python -m unittest tests.test_picker_dialogs tests.test_import_hygiene -v`
Expected: PASS (`OK`).

- [ ] **Step 5: Commit**

```bash
git add gui/brand_central.py gui/world_circuits.py tests/test_picker_dialogs.py
git commit -m "feat(gui): implement BrandCentralDialog and WorldCircuitsDialog"
```

---

### Task 5: Integrate Pickers into `SetupForm` & Sync Backup Controls (`gui/form.py`)

**Files:**
- Modify: `gui/form.py:167-190` (`_build_vehicle_group`), `gui/form.py:304-320` (`_build_session_group`), and add small helper methods for opening/syncing pickers
- Test: `tests/test_gui_form.py`

**Interfaces:**
- Consumes: `BrandCentralDialog`, `WorldCircuitsDialog`
- Produces on `SetupForm`:
  - `self.brand_central_btn: QPushButton` (`'Brand Central…'`)
  - `self.world_circuits_btn: QPushButton` (`'World Circuits…'`)
  - `select_car_by_id(self, car_id: str) -> bool`
  - `select_track_by_id(self, track_id: str) -> bool`

- [ ] **Step 1: Write failing tests in `tests/test_gui_form.py`**

Add tests:
- `test_picker_buttons_present_and_backup_combos_preserved`: `form.brand_central_btn.text()` is `'Brand Central…'`, `form.world_circuits_btn.text()` is `'World Circuits…'`, and `car_search`/`car_combo`/`track_search`/`track_combo` still exist and work.
- `test_dialog_selection_clears_conflicting_backup_filter`:
  - Set `form.car_search.setText('honda')` (so `'207'` is filtered out), then mock `BrandCentralDialog.exec` returning `QDialog.DialogCode.Accepted` with `selected_car_id = '207'` and trigger `form.brand_central_btn.click()`. Assert `form.car_search.text() == ''`, `form.car_combo.currentData() == '207'`, and `form.collect().car_id == '207'`.
  - Repeat for `form.track_search.setText('monza')` -> mock `WorldCircuitsDialog.exec` returning `Accepted` with `selected_track_id = '10'` (Suzuka) -> assert `form.track_search.text() == ''`, `form.track_combo.currentData() == '10'`, and `form.collect().track_id == '10'`.
- `test_dialog_cancel_preserves_existing_form_state`:
  - Select car `'207'` and track `'10'`; mock `BrandCentralDialog.exec` / `WorldCircuitsDialog.exec` returning `QDialog.DialogCode.Rejected` (even if `selected_car_id` is unset); click both buttons and assert `form.collect().car_id == '207'` and `form.collect().track_id == '10'`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_gui_form -v`
Expected: FAIL (`AttributeError: 'SetupForm' object has no attribute 'brand_central_btn'`).

- [ ] **Step 3: Wire `Brand Central…` / `World Circuits…` buttons and sync helpers in `gui/form.py`**

- In `_build_vehicle_group`: add a row or top button `self.brand_central_btn = QPushButton('Brand Central…')` connected to `self._on_open_brand_central` above/alongside the backup `car_search` + `car_combo` (clear label/hint like keeping `car_search` / `car_combo` directly below).
- In `_build_session_group`: add `self.world_circuits_btn = QPushButton('World Circuits…')` connected to `self._on_open_world_circuits` above the backup `track_search` + `track_combo`.
- Implement `select_car_by_id(self, car_id: str) -> bool`: if `self.car_combo.findData(car_id) < 0` and `self.car_search.text()`, clear `self.car_search.setText('')`; find `idx = self.car_combo.findData(car_id)`; if `idx >= 0`, `setCurrentIndex(idx)` and return `True` (also explicitly call `on_car_selected(car_id)` only if index did not change — or let `currentIndexChanged` handle changes cleanly).
- Implement `select_track_by_id(self, track_id: str) -> bool` symmetrically for `track_search` / `track_combo`.
- Implement `_on_open_brand_central` and `_on_open_world_circuits` (each `< 12` lines) calling `dialog.exec() == QDialog.DialogCode.Accepted`.

- [ ] **Step 4: Run full test suite & headless launch verification**

Run: `.venv/bin/python -m unittest discover -s tests -v`
Expected: ALL tests PASS (zero failures, zero skipped assertions, `test_gui_smoke` subprocess launch exits 0, `test_import_hygiene` passes).

- [ ] **Step 5: Commit**

```bash
git add gui/form.py tests/test_gui_form.py
git commit -m "feat(gui): wire Brand Central and World Circuits dialogs into SetupForm"
```

---

## Self-Review Checklist (Verified)

1. **Spec coverage:** Every section of `docs/superpowers/specs/2026-11-16-brand-central-world-circuits-selection-design.md` maps directly to a task: Track country backfill + SUGO (Task 1), Brand Central / World Circuits normalizations + Service (Task 2), Shared Step-by-Step Dialog + search/breadcrumb (Task 3), Brand Central + World Circuits UI pages & button formatting (Task 4), `SetupForm` integration + backup dropdown preservation + sync (Task 5).
2. **Step scan:** Every step specifies exact files, signatures, test names/assertions, and check commands without full implementation code transcripts.
3. **Type consistency:** `CarEntry`, `CountryBrands`, `CircuitSummary`, `TrackLayoutEntry`, `StepPickerDialog`, `BrandCentralDialog`, `WorldCircuitsDialog`, `selected_car_id`, `selected_track_id`, `select_car_by_id`, `select_track_by_id` match identically across Tasks 2–5.
4. **Review Focus:** All 5 failure modes in `Review Focus` have dedicated tests pinned in Tasks 1–5.
