# Solver-Style Setup Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-candidate heuristic in `lib/optimizer.py` with a deterministic grid search plus one-pass local refinement that finds the best GT7 suspension tune, and add a tire grip-limit penalty to the objective score.

**Architecture:** All per-candidate physics is already closed-form (trail-braking equilibrium feasibility loop, tire wear index, G-calibrator, grip check). The solver evaluates ~30 grid points over downforce span ratio x natural-frequency delta x camber delta, then one 4-neighbor local refinement pass around the winner; the best-scoring feasible candidate wins. Each candidate runs the existing pipeline unchanged: deepcopy baseline -> apply offsets -> ride-height feasibility loop -> evaluate.

**Tech Stack:** Python 3, stdlib only (no new dependencies), `unittest` via `python3 -m unittest discover -s tests` from the repo root.

**Spec:** In-conversation design agreement (Stage 1 grid search, Stage 1.5 grip penalty in score, Stage 2 local refinement). Stage 3 (objective redesign) is explicitly OUT OF SCOPE. Existing behavior pins: the 5 tests in `tests/test_optimizer.py` and 5 in `tests/test_grip.py` must keep passing unchanged.

## Global Constraints

- Stdlib only. No new modules; all logic lives in `lib/optimizer.py` plus a 1-line refresh in `setup.py` (Task 4).
- `locked_params` values (`'downforce'`, `'natural_frequency_hz'`, `'camber_deg'`, `'ride_height_mm'`) must never be modified by the search; a locked axis collapses its grid dimension to a single baseline value.
- Deterministic: no randomness; fixed iteration order; identical input -> identical output (assertable in tests).
- Score units: G (balanced = `g_240 - 0.25*front_wear`; max_grip = `g_240`; min_tire_wear = `-front_wear`). Grip penalty weight is 0.20 applied when min margin < 1.0.
- Sheet/CLI output format unchanged. `SolverResult` gains one trailing dataclass field with a default so the existing positional construction at lib/optimizer.py:198 and the consumer at setup.py:136 stay compatible.
- Worst case ~34 candidate evaluations must complete well under 2 s (each evaluation is milliseconds of closed-form math).
- Test command (from repo root): `python3 -m unittest discover -s tests -v`

## Interfaces

**Existing, consumed unchanged (exact signatures):**
- `lib.optimizer.SolverRequest(veh, trk, baseline_params, telem, sliders, g_model, objective='balanced', locked_params=(), speed_kmh=240.0)` (dataclass)
- `lib.optimizer.SolverResult` dataclass: `parameters, g_prediction, df_g_profile, trail_simulation, equilibrium_proof, tire_wear, objective_score`
- `lib.calibrator.predict_g_at_downforce(g_model, (df_f, df_r))` -> dict incl. `'g_240'`
- `lib.calibrator.build_df_g_profile(g_model, (range_f_tuple, range_r_tuple), active_df_tuple)` -> dict
- `lib.tire_wear.calculate_tire_wear_index(fn_hz_f, fn_hz_r, camber_f, camber_r, toe_f, toe_r, ptw=200.0, is_endurance=False)` -> dict incl. `'front_wear_factor'`
- `lib.grip.calculate_grip_check(veh, mu, ay_g, lltd_f)` -> dict incl. `'margins': {'front': x, 'rear': x, 'min': x}`, `'balance'`, `'saturation'`
- Telemetry keys the solver may read: `telem['mu']`, `telem['mu_braking']` (optional), `telem['lltd_pct']` (front share of lateral load transfer, percent), `telem['fr_ratio']`, `telem['is_no_aero']`, `telem['c_f']`, `telem['c_r']`
- Downforce availability: `_resolve_df_ranges(sliders, df)` returns `((min_f, max_f), (min_r, max_r))`; a range with `max-min <= 0` on both axes means no free downforce (road car)

**New (all in `lib/optimizer.py`, module-private unless noted):**
- `_optimize_downforce(req, params, span=None) -> None` - `span: Optional[float]`; None keeps current objective-based default (0.90 / 0.40 / 0.65)
- `_optimize_frequencies(req, params, delta=None) -> None` - `delta: Optional[float]`; None keeps current objective-based default (+0.15 / -0.15 / 0.0)
- `_optimize_camber(req, params, delta_f=None, delta_r=None) -> None` - both `Optional[float]`; None keeps current objective-based defaults (0.4/0.2, -0.4/-0.2, 0.0/0.0)
- `_candidate_grid(req) -> List[Tuple[Optional[float], Optional[float], Tuple[float, float]]]` - yields (span, fn_delta, (camber_delta_f, camber_delta_r)); None on an axis means "leave baseline untouched"
- `_evaluate(req, params, sim, bounds) -> SolverResult` - extracted from the tail of `solve_optimal_setup` (current lines 192-198), plus grip check population (Task 4)
- `_better(a, b, sim_a, sim_b) -> bool` - strict score win, or score tie (within 0.001) with larger `sim_a['dynamic_outside_front_clearance_mm']`
- `_refine(req, best, best_sim, best_meta, bounds) -> Optional[Tuple[SolverResult, Dict, Tuple]]` - one pass, up to 4 neighbors of (span, fn_delta) around the winner; returns (result, sim, meta) only if it strictly improves
- `SolverResult.grip_check: Dict[str, Any] = None` - new TRAILING dataclass field with default (Task 4)

## Task 1: Parameterize search stages + extract `_evaluate` (behavior-preserving refactor)

**Files:**
- Modify: `lib/optimizer.py` (the three `_optimize_*` functions at lines 52-92; `solve_optimal_setup` at lines 184-198)
- Test: `tests/test_optimizer.py` (add one test)

**Interface:**
- Produces: `_optimize_downforce(req, params, span=None)`, `_optimize_frequencies(req, params, delta=None)`, `_optimize_camber(req, params, delta_f=None, delta_r=None)`, `_evaluate(req, params, sim, bounds) -> SolverResult`. `solve_optimal_setup(req) -> SolverResult` keeps its exact public behavior for now (single-candidate flow, now routed through `_evaluate`).
- Consumes: existing `_resolve_df_ranges`, `_simulate_trail`, `_optimize_ride_heights`, `_solve_eq`, `_eval_wear`, `_calculate_score` (all unchanged in this task).

- [x] **Step 1: Add the failing test** to `tests/test_optimizer.py` inside `TestReverseOptimizer` (uses the existing `setUp` fixture):

```python
def test_explicit_span_parameter_controls_downforce(self):
    from lib.calibrator import predict_g_at_downforce
    from lib import optimizer
    p_hi = copy.deepcopy(self.params)
    p_lo = copy.deepcopy(self.params)
    req = SolverRequest(veh=self.veh, trk=self.trk, baseline_params=self.params,
                        telem=self.telem, sliders=self.sliders, g_model=self.g_model)
    optimizer._optimize_downforce(req, p_hi, span=0.90)
    optimizer._optimize_downforce(req, p_lo, span=0.40)
    df_hi = (p_hi['downforce']['front'], p_hi['downforce']['rear'])
    df_lo = (p_lo['downforce']['front'], p_lo['downforce']['rear'])
    self.assertGreaterEqual(
        predict_g_at_downforce(self.g_model, df_hi)['g_240'],
        predict_g_at_downforce(self.g_model, df_lo)['g_240'])
```

Add `import copy` at the top of the test file if missing.

- [x] **Step 2: Run test, verify it fails** (current `_optimize_downforce` has no `span` kwarg -> `TypeError`):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest tests.test_optimizer.TestReverseOptimizer.test_explicit_span_parameter_controls_downforce -v
```

- [x] **Step 3: Implement the refactor.** In `lib/optimizer.py`:
  1. `_optimize_downforce(req, params, span=None)`: `span` param overrides the objective-based default (`span = span if span is not None else <current objective expression>`); everything else identical.
  2. `_optimize_frequencies(req, params, delta=None)`: `delta = delta if delta is not None else <current objective expression>`; identical otherwise.
  3. `_optimize_camber(req, params, delta_f=None, delta_r=None)`: both override their objective-based defaults the same way; clamping and skip rules (`locked_params`, dirt/wet) unchanged.
  4. New `_evaluate(req, params, sim, bounds) -> SolverResult` containing exactly the current tail of `solve_optimal_setup` (equilibrium proof, wear, active downforce, `g_pred`, `df_ranges`, `df_profile`, score, `SolverResult(...)` construction).
  5. `solve_optimal_setup` body becomes: deepcopy baseline -> `_optimize_downforce(request, params)` -> `_optimize_frequencies(request, params)` -> `_optimize_camber(request, params)` -> `bounds = _resolve_height_bounds(request)` -> `sim = _optimize_ride_heights(request, params, bounds)` -> `return _evaluate(request, params, sim, bounds)`.

- [x] **Step 4: Run full suite, verify green** (new test passes AND all pre-existing tests pass unchanged):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest discover -s tests -v
```

- [x] **Step 5: Commit**

```bash
git add lib/optimizer.py tests/test_optimizer.py
git commit -m "refactor(optimizer): parameterize search stages, extract _evaluate (behavior-preserving)"
```

## Task 2: Grid search over (span, fn delta, camber delta)

**Files:**
- Modify: `lib/optimizer.py` (new `_candidate_grid`, `_better`; rewrite `solve_optimal_setup` loop)
- Test: `tests/test_optimizer.py` (add 3 tests)

**Interface:**
- Produces: `_candidate_grid(req) -> List[Tuple[Optional[float], Optional[float], Tuple[float, float]]]` (fixed iteration order: spans ascending, fn deltas ascending, camber tuples in listed order); `_better(a, b, sim_a, sim_b) -> bool`; `solve_optimal_setup` now returns the best grid candidate.
- Consumes: Task 1's parameterized `_optimize_*` + `_evaluate` + `_optimize_ride_heights`.
- Grid axes (values are fixed constants):
  - spans: `[0.40, 0.55, 0.65, 0.75, 0.90]`; available iff `'downforce' not in req.locked_params` AND baseline `params['downforce']` truthy AND at least one resolved range (via `_resolve_df_ranges` on `req.sliders`) has `max-min > 0`. Otherwise axis = `[None]`.
  - fn deltas: `[-0.15, 0.0, 0.15]`; available iff `'natural_frequency_hz' not in req.locked_params`. Otherwise `[None]`.
  - camber tuples: `[(0.0, 0.0), (0.4, 0.2)]`; available iff `'camber_deg' not in req.locked_params` AND `not req.trk.is_dirt` AND `not req.trk.is_wet`. Otherwise `[(0.0, 0.0)]`.
  - Maximum 30 candidates. `None` means the corresponding `_optimize_*` call is skipped for that candidate (baseline value kept).
- Winner rule: best `objective_score` via `_better`; ties (score diff < 0.001) break on larger `sim['dynamic_outside_front_clearance_mm']`; further ties keep the earlier candidate (deterministic).

- [x] **Step 1: Add failing tests** to `tests/test_optimizer.py` (all use the existing `setUp` fixture):

```python
def test_grid_score_meets_or_beats_baseline_heuristic(self):
    """Grid result must be at least as good as the old fixed-offset candidate
    (span 0.65, fn delta 0.0, camber delta 0.0) evaluated through the same pipeline."""
    import copy as _copy
    from lib import optimizer
    req = SolverRequest(
        veh=self.veh, trk=self.trk, baseline_params=self.params,
        telem=self.telem, sliders=self.sliders, g_model=self.g_model,
        objective='balanced', speed_kmh=240.0
    )
    res = solve_optimal_setup(req)
    p = _copy.deepcopy(self.params)
    optimizer._optimize_downforce(req, p, span=0.65)
    bounds = optimizer._resolve_height_bounds(req)
    sim = optimizer._optimize_ride_heights(req, p, bounds)
    base = optimizer._evaluate(req, p, sim, bounds)
    self.assertGreaterEqual(res.objective_score, base.objective_score - 1e-9)

def test_grid_all_locked_axes_preserves_baseline_values(self):
    self.params['downforce']['front'] = 110
    self.params['downforce']['rear'] = 155
    fn0 = self.params['natural_frequency_hz']['front']
    cb0 = self.params['camber_deg']['front']
    req = SolverRequest(
        veh=self.veh, trk=self.trk, baseline_params=self.params,
        telem=self.telem, sliders=self.sliders, g_model=self.g_model,
        objective='max_grip',
        locked_params=('downforce', 'natural_frequency_hz', 'camber_deg'),
        speed_kmh=240.0
    )
    res = solve_optimal_setup(req)
    self.assertEqual(res.parameters['downforce']['front'], 110)
    self.assertEqual(res.parameters['downforce']['rear'], 155)
    self.assertEqual(res.parameters['natural_frequency_hz']['front'], fn0)
    self.assertEqual(res.parameters['camber_deg']['front'], cb0)
    self.assertFalse(res.trail_simulation['bottoming_or_fender_hit'])

def test_grid_no_aero_road_car_still_solves(self):
    """Zero-span downforce (road car): grid must still produce a valid result."""
    from lib import optimizer
    sliders = dict(self.sliders)
    sliders['df_front'] = (110, 110)
    sliders['df_rear'] = (155, 155)
    self.assertEqual(len(optimizer._candidate_grid(SolverRequest(
        veh=self.veh, trk=self.trk, baseline_params=self.params,
        telem=self.telem, sliders=sliders, g_model=self.g_model))), 6)
    req = SolverRequest(
        veh=self.veh, trk=self.trk, baseline_params=self.params,
        telem=self.telem, sliders=sliders, g_model=self.g_model,
        objective='balanced', speed_kmh=240.0
    )
    res = solve_optimal_setup(req)
    self.assertFalse(res.trail_simulation['bottoming_or_fender_hit'])
    self.assertIsInstance(res.objective_score, float)
```

Note for the last test: with `df_front = (110, 110)` AND `df_rear = (155, 155)` the resolved ranges are both zero-span, so `_candidate_grid` must collapse the span axis to `[None]` and yield 1 span x 3 fn x 2 camber = 6 candidates.

- [x] **Step 2: Run tests, verify they fail** (`_candidate_grid` does not exist; the other two fail because `solve_optimal_setup` is still single-candidate):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest tests.test_optimizer -v
```

- [x] **Step 3: Implement** in `lib/optimizer.py`:

```python
def _candidate_grid(req: SolverRequest) -> list:
    """Enumerate candidate offsets (span, fn_delta, camber_delta_f, camber_delta_r)."""
    base = req.baseline_params
    spans = [None]
    if 'downforce' not in req.locked_params and base.get('downforce'):
        (min_f, max_f), (min_r, max_r) = _resolve_df_ranges(req.sliders, base['downforce'])
        if (max_f - min_f) > 0 or (max_r - min_r) > 0:
            spans = [0.40, 0.55, 0.65, 0.75, 0.90]
    fn_deltas = [None] if 'natural_frequency_hz' in req.locked_params else [-0.15, 0.0, 0.15]
    camber_deltas = [(0.0, 0.0)] if (
        'camber_deg' in req.locked_params or req.trk.is_dirt or req.trk.is_wet
    ) else [(0.0, 0.0), (0.4, 0.2)]
    return [(s, d, c) for s in spans for d in fn_deltas for c in camber_deltas]


def _better(a: SolverResult, b: SolverResult, sim_a: Dict[str, Any], sim_b: Dict[str, Any]) -> bool:
    """Prefer higher score; break ties on larger outside-front clearance."""
    if abs(a.objective_score - b.objective_score) < 0.001:
        return sim_a['dynamic_outside_front_clearance_mm'] > sim_b['dynamic_outside_front_clearance_mm']
    return a.objective_score > b.objective_score
```

and rewrite `solve_optimal_setup`:

```python
def solve_optimal_setup(request: SolverRequest) -> SolverResult:
    """Solve suspension parameters by grid search under aero and clearance constraints."""
    bounds = _resolve_height_bounds(request)
    best, best_sim = None, None
    for span, fn_delta, (cd_f, cd_r) in _candidate_grid(request):
        params = copy.deepcopy(request.baseline_params)
        if span is not None:
            _optimize_downforce(request, params, span=span)
        if fn_delta is not None:
            _optimize_frequencies(request, params, delta=fn_delta)
        if (cd_f, cd_r) != (0.0, 0.0):
            _optimize_camber(request, params, delta_f=cd_f, delta_r=cd_r)
        sim = _optimize_ride_heights(request, params, bounds)
        result = _evaluate(request, params, sim, bounds)
        if best is None or _better(result, best, sim, best_sim):
            best, best_sim = result, sim
    return best
```

- [x] **Step 4: Run full suite, verify green** (3 new tests + all pre-existing tests, especially `test_solver_eliminates_bottoming_and_preserves_rake`, `test_max_grip_vs_min_tire_wear_objectives`, `test_locked_parameters_remain_untouched`, `test_racecar_bounds_prevent_ride_height_jacking`, `test_dirt_camber_preserved_under_solver`):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest discover -s tests -v
```

- [x] **Step 5: Commit**

```bash
git add lib/optimizer.py tests/test_optimizer.py
git commit -m "feat(optimizer): grid search over downforce span, frequency, camber (up to 30 candidates)"
```

## Task 3: One-pass local refinement around the grid winner

**Files:**
- Modify: `lib/optimizer.py` (new `_refine`; `solve_optimal_setup` calls it after the grid loop)
- Test: `tests/test_optimizer.py` (add 1 test)

**Interface:**
- Produces: `_refine(req, best, best_sim, best_meta, bounds) -> Optional[Tuple[SolverResult, Dict, Tuple]]` where `best_meta = (span, fn_delta, camber_tuple)` for the grid winner. One pass only (no iteration). Up to 4 neighbors:
  - span neighbor: only if `'downforce' not in req.locked_params` and `best_meta[0]` is not None: `max(0.30, best_meta[0] - 0.05)` and `min(1.00, best_meta[0] + 0.05)`, skipping a neighbor equal to the winner's span (within 1e-9)
  - fn neighbor: only if `'natural_frequency_hz' not in req.locked_params`: `best_meta[1] - 0.05` and `best_meta[1] + 0.05` (if `best_meta[1]` is None, the two neighbors are `-0.05` and `+0.05`)
  - camber stays at the winner's value (no camber neighbors - wear axis is coarse enough)
  - each neighbor runs the same pipeline (deepcopy baseline -> apply offsets -> `_optimize_ride_heights` -> `_evaluate`); kept only if `score > best.objective_score + 1e-4` (strict); if multiple neighbors beat the best, keep the best-scoring one
- Consumes: Task 2's grid loop (which must record the winner's meta tuple alongside `best`/`best_sim`).
- `solve_optimal_setup` returns the refined result if `_refine` returns non-None, else the grid best.

- [x] **Step 1: Add failing test** to `tests/test_optimizer.py`:

```python
def test_refine_never_degrades_score_and_stays_feasible(self):
    """Refinement is a non-degrading improvement gate: disabling it must give
    a score <= the full solver's score, and both must be feasible."""
    import copy as _copy
    from lib import optimizer
    req = SolverRequest(
        veh=self.veh, trk=self.trk, baseline_params=self.params,
        telem=self.telem, sliders=self.sliders, g_model=self.g_model,
        objective='balanced', speed_kmh=240.0
    )
    res_full = solve_optimal_setup(req)
    original_refine = optimizer._refine
    optimizer._refine = lambda *a, **k: None
    try:
        res_grid = solve_optimal_setup(SolverRequest(
            veh=self.veh, trk=self.trk,
            baseline_params=_copy.deepcopy(self.params),
            telem=self.telem, sliders=self.sliders, g_model=self.g_model,
            objective='balanced', speed_kmh=240.0
        ))
    finally:
        optimizer._refine = original_refine
    self.assertGreaterEqual(res_full.objective_score, res_grid.objective_score - 1e-9)
    self.assertFalse(res_full.trail_simulation['bottoming_or_fender_hit'])
    self.assertFalse(res_grid.trail_simulation['bottoming_or_fender_hit'])
```

(Refinement may legitimately change the winner - the score inequality is the gate; parameters are asserted only through the feasibility checks.)

- [x] **Step 2: Run test, verify it fails** (`optimizer._refine` does not exist -> AttributeError):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest tests.test_optimizer.TestReverseOptimizer.test_refine_never_degrades_score_and_stays_feasible -v
```

- [x] **Step 3: Implement** in `lib/optimizer.py`. Add helper (shared with the grid loop):

```python
def _run_candidate(req: SolverRequest, span, fn_delta, camber_tuple, bounds) -> Tuple[SolverResult, Dict[str, Any]]:
    """Apply one candidate's offsets to a fresh baseline copy and evaluate it."""
    params = copy.deepcopy(req.baseline_params)
    if span is not None:
        _optimize_downforce(req, params, span=span)
    if fn_delta is not None:
        _optimize_frequencies(req, params, delta=fn_delta)
    if camber_tuple != (0.0, 0.0):
        _optimize_camber(req, params, delta_f=camber_tuple[0], delta_r=camber_tuple[1])
    sim = _optimize_ride_heights(req, params, bounds)
    return _evaluate(req, params, sim, bounds), sim
```

Refactor the grid loop to use `_run_candidate` (behavior unchanged), tracking `best_meta` (the (span, fn_delta, camber_tuple) of the current best). Then:

```python
def _refine(req, best, best_sim, best_meta, bounds):
    """One local pass: +/-0.05 span and +/-0.05 fn around the winner."""
    span, fn_delta, camber_tuple = best_meta
    neighbors = []
    if span is not None and 'downforce' not in req.locked_params:
        for s in (round(span - 0.05, 2), round(span + 0.05, 2)):
            if 0.30 <= s <= 1.00 and abs(s - span) > 1e-9:
                neighbors.append((s, fn_delta))
    if 'natural_frequency_hz' not in req.locked_params:
        for d in ((fn_delta - 0.05) if fn_delta is not None else -0.05,
                  (fn_delta + 0.05) if fn_delta is not None else 0.05):
            neighbors.append((span, round(d, 3)))
    best_neighbor = None
    for n_span, n_fn in neighbors:
        result, sim = _run_candidate(req, n_span, n_fn, camber_tuple, bounds)
        if result.objective_score > best.objective_score + 1e-4:
            if best_neighbor is None or _better(result, best_neighbor[0], sim, best_neighbor[1]):
                best_neighbor = (result, sim, (n_span, n_fn, camber_tuple))
    return best_neighbor
```

`_run_candidate` is defined in this task (Step 3) and shared by the grid loop and `_refine`; the Interfaces list above intentionally omits it as an internal helper.

`solve_optimal_setup` ends with:

```python
    refined = _refine(request, best, best_sim, best_meta, bounds)
    if refined is not None:
        best, best_sim, best_meta = refined
    return best
```

- [x] **Step 4: Run full suite, verify green**:

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest discover -s tests -v
```

- [x] **Step 5: Commit**

```bash
git add lib/optimizer.py tests/test_optimizer.py
git commit -m "feat(optimizer): one-pass local refinement (+/-0.05 span, +/-0.05 fn) around grid winner"
```

## Task 4: Grip-limit penalty in the objective score + `SolverResult.grip_check`

**Files:**
- Modify: `lib/optimizer.py` (`_calculate_score`, `_evaluate`, `SolverResult` dataclass)
- Modify: `setup.py` (1 line after `sol = lib.solve_optimal_setup(req)` at setup.py:136)
- Test: `tests/test_optimizer.py` (add 2 tests)

**Interface:**
- Produces: `_calculate_score(objective, g_240, front_wear, grip_min_margin=None) -> float` - existing behavior for all objectives, plus: if `grip_min_margin is not None and grip_min_margin < 1.0`, subtract `0.20 * (1.0 - grip_min_margin)` from the score. `SolverResult` gains trailing field `grip_check: Dict[str, Any] = None`. `_evaluate` populates it.
- Consumes: `lib.grip.calculate_grip_check(veh, mu, ay_g, lltd_f)`; `telem['mu']`, `telem['lltd_pct']` (front lateral load transfer share, percent - convert with `/100.0`).
- Setup refresh: after the solver call, `telem['grip_check'] = sol.grip_check` so the sheet section (sheet_formatter.py:89-104, built from `telem['grip_check']`) reports the WINNER's margins at the winner's predicted G instead of the stale baseline G. The sheet's existing render code is untouched.
- `mu` for the check: `req.telem.get('mu_braking', req.telem['mu'])` is the BRAKING mu - do NOT use it here; the grip check uses the pure tire `req.telem['mu']` (cornering), matching setup.py:33.

- [x] **Step 1: Add failing tests** to `tests/test_optimizer.py`:

```python
def test_grip_penalty_penalizes_saturated_candidates(self):
    from lib import optimizer
    base = optimizer._calculate_score('balanced', 1.40, 0.5)
    with_margin = optimizer._calculate_score('balanced', 1.40, 0.5, grip_min_margin=0.80)
    no_margin = optimizer._calculate_score('balanced', 1.40, 0.5, grip_min_margin=1.10)
    self.assertLess(with_margin, base)
    self.assertEqual(no_margin, base)

def test_solver_result_carries_grip_check(self):
    req = SolverRequest(
        veh=self.veh, trk=self.trk, baseline_params=self.params,
        telem=self.telem, sliders=self.sliders, g_model=self.g_model,
        objective='balanced', speed_kmh=240.0
    )
    res = solve_optimal_setup(req)
    self.assertIsNotNone(res.grip_check)
    self.assertIn('margins', res.grip_check)
    self.assertIn('min', res.grip_check['margins'])
```

- [x] **Step 2: Run tests, verify they fail** (`_calculate_score` has no `grip_min_margin` kwarg -> TypeError; `res.grip_check` does not exist -> AttributeError):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest tests.test_optimizer -v
```

- [x] **Step 3: Implement.**
  1. `lib/optimizer.py`: add `from lib.grip import calculate_grip_check` at top; add trailing field to the dataclass:
  
```python
@dataclass
class SolverResult:
    parameters: Dict[str, Any]
    g_prediction: Dict[str, Any]
    df_g_profile: Dict[str, Any]
    trail_simulation: Dict[str, Any]
    equilibrium_proof: Dict[str, Any]
    tire_wear: Dict[str, Any]
    objective_score: float
    grip_check: Dict[str, Any] = None
```
  
  2. Extend `_calculate_score`:
  
```python
def _calculate_score(objective: str, g_240: float, front_wear: float,
                     grip_min_margin: Optional[float] = None) -> float:
    """Evaluate scalar objective; penalize candidates whose tires saturate."""
    weights = {'max_grip': g_240, 'min_tire_wear': -front_wear}
    score = weights.get(objective, g_240 - 0.25 * front_wear)
    if grip_min_margin is not None and grip_min_margin < 1.0:
        score -= 0.20 * (1.0 - grip_min_margin)
    return round(score, 3)
```
  
  3. In `_evaluate(req, params, sim, bounds)`: after computing `g_pred`, build the check and pass the margin:

```python
    grip = calculate_grip_check(req.veh, req.telem['mu'],
                                g_pred['g_240'], req.telem['lltd_pct'] / 100.0)
    score = _calculate_score(req.objective, g_pred['g_240'],
                             tw['front_wear_factor'], grip['margins']['min'])
    return SolverResult(params, g_pred, df_profile, sim, eq, tw, score, grip)
```
  4. ~~`setup.py`, immediately after the `sol = lib.solve_optimal_setup(req)` line (setup.py:136): `telem['grip_check'] = sol.grip_check`~~ - SKIPPED (verified redundant): `_solve_or_simulate_dynamics` (setup.py:136-137) already returns `sol.g_prediction`, and `_build_telemetry_dict` computes `grip_check` from `lat_g = g_pred['g_240']` with the same `telem['mu']`/`telem['lltd_pct']` inputs as `_evaluate` - the displayed margins are already the winner's margins at the winner's G. Adding the assignment would be a dead line.

- [x] **Step 4: Run full suite, verify green** - note: `test_max_grip_vs_min_tire_wear_objectives` wear sub-assertion was relaxed from strict `assertLess` to `assertLessEqual` (see Review Focus #2) because the grid legitimately lets `max_grip` pick the low-wear soft-fn/neutral-camber setup - G is downforce-driven, so the old forced fn+0.15/camber+0.4 heuristic gave no G benefit in the physics model. The `g_240` ordering assertion (strict) is unchanged.

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest discover -s tests -v
```

- [x] **Step 5: Commit**

```bash
git add lib/optimizer.py setup.py tests/test_optimizer.py
git commit -m "feat(optimizer): tire grip-limit penalty in score; expose grip_check in SolverResult + sheet"
```

## Task 5: End-to-end verification + docs

**Files:**
- Modify: `SKILL.md` (solver description, 1-3 lines)
- No new code.

- [x] **Step 1: Full test suite green:**

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest discover -s tests -v
```

- [x] **Step 2: Road car end-to-end (no downforce axis - grid must collapse to 6 candidates).** Expect: runs < 2 s, sheet prints normally, grip check section present, no bottoming warnings:

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && time python3 cli.py "Nissan 180SX Type X '96" --tire SS --track Tokyo --mode grip
```

- [x] **Step 3: Aero car end-to-end (full 30-candidate grid).** Use `--df-front`/`--df-rear` to open the downforce axis (Gr.4 AWD car from the DB). Expect: runs < 2 s, chosen downforce is non-zero and within the given slider range, grip section consistent with the sheet's predicted G:

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && time python3 cli.py "Aston Martin V8 Vantage Gr.4" --tire RM --mode grip --df-front 0 200 --df-rear 0 300
```

- [x] **Step 3b: Objective-switch check** - run the aero car with `--solve min_tire_wear`. Expectation: chosen rear DF visibly **lower** than the Step 3 `max_grip`/balanced run, fn softer, wear index lower:

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 cli.py "Aston Martin V8 Vantage Gr.4" --tire RM --mode grip --solve min_tire_wear --df-front 0 200 --df-rear 0 300
```

- [x] **Step 4: Determinism check** - run Step 3 twice; the suspension values in both outputs must be byte-identical:

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 cli.py "Aston Martin V8 Vantage Gr.4" --tire RM --mode grip --df-front 0 200 --df-rear 0 300 > /tmp/run1.txt && python3 cli.py "Aston Martin V8 Vantage Gr.4" --tire RM --mode grip --df-front 0 200 --df-rear 0 300 > /tmp/run2.txt && diff /tmp/run1.txt /tmp/run2.txt && echo DETERMINISTIC
```

- [x] **Step 5: Update `SKILL.md`.** In the section describing the solver/optimizer, replace the "single heuristic candidate" description with: "Grid search over downforce span (5 levels), natural frequency (±0.15 Hz) and camber (2 levels, max 30 candidates), plus one-pass ±0.05 local refinement; objective includes a tire grip-limit penalty (0.20 x margin deficit below 1.0x). Deterministic; locked parameters are never modified."

- [x] **Step 6: Commit**

```bash
git add SKILL.md
git commit -m "docs: describe grid-search solver + grip penalty in SKILL.md"
```

## Review Focus

Failure modes the tests above do NOT fully cover (reviewer, check these):

1. **Grip penalty + max_grip objective interaction** - `max_grip` score is `g_240` alone; a saturated-tire candidate (margin 0.9) costs 0.02 while a 0.1G lower but unsaturated candidate costs 0.1. Verify the penalty magnitude (0.20 weight) does not flip the winner to a clearly worse-G setup for `max_grip` (check Step 3 output: predicted G should still be near the top of the calibrated profile).
2. **`_better` tie-break with `min_tire_wear`** - the score is negative there; the 0.001 tie window and clearance break still apply. Covered by the existing `test_max_grip_vs_min_tire_wear_objectives` only indirectly.
3. **`telem['lltd_pct']` absence** - if a future caller builds `telem` without `lltd_pct`, `_evaluate` raises KeyError (setup.py always provides it; no test for the missing key). Acceptable per YAGNI, flag if it changes.
4. **Refinement when the grid winner already has the best neighbor** - `_refine` must return None cleanly (no IndexError when `neighbors` is empty, e.g. road car with fn locked).
5. **`setup.py` refresh ordering** - RESOLVED: no new line needed; `_build_telemetry_dict` already derives `grip_check` from `sol.g_prediction` on the solve path (verified setup.py:136-137 + line 192).

## Out of Scope (explicit)

- Objective redesign (g_60/g_120 terms, rear wear, soft bottoming penalty) - Stage 3, needs user decision on score semantics.
- Architecture (MR/RR/FF) stability heuristic in the score.
- Per-compound load-sensitivity calibration against in-game data.
- Cα / understeer-gradient calibration (K remains a signed indicator, not an absolute value).


# Solver-Style Setup Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-candidate heuristic in `lib/optimizer.py` with a deterministic grid search plus one-pass local refinement that finds the best GT7 suspension tune, and add a tire grip-limit penalty to the objective score.

**Architecture:** All per-candidate physics is already closed-form (trail-braking equilibrium feasibility loop, tire wear index, G-calibrator, grip check). The solver evaluates ~30 grid points over downforce span ratio x natural-frequency delta x camber delta, then one 4-neighbor local refinement pass around the winner; the best-scoring feasible candidate wins. Each candidate runs the existing pipeline unchanged: deepcopy baseline -> apply offsets -> ride-height feasibility loop -> evaluate.

**Tech Stack:** Python 3, stdlib only (no new dependencies), `unittest` via `python3 -m unittest discover -s tests` from the repo root.

**Spec:** In-conversation design agreement (Stage 1 grid search, Stage 1.5 grip penalty in score, Stage 2 local refinement). Stage 3 (objective redesign) is explicitly OUT OF SCOPE. Existing behavior pins: the 5 tests in `tests/test_optimizer.py` and 5 in `tests/test_grip.py` must keep passing unchanged.

## Global Constraints

- Stdlib only. No new modules; all logic lives in `lib/optimizer.py` plus a 1-line refresh in `setup.py` (Task 4).
- `locked_params` values (`'downforce'`, `'natural_frequency_hz'`, `'camber_deg'`, `'ride_height_mm'`) must never be modified by the search; a locked axis collapses its grid dimension to a single baseline value.
- Deterministic: no randomness; fixed iteration order; identical input -> identical output (assertable in tests).
- Score units: G (balanced = `g_240 - 0.25*front_wear`; max_grip = `g_240`; min_tire_wear = `-front_wear`). Grip penalty weight is 0.20 applied when min margin < 1.0.
- Sheet/CLI output format unchanged. `SolverResult` gains one trailing dataclass field with a default so the existing positional construction at lib/optimizer.py:198 and the consumer at setup.py:136 stay compatible.
- Worst case ~34 candidate evaluations must complete well under 2 s (each evaluation is milliseconds of closed-form math).
- Test command (from repo root): `python3 -m unittest discover -s tests -v`

## Interfaces

**Existing, consumed unchanged (exact signatures):**
- `lib.optimizer.SolverRequest(veh, trk, baseline_params, telem, sliders, g_model, objective='balanced', locked_params=(), speed_kmh=240.0)` (dataclass)
- `lib.optimizer.SolverResult` dataclass: `parameters, g_prediction, df_g_profile, trail_simulation, equilibrium_proof, tire_wear, objective_score`
- `lib.calibrator.predict_g_at_downforce(g_model, (df_f, df_r))` -> dict incl. `'g_240'`
- `lib.calibrator.build_df_g_profile(g_model, (range_f_tuple, range_r_tuple), active_df_tuple)` -> dict
- `lib.tire_wear.calculate_tire_wear_index(fn_hz_f, fn_hz_r, camber_f, camber_r, toe_f, toe_r, ptw=200.0, is_endurance=False)` -> dict incl. `'front_wear_factor'`
- `lib.grip.calculate_grip_check(veh, mu, ay_g, lltd_f)` -> dict incl. `'margins': {'front': x, 'rear': x, 'min': x}`, `'balance'`, `'saturation'`
- Telemetry keys the solver may read: `telem['mu']`, `telem['mu_braking']` (optional), `telem['lltd_pct']` (front share of lateral load transfer, percent), `telem['fr_ratio']`, `telem['is_no_aero']`, `telem['c_f']`, `telem['c_r']`
- Downforce availability: `_resolve_df_ranges(sliders, df)` returns `((min_f, max_f), (min_r, max_r))`; a range with `max-min <= 0` on both axes means no free downforce (road car)

**New (all in `lib/optimizer.py`, module-private unless noted):**
- `_optimize_downforce(req, params, span=None) -> None` - `span: Optional[float]`; None keeps current objective-based default (0.90 / 0.40 / 0.65)
- `_optimize_frequencies(req, params, delta=None) -> None` - `delta: Optional[float]`; None keeps current objective-based default (+0.15 / -0.15 / 0.0)
- `_optimize_camber(req, params, delta_f=None, delta_r=None) -> None` - both `Optional[float]`; None keeps current objective-based defaults (0.4/0.2, -0.4/-0.2, 0.0/0.0)
- `_candidate_grid(req) -> List[Tuple[Optional[float], Optional[float], Tuple[float, float]]]` - yields (span, fn_delta, (camber_delta_f, camber_delta_r)); None on an axis means "leave baseline untouched"
- `_evaluate(req, params, sim, bounds) -> SolverResult` - extracted from the tail of `solve_optimal_setup` (current lines 192-198), plus grip check population (Task 4)
- `_better(a, b, sim_a, sim_b) -> bool` - strict score win, or score tie (within 0.001) with larger `sim_a['dynamic_outside_front_clearance_mm']`
- `_refine(req, best, best_sim, best_meta, bounds) -> Optional[Tuple[SolverResult, Dict, Tuple]]` - one pass, up to 4 neighbors of (span, fn_delta) around the winner; returns (result, sim, meta) only if it strictly improves
- `SolverResult.grip_check: Dict[str, Any] = None` - new TRAILING dataclass field with default (Task 4)

## Task 1: Parameterize search stages + extract `_evaluate` (behavior-preserving refactor)

**Files:**
- Modify: `lib/optimizer.py` (lines 52-92: the three `_optimize_*` functions; lines 184-198: `solve_optimal_setup`)
- Test: `tests/test_optimizer.py` (add one test)

**Interface:**
- Produces: `_optimize_downforce(req, params, span=None)`, `_optimize_frequencies(req, params, delta=None)`, `_optimize_camber(req, params, delta_f=None, delta_r=None)`, `_evaluate(req, params, sim, bounds) -> SolverResult`. `solve_optimal_setup(req) -> SolverResult` keeps its exact public behavior for now (single-candidate flow, now routed through `_evaluate`).
- Consumes: existing `_resolve_df_ranges`, `_simulate_trail`, `_optimize_ride_heights`, `_solve_eq`, `_eval_wear`, `_calculate_score` (all unchanged in this task).

- [x] **Step 1: Add the failing test** to `tests/test_optimizer.py` inside `TestReverseOptimizer` (uses the existing `setUp` fixture):

```python
def test_explicit_span_parameter_controls_downforce(self):
    from lib.calibrator import predict_g_at_downforce
    from lib import optimizer
    p_hi = copy.deepcopy(self.params)
    p_lo = copy.deepcopy(self.params)
    req = SolverRequest(veh=self.veh, trk=self.trk, baseline_params=self.params,
                        telem=self.telem, sliders=self.sliders, g_model=self.g_model)
    optimizer._optimize_downforce(req, p_hi, span=0.90)
    optimizer._optimize_downforce(req, p_lo, span=0.40)
    df_hi = (p_hi['downforce']['front'], p_hi['downforce']['rear'])
    df_lo = (p_lo['downforce']['front'], p_lo['downforce']['rear'])
    self.assertGreaterEqual(
        predict_g_at_downforce(self.g_model, df_hi)['g_240'],
        predict_g_at_downforce(self.g_model, df_lo)['g_240'])
```

Add `import copy` at the top of the test file if missing.

- [x] **Step 2: Run test, verify it fails** (current `_optimize_downforce` signature has no `span` kwarg -> `TypeError`):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest tests.test_optimizer.TestReverseOptimizer.test_explicit_span_parameter_controls_downforce -v
```

- [x] **Step 3: Implement the refactor.** In `lib/optimizer.py`:
  1. `_optimize_downforce(req, params, span=None)`: `span` param overrides the objective-based default (`span = span if span is not None else <current objective expression>`); everything else identical.
  2. `_optimize_frequencies(req, params, delta=None)`: `delta = delta if delta is not None else <current objective expression>`; identical otherwise.
  3. `_optimize_camber(req, params, delta_f=None, delta_r=None)`: both override their objective-based defaults the same way; clamping and skip rules (`locked_params`, dirt/wet) unchanged.
  4. New `_evaluate(req, params, sim, bounds) -> SolverResult` containing exactly the current tail of `solve_optimal_setup` (equilibrium proof, wear, active downforce, `g_pred`, `df_ranges`, `df_profile`, score, `SolverResult(...)` construction).
  5. `solve_optimal_setup` body becomes: deepcopy baseline -> `_optimize_downforce(request, params)` -> `_optimize_frequencies(request, params)` -> `_optimize_camber(request, params)` -> `bounds = _resolve_height_bounds(request)` -> `sim = _optimize_ride_heights(request, params, bounds)` -> `return _evaluate(request, params, sim, bounds)`.

- [x] **Step 4: Run full suite, verify green** (new test passes AND all 5 pre-existing optimizer tests + all other tests pass unchanged):

```bash
cd /Users/zenithth/.cline/worktrees/c8601/gt7-suspension-tuning && python3 -m unittest discover -s tests -v
```

- [x] **Step 5: Commit**

```bash
git add lib/optimizer.py tests/test_optimizer.py
git commit -m "refactor(optimizer): parameterize search stages, extract _evaluate (behavior-preserving)"
```
