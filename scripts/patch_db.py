#!/usr/bin/env python3
"""
GT7 Database Patch Script
Fixes confirmed incorrect entries in cars_master.json and stockperf.csv.

Sources:
  - F1500T-A: User-verified in-game (PP 948.93 RS, 986 HP, V6-F1500T-A engine)
  - Ferrari 499P: Web-verified (Gr.1 LMH, AWD, 1030kg, 48:52, ~670HP, PP ~851)
  - BMW/Peugeot/Porsche LMH: Cross-referenced group/drivetrain corrections
"""

import json
import csv
import shutil
from pathlib import Path
from datetime import datetime

CARS_JSON = Path("data/cars_master.json")
STOCKPERF_CSV = Path("data/csv/stockperf.csv")
BACKUP_SUFFIX = f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


# ─────────────────────────────────────────────────────────────────────────────
# PATCH DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

CARS_PATCHES = {

    # F1500T-A — wrong power (1000→986), wrong aspiration, missing engine code
    # Source: user confirmed in-game + web (gran-turismo.com, gtplus.app)
    "3342": {
        "engine.code": "V6-F1500T-A",
        "engine.displacement_cc": 1500,
        "engine.power_hp": 986,
        "engine.torque_nm": 658.2,
        "engine.aspiration": "Turbocharged",   # single turbo, not twin
        "engine.gearbox": "7-speed",            # F1-style sequential
        "slider_ranges": {
            "height_front": [45, 60], "height_rear": [45, 60],
            "fn_front": [4.0, 6.0], "fn_rear": [4.0, 6.0],
            "df_front": [700, 900], "df_rear": [1300, 1700]
        },
        # Note: balance 40:60 and mass 540kg are correct per user
    },

    # Red Bull X2019 Competition & 25th Anniversary
    "3374": {
        "slider_ranges": {
            "height_front": [45, 55], "height_rear": [50, 65],
            "fn_front": [4.0, 6.0], "fn_rear": [4.0, 6.0],
            "df_front": [800, 1200], "df_rear": [1200, 1600]
        }
    },
    "3517": {
        "slider_ranges": {
            "height_front": [45, 55], "height_rear": [50, 65],
            "fn_front": [4.0, 6.0], "fn_rear": [4.0, 6.0],
            "df_front": [800, 1200], "df_rear": [1200, 1600]
        }
    },

    # Porsche 911 Turbo S Leichtbau '93
    "3440": {
        "slider_ranges": {
            "df_front": [50, 200], "df_rear": [140, 290]
        }
    },

    # Porsche 911 Turbo (930) '81
    "3385": {
        "slider_ranges": {
            "df_front": [50, 200], "df_rear": [100, 250]
        }
    },

    # Chevrolet Camaro ZL1 1LE Package '18
    "3387": {
        "slider_ranges": {
            "df_front": [200, 250], "df_rear": [300, 350]
        }
    },

    # Toyota Supra GT Road Car (JZA80)
    "3596": {
        "slider_ranges": {
            "height_front": [65, 105], "height_rear": [65, 105],
            "fn_front": [1.5, 3.5], "fn_rear": [1.5, 3.5],
            "df_front": [200, 200], "df_rear": [400, 500]
        }
    },

    # Ferrari F355 Berlinetta '94
    "3614": {
        "slider_ranges": {
            "df_front": [50, 200], "df_rear": [100, 250]
        }
    },

    # Toyota Chaser Tourer V '97 — miscategorised as Gr.3 in upstream DB
    "3612": {
        "group": "Road Car",
        "body_style": "Sedan",
        "stock_pp": 487.5,
    },

    # Ferrari 499P — duplicated 296 GT3 data. Real: Gr.1 LMH AWD hybrid
    # Source: gran-turismo.com + web search consensus
    "3605": {
        "group": "Gr.1",
        "body_style": "LMH Hypercar",
        "drivetrain": "AWD",
        "mass_kg": 1030,
        "balance.front_pct": 48,
        "balance.rear_pct": 52,
        "balance.ratio_str": "48:52",
        "engine.code": "F163CE-Hybrid",
        "engine.type": "V6",
        "engine.aspiration": "Twin-Turbocharged + Hybrid MGU",
        "engine.displacement_cc": 2992,
        "engine.power_hp": 670,         # combined ICE + MGU (stock)
        "engine.torque_nm": 790.0,       # ~582.8 ft-lb combined
        "engine.gearbox": "7-speed",
        "stock_pp": 851.27,
    },

    # BMW M Hybrid V8 '25 — LMDh, likely Gr.1 not Road Car
    # Source: cross-reference (1030kg LMDh class)
    "3604": {
        "group": "Gr.1",
        "body_style": "LMDh Hypercar",
    },

    # Peugeot 9X8 '25 — LMH AWD, not Road Car
    # Source: cross-reference (1030kg LMH class)
    "3606": {
        "group": "Gr.1",
        "body_style": "LMH Hypercar",
    },

    # Porsche 963 '24 — LMDh MR, not Road Car
    # Source: cross-reference (1030kg LMDh class)
    "3607": {
        "group": "Gr.1",
        "body_style": "LMDh Hypercar",
    },

    # Honda Step WGN Spada Premium Line '23 — 4WD (RP7) in GT7, not FF
    # Source: user confirmed in-game + gran-turismo.com (4WD, 1810kg, 57:43, 147 HP, 203.0 Nm)
    "3616": {
        "drivetrain": "AWD",
        "mass_kg": 1810,
        "balance.front_pct": 57,
        "balance.rear_pct": 43,
        "balance.ratio_str": "57:43",
        "engine.power_hp": 147,
        "engine.torque_nm": 203.0,
    },
}

# PP corrections for stockperf.csv
# F1500T-A RS confirmed by user = 948.93 (was 934.82, delta = +14.11)
# Other compounds: proportional delta applied (approximate — only RS is user-verified)
F1500T_PP_DELTA = 948.93 - 934.82  # = +14.11

STOCKPERF_PATCHES = {
    # Format: (car_id, tire): new_pp
    ("3342", "RS"): 948.93,   # USER CONFIRMED ✅
    ("3342", "RM"): round(925.54 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "RH"): round(913.82 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "SS"): round(901.53 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "SM"): round(876.36 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "SH"): round(849.32 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "CS"): round(825.65 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "CM"): round(791.10 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "CH"): round(732.46 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "IM"): round(901.53 + F1500T_PP_DELTA, 2),   # approx
    ("3342", "W"):  round(876.35 + F1500T_PP_DELTA, 2),   # approx
    # 499P stock PP (Gr.1, no tire breakdown available)
    ("3605", "CS"): 851.27,   # approximate stock CS PP from web
}


# ─────────────────────────────────────────────────────────────────────────────
# PATCH APPLIERS
# ─────────────────────────────────────────────────────────────────────────────

def set_nested(d: dict, dotpath: str, value):
    """Set a nested dict value via dot-notation path like 'engine.power_hp'."""
    keys = dotpath.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def apply_car_patches(cars: list) -> tuple[list, list]:
    """Apply CARS_PATCHES to the car list. Returns (patched_list, change_log)."""
    log = []
    id_map = {c["id"]: c for c in cars}

    for car_id, patches in CARS_PATCHES.items():
        if car_id not in id_map:
            log.append(f"  ⚠️  ID {car_id} not found — skipped")
            continue

        car = id_map[car_id]
        log.append(f"\n  🔧 {car['name']} (ID {car_id})")
        for dotpath, new_val in patches.items():
            # Read old value for logging
            keys = dotpath.split(".")
            old = car
            for k in keys:
                old = old.get(k, "MISSING") if isinstance(old, dict) else "MISSING"

            set_nested(car, dotpath, new_val)
            log.append(f"       {dotpath}: {old!r} → {new_val!r}")

    return cars, log


def apply_stockperf_patches(rows: list) -> tuple[list, list]:
    """Apply STOCKPERF_PATCHES to stockperf rows. Returns (patched_rows, change_log)."""
    log = []
    patched = []
    for row in rows:
        key = (row["ID"], row["Tyre"])
        if key in STOCKPERF_PATCHES:
            old = row["PP"]
            row = dict(row)
            row["PP"] = str(STOCKPERF_PATCHES[key])
            verified = "✅ USER VERIFIED" if key == ("3342", "RS") else "~ approx"
            log.append(f"  ID {key[0]} {key[1]}: {old} → {row['PP']}  {verified}")
        patched.append(row)
    return patched, log


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  GT7 Database Patch")
    print("=" * 65)

    # ── Backup originals ──────────────────────────────────────────────
    for path in [CARS_JSON, STOCKPERF_CSV]:
        backup = path.with_suffix(path.suffix + BACKUP_SUFFIX)
        shutil.copy2(path, backup)
        print(f"\n📦 Backed up: {path.name} → {backup.name}")

    # ── Patch cars_master.json ────────────────────────────────────────
    print("\n\n── cars_master.json ─────────────────────────────────────────")
    with open(CARS_JSON, "r", encoding="utf-8") as f:
        cars = json.load(f)

    cars, car_log = apply_car_patches(cars)
    for line in car_log:
        print(line)

    with open(CARS_JSON, "w", encoding="utf-8") as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {CARS_JSON}")

    # ── Patch stockperf.csv ───────────────────────────────────────────
    print("\n\n── stockperf.csv ─────────────────────────────────────────────")
    with open(STOCKPERF_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    rows, pp_log = apply_stockperf_patches(rows)
    for line in pp_log:
        print(line)

    with open(STOCKPERF_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "PP", "Tyre"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n✅ Saved: {STOCKPERF_CSV}")

    # ── Verify round-trip ─────────────────────────────────────────────
    print("\n\n── Verification ──────────────────────────────────────────────")
    with open(CARS_JSON) as f:
        verify_cars = {c["id"]: c for c in json.load(f)}

    checks = [
        ("3342", "engine.power_hp", 986),
        ("3342", "engine.code", "V6-F1500T-A"),
        ("3342", "engine.aspiration", "Turbocharged"),
        ("3605", "group", "Gr.1"),
        ("3605", "drivetrain", "AWD"),
        ("3605", "mass_kg", 1030),
        ("3605", "stock_pp", 851.27),
        ("3616", "drivetrain", "AWD"),
        ("3616", "mass_kg", 1810),
        ("3616", "balance.ratio_str", "57:43"),
    ]
    all_ok = True
    for car_id, dotpath, expected in checks:
        car = verify_cars.get(car_id, {})
        keys = dotpath.split(".")
        val = car
        for k in keys:
            val = val.get(k) if isinstance(val, dict) else None
        ok = val == expected
        all_ok = all_ok and ok
        status = "✅" if ok else "❌"
        print(f"  {status} ID {car_id} {dotpath}: {val!r} (expected {expected!r})")

    print()
    if all_ok:
        print("✅ ALL CHECKS PASSED — Database patched successfully")
    else:
        print("❌ SOME CHECKS FAILED — Review output above")

    print("\nNote: stockperf.csv RS=948.93 is USER-VERIFIED.")
    print("      Other F1500T-A tire PP values are approximate (+14.11 delta).")
    print("      Confirm remaining compounds in-game to finalize.")


if __name__ == "__main__":
    main()
