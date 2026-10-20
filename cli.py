#!/usr/bin/env python3
"""
GT7 Race-Engineering CLI Interface & Setup Sheet Formatter (Root Runner)
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, Optional

import setup
from db.interface import get_car, get_track, save_car_sliders

def format_setup_sheet(setup_dict: Dict[str, Any]) -> str:
    """Format setup into dual English/Thai GT7 tuning sheet."""
    car, params, telem, track = setup_dict['car'], setup_dict['parameters'], setup_dict.get('telemetry', {}), setup_dict.get('track')
    t_name = track['name'] if track else 'General Balanced Circuit'

    lines = [
        '=' * 86,
        '🏎️  GT7 FIRST-PRINCIPLES SUSPENSION & CHASSIS SETUP SHEET (Update 1.72+ Spec IV)',
        f"Target Car:   {car.get('name')} [{car.get('drivetrain')}, {car.get('mass_kg', 'N/A')} kg, {car.get('balance',{}).get('ratio_str','N/A')}]",
        f"Target Track: {t_name} | Tire: {setup_dict['tire_compound']} | Mode: {setup_dict['setup_mode'].upper()}",
        '=' * 86,
        '📊 พารามิเตอร์ทางกายภาพที่คำนวณได้จาก First Principles (Derived Physical Telemetry):',
        f"• น้ำหนัก Sprung Mass: รวม {telem.get('mass_sprung_total_kg')} kg (มุมหน้า: {telem.get('mass_sprung_corner_f_kg')} kg | มุมหลัง: {telem.get('mass_sprung_corner_r_kg')} kg)",
        f"• สัมประสิทธิ์กริปยาง (μ): {telem.get('tire_friction_mu')} | แรงเหวี่ยงสูงสุดโดยประมาณ: {telem.get('lateral_g_capacity')} G",
        f"• เป้าหมายการถ่ายเทน้ำหนักขณะเลี้ยว (Target Front LLTD): {telem.get('target_lltd_front_pct')}% (คุมบาลานซ์เลี้ยวเข้าเอเปกซ์)",
        f"• อัตราส่วน Flat Ride (หลัง/หน้า): {telem.get('flat_ride_frequency_ratio')} (ซิงค์จังหวะยุบ-คืนตัวข้ามเนินและผิวขรุขระ)",
        f"• แรงถ่ายเทน้ำหนักขณะเบรก (Braking Load Transfer): +{telem.get('dynamic_braking_pitch_transfer_pct')}% ถ่ายไปล้อหน้า",
    ]

    if telem.get('high_speed_simulation'):
        sim = telem['high_speed_simulation']
        status_sym = '⚠️ เสี่ยงกระแทกซุ้มล้อ/Bump Stop' if sim['bottoming_or_fender_hit'] else '✅ ปลอดภัย (มีระยะยุบเหลือ)'
        lines.append(f"• จำลองการยุบตัวล้อหน้านอกโค้งขณะ Trail-Braking ที่ {sim['speed_kmh']} km/h: {status_sym}")
        lines.append(
            f"  ↳ แรงกดแอร์โร: {sim['aero_compression_mm']['front']} มม. | แรงทิ่มเบรก: {sim['pitch_compression_front_mm']} มม. | แรงเอียงเลี้ยว: {sim['roll_compression_front_mm']} มม. "
            f"(ยุบรวม {sim['total_outside_front_compression_mm']} มม. | ระยะเหลือ {sim['dynamic_outside_front_clearance_mm']} มม. | Rake ขณะวิ่ง {sim['dynamic_rake_mm']} มม.)"
        )

    if telem.get('equilibrium_proof'):
        eq = telem['equilibrium_proof']
        eq_status = '✅ ผ่าน (Compliance Pass)' if eq['trail_braking_feasible'] else '⚠️ เสี่ยง Bump Stop (Compliance Warn)'
        lines.append(f"• สมดุลฟิสิกส์ Trail-Braking & ทอร์กส่งกำลัง (Equilibrium Proof): {eq_status}")
        lines.append(
            f"  ↳ แรงบิดกดท้าย (Acceleration Squat): {eq['acceleration_squat_rear_mm']} มม. | หน้าลอย (Lift): {eq['acceleration_lift_front_mm']} มม. | Rake ตอนกดคันเร่ง: {eq['dynamic_rake_accel_mm']} มม."
        )
        lines.append(
            f"  ↳ ระยะยุบเหลือขณะ Trail-Braking: {eq['min_dynamic_clearance_mm']} มม. (ยุบรวม {eq['total_trail_compression_front_mm']} มม. | Rake ตอนเบรกเลี้ยว: {eq['dynamic_rake_brake_mm']} มม.)"
        )

    if telem.get('tire_wear_analysis'):
        tw = telem['tire_wear_analysis']
        lines.append(
            f"• การวิเคราะห์การสึกหรอของยาง (Tire Wear Index): หน้า {tw['front_wear_factor']}x | หลัง {tw['rear_wear_factor']}x (สัดส่วนความสึกหรอ หลัง/หน้า: {tw['relative_rear_bias']})"
        )

    lines.extend([
        '─' * 86,
        f"{'ค่าปรับตั้ง (GT7 ภาษาไทย)':<35} {'English Menu':<22} {'หน้า (Front)':<14} {'หลัง (Rear)':<14}",
        '─' * 86,
    ])

    rh = params.get('ride_height_mm', {})
    rh_str_f = f"{rh.get('front')}" + (f" [{rh.get('range_f')}]" if 'range_f' in rh else (f" [{rh.get('range')}]" if 'range' in rh else ""))
    rh_str_r = f"{rh.get('rear')}" + (f" [{rh.get('range_r')}]" if 'range_r' in rh else (f" [{rh.get('range')}]" if 'range' in rh else ""))
    lines.append(f"{'ความสูงของตัวรถ (มม.)':<35} {'Body Height (mm)':<22} {rh_str_f:<14} {rh_str_r:<14}")

    nf = params.get('natural_frequency_hz', {})
    nf_str_f = f"{nf.get('front'):.2f}" + (f" [{nf.get('range_f')}]" if 'range_f' in nf else "")
    nf_str_r = f"{nf.get('rear'):.2f}" + (f" [{nf.get('range_r')}]" if 'range_r' in nf else "")
    lines.append(f"{'ความถี่ธรรมชาติ (Hz)':<35} {'Natural Freq (Hz)':<22} {nf_str_f:<14} {nf_str_r:<14}")

    arb = params.get('anti_roll_bar', {})
    lines.append(f"{'เหล็กกันโคลง (1-10)':<35} {'Anti-Roll Bar':<22} {str(arb.get('front')):<14} {str(arb.get('rear')):<14}")

    dc = params.get('damping_compression_pct', {})
    lines.append(f"{'อัตราการยุบตัวโช้ค (%)':<35} {'Damping Comp (%)':<22} {str(dc.get('front')):<14} {str(dc.get('rear')):<14}")

    de = params.get('damping_expansion_pct', {})
    lines.append(f"{'อัตราการคืนตัวโช้ค (%)':<35} {'Damping Exp (%)':<22} {str(de.get('front')):<14} {str(de.get('rear')):<14}")

    cam = params.get('camber_deg', {})
    lines.append(f"{'มุมแคมเบอร์ลบ (องศา °)':<35} {'Negative Camber':<22} {f'{cam.get('front'):.1f}':<14} {f'{cam.get('rear'):.1f}':<14}")

    toe = params.get('toe_angle', {})
    lines.append(f"{'มุมโท (In / Out °)':<35} {'Toe Angle':<22} {str(toe.get('front')):<14} {str(toe.get('rear')):<14}")

    df = params.get('downforce', {})
    if df:
        df_f = f"{df.get('front')}" + (f" [{df.get('range_f')}]" if 'range_f' in df else "")
        df_r = f"{df.get('rear')}" + (f" [{df.get('range_r')}]" if 'range_r' in df else "")
        lines.append(f"{'แรงกดอากาศพลศาสตร์':<35} {'Downforce':<22} {df_f:<14} {df_r:<14}")

    lines.append('─' * 86)

    lsd_r = params.get('lsd_rear')
    lsd_f = params.get('lsd_front')
    is_ff = (car.get('drivetrain') == 'FF')
    if lsd_r or lsd_f:
        f_init = str(lsd_f.get('init')) if lsd_f else '-'
        r_init = '-' if is_ff else (str(lsd_r.get('init')) if lsd_r else '-')
        f_accel = str(lsd_f.get('accel')) if lsd_f else '-'
        r_accel = '-' if is_ff else (str(lsd_r.get('accel')) if lsd_r else '-')
        f_brake = str(lsd_f.get('brake')) if lsd_f else '-'
        r_brake = '-' if is_ff else (str(lsd_r.get('brake')) if lsd_r else '-')
        lines.append(f"{'LSD ทอร์กเริ่มต้น (0-30)':<35} {'LSD Initial Torque':<22} {f_init:<14} {r_init:<14}")
        lines.append(f"{'LSD ความไวการเร่ง (0-100)':<35} {'LSD Accel Sens':<22} {f_accel:<14} {r_accel:<14}")
        lines.append(f"{'LSD ความไวการเบรก (0-100)':<35} {'LSD Braking Sens':<22} {f_brake:<14} {r_brake:<14}")
        lines.append('─' * 86)

    if params.get('awd_torque_split'):
        lines.append(f"• การกระจายแรงบิด AWD (Front:Rear): {params.get('awd_torque_split')}")
    lines.append(f"• ตัวควบคุมสมดุลเบรก (Brake Balance Controller): {params.get('brake_bias')} (หน้า + / หลัง -)")
    lines.append(f"• ความเร็วสูงสุดอัตโนมัติ (Auto-set Top Speed): {params.get('transmission_top_speed_kmh')} km/h (เกียร์แข่ง Fully Customisable)")

    notes = params.get('endurance_notes', [])
    if notes:
        lines.append('─' * 86)
        lines.append("🏁 คำแนะนำทางวิศวกรรม & กลยุทธ์การแข่ง (Engineering & Racecraft Notes):")
        for n in notes:
            lines.append(f"  {n}")

    qt = params.get('quick_trims')
    if qt:
        lines.append('─' * 86)
        lines.append("⚡ QUICK-TRIMS DELTA TABLE (โหมดปรับด่วน: ถนอมยาง & เน้นความนิ่ง - Section 2.F):")
        ts = qt.get('tire_saver', {})
        lines.append(f"• [Tire-Saver Spec / โหมดถนอมยาง]:")
        lines.append(f"  สปริง: {ts.get('natural_frequency_hz')} | แคมเบอร์: {ts.get('negative_camber')} | โท: {ts.get('toe_angle')} | LSD Accel: {ts.get('lsd_accel')}")
        lines.append(f"  ↳ {ts.get('description')}")

        ms = qt.get('max_stability', {})
        lines.append(f"• [Max Stability Spec / โหมดเน้นความนิ่ง]:")
        lines.append(f"  ARB: {ms.get('anti_roll_bar')} | หลัง Rebound: {ms.get('damping_expansion_rear')} | โทหลัง: {ms.get('rear_toe_in')} | LSD Brake: {ms.get('lsd_braking_sens')} | สมดุลเบรก: {ms.get('brake_bias')}")
        lines.append(f"  ↳ {ms.get('description')}")

    lines.append('=' * 86)
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description="GT7 First-Principles Race-Engineering Auto-Tuner")
    parser.add_argument('car', help="Car name or ID from GT7 database")
    parser.add_argument('-t', '--track', help="Target track name or ID")
    parser.add_argument('--tire', default='SS', choices=['CH','CM','CS','SH','SM','SS','RH','RM','RS','Dirt','Wet'])
    parser.add_argument('--mass', type=int)
    parser.add_argument('--power', type=int)
    parser.add_argument('--torque', type=float)
    parser.add_argument('--drivetrain', choices=['FF','FR','MR','RR','AWD','4WD','4x4'])
    parser.add_argument('--balance', type=int, nargs=2, metavar=('FRONT', 'REAR'))
    parser.add_argument('--mode', default='grip', choices=['grip','time_attack','wet','dirt','drift','endurance'])
    parser.add_argument('--df-front', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--df-rear', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--height-range', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--height-front', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--height-rear', type=int, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--fn-front', type=float, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--fn-rear', type=float, nargs=2, metavar=('MIN', 'MAX'))
    parser.add_argument('--save-sliders', action='store_true')
    parser.add_argument('--stability', type=float, nargs=2, metavar=('LOW', 'HIGH'))
    parser.add_argument('--symptom', nargs='+', choices=['entry_push','exit_snap','bottoming','curb_hop'])
    parser.add_argument('--widebody', action='store_true')
    parser.add_argument('--speed', type=float)
    parser.add_argument('--json', action='store_true')

    args = parser.parse_args()

    car_data = get_car(args.car)
    if not car_data:
        car_data = {'name': args.car, 'mass_kg': args.mass or 1350, 'drivetrain': args.drivetrain or 'FR'}

    track_data = get_track(args.track) if args.track else None

    if args.save_sliders and car_data.get('id'):
        new_sliders = {}
        if args.df_front: new_sliders['df_front'] = list(args.df_front)
        if args.df_rear: new_sliders['df_rear'] = list(args.df_rear)
        if args.height_range: new_sliders['height_range'] = list(args.height_range)
        if args.height_front: new_sliders['height_front'] = list(args.height_front)
        if args.height_rear: new_sliders['height_rear'] = list(args.height_rear)
        if args.fn_front: new_sliders['fn_front'] = list(args.fn_front)
        if args.fn_rear: new_sliders['fn_rear'] = list(args.fn_rear)
        save_car_sliders(str(car_data['id']), new_sliders)

    res = setup.build_setup(
        car=car_data,
        track=track_data,
        tire=args.tire,
        custom_mass=args.mass,
        custom_power=args.power,
        custom_torque=args.torque,
        custom_drivetrain=args.drivetrain,
        custom_balance=args.balance,
        mode=args.mode,
        df_front_range=args.df_front,
        df_rear_range=args.df_rear,
        height_range=args.height_range,
        height_front_range=args.height_front,
        height_rear_range=args.height_rear,
        fn_front_range=args.fn_front,
        fn_rear_range=args.fn_rear,
        stability=args.stability,
        symptoms=args.symptom,
        is_widebody=args.widebody,
        speed_kmh=args.speed
    )

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(format_setup_sheet(res))

if __name__ == '__main__':
    main()
