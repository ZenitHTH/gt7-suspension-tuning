#!/usr/bin/env python3
"""
GT7 Setup Synthesizer Orchestrator (Root Setup Coordinator)
Coordinates models from models.py and executes calculations through lib/ calculation modules.
"""

from typing import Dict, Optional, Any, Tuple, List
from models import VehicleSpec, TrackSpec
import lib

def build_setup(
    car: Dict[str, Any],
    track: Optional[Dict[str, Any]] = None,
    tire: str = 'SS',
    custom_mass: Optional[int] = None,
    custom_power: Optional[int] = None,
    custom_torque: Optional[float] = None,
    custom_drivetrain: Optional[str] = None,
    custom_balance: Optional[Tuple[int, int]] = None,
    mode: str = 'grip',
    df_front_range: Optional[Tuple[int, int]] = None,
    df_rear_range: Optional[Tuple[int, int]] = None,
    height_range: Optional[Tuple[int, int]] = None,
    height_front_range: Optional[Tuple[int, int]] = None,
    height_rear_range: Optional[Tuple[int, int]] = None,
    fn_front_range: Optional[Tuple[float, float]] = None,
    fn_rear_range: Optional[Tuple[float, float]] = None,
    stability: Optional[Tuple[float, float]] = None,
    symptoms: Optional[List[str]] = None,
    is_widebody: bool = False,
    speed_kmh: Optional[float] = None
) -> Dict[str, Any]:
    """Coordinate vehicle parameters and compute setup using modular lib/ calculations."""
    saved_sliders = car.get('slider_ranges') or {}
    if df_front_range is None and 'df_front' in saved_sliders:
        df_front_range = tuple(saved_sliders['df_front'])
    if df_rear_range is None and 'df_rear' in saved_sliders:
        df_rear_range = tuple(saved_sliders['df_rear'])
    if height_range is None and 'height_range' in saved_sliders:
        height_range = tuple(saved_sliders['height_range'])
    if height_front_range is None and 'height_front' in saved_sliders:
        height_front_range = tuple(saved_sliders['height_front'])
    if height_rear_range is None and 'height_rear' in saved_sliders:
        height_rear_range = tuple(saved_sliders['height_rear'])
    if fn_front_range is None and 'fn_front' in saved_sliders:
        fn_front_range = tuple(saved_sliders['fn_front'])
    if fn_rear_range is None and 'fn_rear' in saved_sliders:
        fn_rear_range = tuple(saved_sliders['fn_rear'])

    overrides = {
        'mass': custom_mass,
        'power': custom_power,
        'torque': custom_torque,
        'drivetrain': custom_drivetrain,
        'balance': custom_balance
    }
    veh = VehicleSpec.from_dict(car, custom_overrides=overrides, is_widebody=is_widebody)
    trk = TrackSpec.from_dict(track, mode=mode, tire=tire)

    car = dict(car)
    car['mass_kg'] = int(veh.mass_kg)
    car['drivetrain'] = veh.drivetrain
    car['balance'] = {
        'front_pct': int(round(veh.front_weight_ratio * 100)),
        'rear_pct': int(round(veh.rear_weight_ratio * 100)),
        'ratio_str': f"{int(round(veh.front_weight_ratio * 100))}:{int(round(veh.rear_weight_ratio * 100))}"
    }

    mu = lib.get_tire_mu(tire)
    ay_est = mu * (0.90 if trk.bumpiness == 'high' else (1.05 if trk.bumpiness == 'low' else 1.00))

    tot_s, c_f, c_r = lib.calculate_sprung_mass(veh.mass_kg, veh.front_weight_ratio, veh.group)
    rh_f, rh_r = lib.calculate_ride_height(
        trk.is_dirt, veh.is_racecar, veh.is_ultralight, veh.body_style, trk.bumpiness,
        veh.power_to_weight, veh.front_weight_ratio, height_range, height_front_range,
        height_rear_range, elevation_diff_m=trk.elevation_diff_m, is_widebody=is_widebody,
        height_m=veh.height_m, group=veh.group
    )
    df = lib.calculate_aerodynamics(
        df_front_range, df_rear_range, veh.front_weight_ratio, veh.group,
        is_oval=trk.is_oval, downforce_demand=trk.downforce_demand, is_endurance=trk.is_endurance,
        width_m=veh.width_m, height_m=veh.height_m, body_style=veh.body_style
    )
    fn_f, fn_r, fr_ratio = lib.calculate_natural_frequencies(
        mu, veh.front_weight_ratio, trk.bumpiness, veh.group, veh.mass_kg,
        trk.is_dirt, trk.is_endurance, fn_front_range, fn_rear_range,
        df_front=df['front'], df_rear=df['rear']
    )
    arb_f, arb_r, lltd_pct = lib.calculate_anti_roll_bars(veh.front_weight_ratio, veh.drivetrain, trk.is_dirt)
    is_high_boost = ('Turbo' in veh.aspiration and veh.power_hp > 450)
    comp_f, comp_r, exp_f, exp_r = lib.calculate_dampers(
        trk.bumpiness, veh.power_to_weight, is_high_boost, veh.drivetrain,
        veh.front_weight_ratio, trk.is_dirt, trk.is_wet, elevation_diff_m=trk.elevation_diff_m
    )
    cam_f, cam_r, toe_f, toe_r = lib.calculate_wheel_alignment(
        ay_est, veh.front_weight_ratio, veh.rear_weight_ratio, veh.drivetrain,
        veh.power_hp, trk.is_dirt, trk.is_wet, trk.is_endurance
    )
    lsd_rear, lsd_front = lib.calculate_differential_lsd(
        veh.torque_nm, veh.power_to_weight, veh.rear_weight_ratio, veh.drivetrain, trk.is_endurance
    )
    if veh.drivetrain == 'FF':
        lsd_front = dict(lsd_rear) if isinstance(lsd_rear, dict) else lsd_rear
    bias, pitch_transfer_pct = lib.calculate_brake_bias(
        veh.front_weight_ratio, veh.hcg_m, veh.wheelbase_m, veh.drivetrain, is_endurance=trk.is_endurance
    )

    auto_top_speed = lib.calculate_top_speed(veh.power_hp, veh.power_to_weight, trk.longest_straight_m, trk.is_oval)

    notes = []
    if is_widebody:
        notes.append("• [Widebody Clearance] เพิ่มระยะยุบตัวซุ้มล้อหน้า +5 มม. เพื่อป้องกันหน้ายางขัดกับซุ้มล้อ (Fender Scrub) ขณะแตะเบรกลึก")
    if trk.is_endurance:
        notes.append("• [Tire Conservation] เซ็ตติ้งเน้นถนอมยาง: ลดมุม Camber และ Toe เพื่อลดการกินขอบยางด้านในและตัดการไถลากบนทางตรงยาว พร้อมลดสปริงเรทลงเพื่อลดความร้อนสะสมในเนื้อยาง")
    if veh.front_weight_ratio >= 0.55 and veh.drivetrain == 'FR':
        notes.append("• [Anti-Understeer] ปลดล็อค LSD Braking = 22-26 (บนสเกล 0-100) และ ARB หน้าอ่อน/หลังแข็ง เพื่อให้ท้ายช่วยหมุนเข้าเอเปกซ์")
        if any(yr in veh.name for yr in ["'6", "'7", "196", "197"]):
            notes.append("• [CRITICAL WARNING] ห้ามติดตั้ง Steering Angle Adapter (ตัวปรับมุมเลี้ยว) สำหรับวิ่งกริป! มันเป็นอะไหล่ดริฟต์ที่ลบ Ackermann geometry ทำให้ล้อหน้าไถต้านกันและดื้อโค้งสนิทเมื่อแตะเบรก")
            notes.append("• [Driving Assists] ปิด ASM (Active Stability Management) และ Countersteering Assistance เป็น OFF เพื่อให้ทำ Trail Braking ได้")
            notes.append("• [Chassis Rigidity] ติดตั้ง Roll Cage (โรลเคจ) ใน GT Auto เพื่อลดการบิดตัวของโครงสร้างตัวถังยุคคลาสสิก")
    elif veh.drivetrain in ['MR', 'RR']:
        notes.append("• [MR/RR Stability] LSD Braking ล็อคแน่น 52-65 (บนสเกล 0-100) ป้องกันอาการท้ายสะบัดหมุน (Snap Oversteer) ขณะแตะเบรกเลี้ยว (Trail-Braking)")

    if veh.group == 'Gr.4' and veh.drivetrain in ['AWD', '4WD']:
        notes.append("• [Gr.4 AWD Center Diff] รถแข่ง Gr.4 ขับเคลื่อน 4 ล้อ (AWD/4WD) ล็อค Center Diff จากโรงงาน ไม่สามารถติดตั้งหรือปรับ Torque-Distributing Center Diff ได้ (Fixed Homologation)")
        notes.append("  ↳ วิธีแก้หน้าดื้อ: ให้คลาย LSD ล้อหน้าให้อ่อน (Accel 14-16 / Braking 18-20), ปรับ ARB หน้าอ่อน/หลังแข็ง (3/7 หรือ 2/8), ปรับสมดุลเบรกไปหลัง (-2), และใช้ Front Toe-Out ช่วยดึงหน้ารถเข้าโค้ง")

    awd_split = None
    if veh.drivetrain in ['AWD', '4WD']:
        awd_split = 'Fixed (Homologation / ปรับไม่ได้ใน Gr.4)' if veh.group == 'Gr.4' else '35:65'

    rh_dict = {'front': rh_f, 'rear': rh_r}
    if height_range:
        rh_dict['range'] = f"{height_range[0]}-{height_range[1]}"
    elif height_front_range and height_rear_range:
        rh_dict['range_f'] = f"{height_front_range[0]}-{height_front_range[1]}"
        rh_dict['range_r'] = f"{height_rear_range[0]}-{height_rear_range[1]}"

    fn_dict = {'front': fn_f, 'rear': fn_r}
    if fn_front_range and fn_rear_range:
        fn_dict['range_f'] = f"{fn_front_range[0]:.2f}-{fn_front_range[1]:.2f}"
        fn_dict['range_r'] = f"{fn_rear_range[0]:.2f}-{fn_rear_range[1]:.2f}"

    params = {
        'ride_height_mm': rh_dict,
        'natural_frequency_hz': fn_dict,
        'anti_roll_bar': {'front': arb_f, 'rear': arb_r},
        'damping_compression_pct': {'front': comp_f, 'rear': comp_r},
        'damping_expansion_pct': {'front': exp_f, 'rear': exp_r},
        'camber_deg': {'front': cam_f, 'rear': cam_r},
        'toe_angle': {'front': toe_f, 'rear': toe_r},
        'downforce': df,
        'lsd_rear': lsd_rear,
        'lsd_front': lsd_front,
        'brake_bias': bias,
        'awd_torque_split': awd_split,
        'transmission_top_speed_kmh': auto_top_speed,
        'endurance_notes': notes
    }

    if stability or symptoms:
        params = lib.apply_closed_loop_trim(
            parameters=params,
            stability=stability,
            symptoms=symptoms,
            drivetrain=veh.drivetrain,
            group=veh.group
        )
        if stability:
            notes.append(f"• [Closed-Loop Stability Trim] ปรับจูนชดเชยค่าความเสถียร (Stability Index: Low {stability[0]}, High {stability[1]})")
        if symptoms:
            notes.append(f"• [Symptom Trim] ปรับจูนแก้อาการขับขี่: {', '.join(symptoms)}")

    sim_spd = float(speed_kmh) if speed_kmh is not None else (240.0 if veh.is_racecar else 200.0)
    h_min_f = height_front_range[0] if height_front_range else (height_range[0] if height_range else (45 if veh.is_racecar else 90))

    sim = lib.simulate_high_speed_trail_braking(
        speed_kmh=sim_spd,
        mass_kg=veh.mass_kg,
        corner_front_kg=c_f,
        corner_rear_kg=c_r,
        wf=veh.front_weight_ratio,
        hcg_m=veh.hcg_m,
        wheelbase_m=veh.wheelbase_m,
        track_width_m=veh.track_width_m,
        mu=mu,
        rh_front_mm=params['ride_height_mm']['front'],
        rh_rear_mm=params['ride_height_mm']['rear'],
        fn_front_hz=params['natural_frequency_hz']['front'],
        fn_rear_hz=params['natural_frequency_hz']['rear'],
        arb_front=params['anti_roll_bar']['front'],
        arb_rear=params['anti_roll_bar']['rear'],
        df_front=params['downforce']['front'] if params.get('downforce') else 0,
        df_rear=params['downforce']['rear'] if params.get('downforce') else 0,
        is_widebody=is_widebody,
        height_min_front_mm=h_min_f
    )

    if sim['bottoming_or_fender_hit']:
        bump = sim['recommended_front_rh_bump_mm']
        notes.append(f"⚠️ [Bottoming/Fender Guard] ตรวจพบความเสี่ยงล้อหน้ากระแทกซุ้มล้อ/Bump Stop ที่ความเร็ว {sim_spd:.0f} km/h (ยุบรวม {sim['total_outside_front_compression_mm']} มม.) -> แนะนำยกหน้าขึ้น +{bump} มม.")

    params['quick_trims'] = lib.build_quick_trims(params, drivetrain=veh.drivetrain, is_endurance=trk.is_endurance)

    return {
        'car': car,
        'track': track,
        'tire_compound': tire,
        'setup_mode': mode,
        'telemetry': {
            'mass_sprung_total_kg': tot_s,
            'mass_sprung_corner_f_kg': c_f,
            'mass_sprung_corner_r_kg': c_r,
            'weight_dist_pct': f'{veh.front_weight_ratio*100.0:.1f}% F / {veh.rear_weight_ratio*100.0:.1f}% R',
            'tire_friction_mu': mu,
            'lateral_g_capacity': round(ay_est, 2),
            'target_lltd_front_pct': lltd_pct,
            'flat_ride_frequency_ratio': fr_ratio,
            'dynamic_braking_pitch_transfer_pct': pitch_transfer_pct,
            'brake_bias': params['brake_bias'],
            'high_speed_simulation': sim
        },
        'parameters': params
    }
