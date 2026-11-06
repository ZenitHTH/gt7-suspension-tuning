# Progress Ledger — GT7 Suspension GUI Plan (2026-07-12)

Plan: `docs/superpowers/plans/2026-07-12-gt7-suspension-gui.md`
Branch: `cline/c8601` | Baseline commit: `142c87f` (plan doc)
Harness note: `spawn_agent` has no model parameter — all subagents run the session model. (Ruling: no model control exists in this harness; proceed.)

- Task 1: complete (commits 142c87f..1aa3175, review clean)
- Task 1: minor (deferred): #c62828 only documented in theme.py comment (applied inline by ResultsView, Task 6); non-numeric GT7_GUI_AUTO_QUIT_MS → ValueError; blank line in gui/__init__.py
- Task 2: complete (commits 1aa3175..9c155b3, review clean)
- Task 2: minor (deferred): test asserts 'QUICK-TRIMS DELTA TABLE' not 'Quick-Trim' (matches real sheet text); extra "must be a (min,max) pair" validation message; duplicate get_car call in compute
- Task 2: Ruling: plan "8 range fields" None-warning wording was internally contradictory (unsatisfiable with its own test) — scoped to the 6 slider fields with DB fallback; plan text corrected
- Task 3: complete (commits 9c155b3..7b0abdb, review clean)
- Task 3: minor (deferred): failed-signal path untested (brief mandates only finished; compute never raises)
- Task 4: complete (commits 7b0abdb..46313b6, review clean)
- Task 4: minor (deferred): float-kind assertion in separate test (behavior covered); form.py missing trailing newline; _ensure_app/_APP boilerplate duplicated across test files (expect 3rd copy in Task 5)
- Task 4: Ruling: brief "8 × RangePair" typo — 6 named pairs implemented; plan corrected. DB car records have no axle-width fields — db_info_label shows verified fields only; plan corrected
- Task 5: complete (commits 46313b6..9c3baf6, 1 fix round)
- Task 5: fix round 1/5 (2 addressed, 0 open — _ref_df (v,v) rule + pinning test; commit 9c3baf6)
- Task 5: minor (deferred): validate() suppresses warnings when errors present (elif precedence); test_collect_full_request doesn't set/assert custom_mass; bare `assert` style in test
- Task 6: pending
- Task 6: complete (commits 9c3baf6..ba0b129, review clean)
- Task 6: minor (deferred): no try/except around collect()/Worker construction in _on_compute (practically unreachable — button could stick "Computing…"); e2e test prints timing line; no closeEvent/thread-stop on window close (worst case exit notice)
- Task 7: complete (commits ba0b129..f055f33, review clean)
- Task 7: minor (deferred — final review to triage): stale-PNG trap in theme.py glyph write (existence-only guard; fix: rewrite unconditionally or size-check — one line); non-atomic PNG write (subsumed); _ARROW_RGB duplicates text-primary token (no sync enforcement); Windows backslash path in QSS url() (macOS-only per plan); glyph PNGs deviate from "no images" principle (documented, justified)
- Final review: done (a34d8c4..f055f33) — 2 findings: Critical DF clamp/clobber + Important close-during-solve qFatal; verdict With fixes
- Final fix wave: complete (commit dbf104d, scoped re-review clean; 118/118 green)
- Final fix wave: minor (deferred): misleading comment at gui/app.py:186 ("unblock the loop" — no loop on worker thread); pre-existing: GT7_GUI_AUTO_QUIT_MS timer path bypasses closeEvent (unreachable in current flows)
- Ruling (final): fix-wave scope = the 2 must-fix findings + GUI.md note; plan doc max_v/closeEvent corrections applied by controller post-wave
