#!/usr/bin/env python3
"""
GT7 Setup Sheet Formatter
Renders dual English/Thai setup sheets and formatted physical telemetry.
"""

from typing import Dict, Any, List


def _format_header(car: Dict[str, Any], track: Any, tire: str, mode: str) -> List[str]:
    """Render setup sheet top banner and vehicle target header."""
    t_name = track['name'] if track else 'General Balanced Circuit'
    mass = car.get('mass_kg', 'N/A')
    balance_str = car.get('balance', {}).get('ratio_str', 'N/A')
    return [
        '=' * 86,
        '🏎️  GT7 FIRST-PRINCIPLES SUSPENSION & CHASSIS SETUP SHEET (Update 1.72+ Spec IV)',
        f"Target Car:   {car.get('name')} [{car.get('drivetrain')}, {mass} kg, {balance_str}]",
        f"Target Track: {t_name} | Tire: {tire} | Mode: {mode.upper()}",
        '=' * 86,
    ]


def _format_dynamic_g_lines(telem: Dict[str, Any]) -> List[str]:
    """Format dynamic cornering G and aero downforce scaling table."""
    dyn_g, prof = telem.get('dynamic_g_force'), telem.get('downforce_g_profile')
    if not dyn_g or not prof:
        return []
    df = dyn_g['downforce']
    min_a, max_a = prof['min_aero'], prof['max_aero']
    min_f, min_r = min_a['downforce']['front'], min_a['downforce']['rear']
    max_f, max_r = max_a['downforce']['front'], max_a['downforce']['rear']
    lines = [
        f"• แรงเหวี่ยง G ตามแรงกดแอร์โร (Dynamic G @ DF {df['front']}/{df['rear']}): 60 km/h = {dyn_g['g_60']:.2f}G | 120 km/h = {dyn_g['g_120']:.2f}G | 240 km/h = {dyn_g['g_240']:.2f}G"
    ]
    if (min_f, min_r) != (max_f, max_r) and (max_f > 0 or max_r > 0):
        lines.append(
            f"  ↳ เทียบสเกลแรงกด (240 km/h G vs Aero): Min DF ({min_f}/{min_r}) = {min_a['g_240']:.2f}G | Setup DF ({df['front']}/{df['rear']}) = {dyn_g['g_240']:.2f}G | Max DF ({max_f}/{max_r}) = {max_a['g_240']:.2f}G"
        )
    return lines


def _format_telemetry(telem: Dict[str, Any]) -> List[str]:
    """Format derived physical telemetry metrics."""
    lines = [
        '📊 พารามิเตอร์ทางกายภาพที่คำนวณได้จาก First Principles (Derived Physical Telemetry):',
        f"• น้ำหนัก Sprung Mass: รวม {telem.get('mass_sprung_total_kg')} kg (มุมหน้า: {telem.get('mass_sprung_corner_f_kg')} kg | มุมหลัง: {telem.get('mass_sprung_corner_r_kg')} kg)",
        f"• สัมประสิทธิ์กริปยาง (μ): {telem.get('tire_friction_mu')} | แรงเหวี่ยงสูงสุดโดยประมาณ: {telem.get('lateral_g_capacity')} G",
        f"• เป้าหมายการถ่ายเทน้ำหนักขณะเลี้ยว (Target Front LLTD): {telem.get('target_lltd_front_pct')}% (คุมบาลานซ์เลี้ยวเข้าเอเปกซ์)",
        f"• อัตราส่วน Flat Ride (หลัง/หน้า): {telem.get('flat_ride_frequency_ratio')} (ซิงค์จังหวะยุบ-คืนตัวข้ามเนินและผิวขรุขระ)",
        f"• แรงถ่ายเทน้ำหนักขณะเบรก (Braking Load Transfer): +{telem.get('dynamic_braking_pitch_transfer_pct')}% ถ่ายไปล้อหน้า",
    ]
    lines.extend(_format_dynamic_g_lines(telem))
    return lines


def _format_trail_sim_lines(sim: Dict[str, Any]) -> List[str]:
    """Format high-speed trail-braking simulation lines."""
    sym = '⚠️ เสี่ยงกระแทกซุ้มล้อ/Bump Stop' if sim['bottoming_or_fender_hit'] else '✅ ปลอดภัย (มีระยะยุบเหลือ)'
    comp = sim['total_outside_front_compression_mm']
    clr = sim['dynamic_outside_front_clearance_mm']
    rake = sim['dynamic_rake_mm']
    return [
        f"• จำลองการยุบตัวล้อหน้านอกโค้งขณะ Trail-Braking ที่ {sim['speed_kmh']} km/h: {sym}",
        f"  ↳ แรงกดแอร์โร: {sim['aero_compression_mm']['front']} มม. | แรงทิ่มเบรก: {sim['pitch_compression_front_mm']} มม. | แรงเอียงเลี้ยว: {sim['roll_compression_front_mm']} มม. (ยุบรวม {comp} มม. | ระยะเหลือ {clr} มม. | Rake ขณะวิ่ง {rake} มม.)"
    ]


def _format_equilibrium_lines(eq: Dict[str, Any]) -> List[str]:
    """Format suspension equilibrium proof lines."""
    status = '✅ ผ่าน (Compliance Pass)' if eq['trail_braking_feasible'] else '⚠️ เสี่ยง Bump Stop (Compliance Warn)'
    return [
        f"• สมดุลฟิสิกส์ Trail-Braking & ทอร์กส่งกำลัง (Equilibrium Proof): {status}",
        f"  ↳ แรงบิดกดท้าย (Acceleration Squat): {eq['acceleration_squat_rear_mm']} มม. | หน้าลอย (Lift): {eq['acceleration_lift_front_mm']} มม. | Rake ตอนกดคันเร่ง: {eq['dynamic_rake_accel_mm']} มม.",
        f"  ↳ ระยะยุบเหลือขณะ Trail-Braking: {eq['min_dynamic_clearance_mm']} มม. (ยุบรวม {eq['total_trail_compression_front_mm']} มม. | Rake ตอนเบรกเลี้ยว: {eq['dynamic_rake_brake_mm']} มม.)"
    ]


def _format_simulation_proofs(telem: Dict[str, Any]) -> List[str]:
    """Format high-speed trail braking simulation, equilibrium proof, and tire wear analysis."""
    lines = []
    if telem.get('high_speed_simulation'):
        lines.extend(_format_trail_sim_lines(telem['high_speed_simulation']))
    if telem.get('equilibrium_proof'):
        lines.extend(_format_equilibrium_lines(telem['equilibrium_proof']))
    if telem.get('tire_wear_analysis'):
        tw = telem['tire_wear_analysis']
        lines.append(f"• การวิเคราะห์การสึกหรอของยาง (Tire Wear Index): หน้า {tw['front_wear_factor']}x | หลัง {tw['rear_wear_factor']}x (สัดส่วนความสึกหรอ หลัง/หน้า: {tw['relative_rear_bias']})")
    return lines


def _format_damper_alignment_rows(params: Dict[str, Any]) -> List[str]:
    """Format damper, camber, toe, and aero rows for table."""
    dc, de = params.get('damping_compression_pct', {}), params.get('damping_expansion_pct', {})
    cam, toe, df = params.get('camber_deg', {}), params.get('toe_angle', {}), params.get('downforce', {})
    rows = [
        f"{'อัตราการยุบตัวโช้ค (%)':<35} {'Damping Comp (%)':<22} {str(dc.get('front')):<14} {str(dc.get('rear')):<14}",
        f"{'อัตราการคืนตัวโช้ค (%)':<35} {'Damping Exp (%)':<22} {str(de.get('front')):<14} {str(de.get('rear')):<14}",
        f"{'มุมแคมเบอร์ลบ (องศา °)':<35} {'Negative Camber':<22} {f'{cam.get('front'):.1f}':<14} {f'{cam.get('rear'):.1f}':<14}",
        f"{'มุมโท (In / Out °)':<35} {'Toe Angle':<22} {str(toe.get('front')):<14} {str(toe.get('rear')):<14}",
    ]
    if df:
        df_f = f"{df.get('front')}" + (f" [{df.get('range_f')}]" if 'range_f' in df else "")
        df_r = f"{df.get('rear')}" + (f" [{df.get('range_r')}]" if 'range_r' in df else "")
        rows.append(f"{'แรงกดอากาศพลศาสตร์':<35} {'Downforce':<22} {df_f:<14} {df_r:<14}")
    rows.append('─' * 86)
    return rows


def _format_suspension_table(params: Dict[str, Any]) -> List[str]:
    """Format core suspension tuning parameters table."""
    rh, nf, arb = params.get('ride_height_mm', {}), params.get('natural_frequency_hz', {}), params.get('anti_roll_bar', {})
    rh_f = f"{rh.get('front')}" + (f" [{rh.get('range_f')}]" if 'range_f' in rh else (f" [{rh.get('range')}]" if 'range' in rh else ""))
    rh_r = f"{rh.get('rear')}" + (f" [{rh.get('range_r')}]" if 'range_r' in rh else (f" [{rh.get('range')}]" if 'range' in rh else ""))
    nf_f = f"{nf.get('front'):.2f}" + (f" [{nf.get('range_f')}]" if 'range_f' in nf else "")
    nf_r = f"{nf.get('rear'):.2f}" + (f" [{nf.get('range_r')}]" if 'range_r' in nf else "")
    lines = [
        '─' * 86,
        f"{'ค่าปรับตั้ง (GT7 ภาษาไทย)':<35} {'English Menu':<22} {'หน้า (Front)':<14} {'หลัง (Rear)':<14}",
        '─' * 86,
        f"{'ความสูงของตัวรถ (มม.)':<35} {'Body Height (mm)':<22} {rh_f:<14} {rh_r:<14}",
        f"{'ความถี่ธรรมชาติ (Hz)':<35} {'Natural Freq (Hz)':<22} {nf_f:<14} {nf_r:<14}",
        f"{'เหล็กกันโคลง (1-10)':<35} {'Anti-Roll Bar':<22} {str(arb.get('front')):<14} {str(arb.get('rear')):<14}",
    ]
    lines.extend(_format_damper_alignment_rows(params))
    return lines


def _format_lsd_and_drivetrain(params: Dict[str, Any], car: Dict[str, Any]) -> List[str]:
    """Format LSD settings, brake balance, and transmission."""
    lines = []
    lsd_r, lsd_f, is_ff = params.get('lsd_rear'), params.get('lsd_front'), (car.get('drivetrain') == 'FF')
    if lsd_r or lsd_f:
        f_i, r_i = str(lsd_f.get('init')) if lsd_f else '-', '-' if is_ff else str(lsd_r.get('init'))
        f_a, r_a = str(lsd_f.get('accel')) if lsd_f else '-', '-' if is_ff else str(lsd_r.get('accel'))
        f_b, r_b = str(lsd_f.get('brake')) if lsd_f else '-', '-' if is_ff else str(lsd_r.get('brake'))
        lines.append(f"{'LSD ทอร์กเริ่มต้น (0-30)':<35} {'LSD Initial Torque':<22} {f_i:<14} {r_i:<14}")
        lines.append(f"{'LSD ความไวการเร่ง (0-100)':<35} {'LSD Accel Sens':<22} {f_a:<14} {r_a:<14}")
        lines.append(f"{'LSD ความไวการเบรก (0-100)':<35} {'LSD Braking Sens':<22} {f_b:<14} {r_b:<14}")
        lines.append('─' * 86)
    if params.get('awd_torque_split'):
        lines.append(f"• การกระจายแรงบิด AWD (Front:Rear): {params.get('awd_torque_split')}")
    lines.append(f"• ตัวควบคุมสมดุลเบรก (Brake Balance Controller): {params.get('brake_bias')} (หน้า + / หลัง -)")
    lines.append(f"• ความเร็วสูงสุดอัตโนมัติ (Auto-set Top Speed): {params.get('transmission_top_speed_kmh')} km/h (เกียร์แข่ง Fully Customisable)")
    return lines


def _format_quick_trim_details(qt: Dict[str, Any]) -> List[str]:
    """Format individual quick-trim section rows."""
    ts, ms = qt.get('tire_saver', {}), qt.get('max_stability', {})
    return [
        '─' * 86,
        "⚡ QUICK-TRIMS DELTA TABLE (โหมดปรับด่วน: ถนอมยาง & เน้นความนิ่ง - Section 2.F):",
        "• [Tire-Saver Spec / โหมดถนอมยาง]:",
        f"  สปริง: {ts.get('natural_frequency_hz')} | แคมเบอร์: {ts.get('negative_camber')} | โท: {ts.get('toe_angle')} | LSD Accel: {ts.get('lsd_accel')}",
        f"  ↳ {ts.get('description')}",
        "• [Max Stability Spec / โหมดเน้นความนิ่ง]:",
        f"  ARB: {ms.get('anti_roll_bar')} | หลัง Rebound: {ms.get('damping_expansion_rear')} | โทหลัง: {ms.get('rear_toe_in')} | LSD Brake: {ms.get('lsd_braking_sens')} | สมดุลเบรก: {ms.get('brake_bias')}",
        f"  ↳ {ms.get('description')}"
    ]


def _format_notes_and_quick_trims(params: Dict[str, Any]) -> List[str]:
    """Format engineering notes and Section 2.F quick-trims table."""
    lines = []
    notes = params.get('endurance_notes', [])
    if notes:
        lines.extend(['─' * 86, "🏁 คำแนะนำทางวิศวกรรม & กลยุทธ์การแข่ง (Engineering & Racecraft Notes):"])
        lines.extend(f"  {n}" for n in notes)
    if params.get('quick_trims'):
        lines.extend(_format_quick_trim_details(params['quick_trims']))
    return lines


def format_setup_sheet(setup_dict: Dict[str, Any]) -> str:
    """Format setup into dual English/Thai GT7 tuning sheet."""
    car, params = setup_dict['car'], setup_dict['parameters']
    telem, track = setup_dict.get('telemetry', {}), setup_dict.get('track')
    sections = [
        _format_header(car, track, setup_dict['tire_compound'], setup_dict['setup_mode']),
        _format_telemetry(telem),
        _format_simulation_proofs(telem),
        _format_suspension_table(params),
        _format_lsd_and_drivetrain(params, car),
        _format_notes_and_quick_trims(params),
        ['=' * 86]
    ]
    return '\n'.join(line for sec in sections for line in sec)
