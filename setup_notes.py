#!/usr/bin/env python3
"""
GT7 Engineering Notes & Strategy Generator
Compiles engineering advice, setup warnings, and racecraft notes based on vehicle specs and physics proofs.
"""

from typing import List, Tuple, Optional, Any, Dict
from models import VehicleSpec, TrackSpec


def _append_tire_and_endurance_notes(notes: List[str], trk: TrackSpec, tire: str, fn_f: float) -> None:
    """Append endurance racecraft and sports tire compliance notes."""
    if trk.is_endurance:
        notes.append("• [Tire Conservation] เซ็ตติ้งเน้นถนอมยาง: ลดมุม Camber และ Toe เพื่อลดการกินขอบยางด้านในและตัดการไถลากบนทางตรงยาว พร้อมลดสปริงเรทลงเพื่อลดความร้อนสะสมในเนื้อยาง")
        notes.append("• [PP Optimization Meta (Update 1.71/1.72)] แนะนำถอดเบรกเรซซิ่ง (Racing Brakes) ออกแล้วใช้เบรก Normal/Sport + ผ้าเบรก Racing และถอด Clutch Kit กับ Anti-Lag ออก ช่วยประหยัดแต้ม PP นำไปเพิ่มแรงม้าได้ +50-80 HP")
    if tire in ['SH', 'SM', 'SS'] and fn_f >= 2.85:
        notes.append("• [Sports Tire Compliance Guard] วิ่งยางสปอร์ต (Sports Tires) ห้ามใช้สปริงแข็งระดับ 3.0 Hz ของยางเรซซิ่ง เพราะจะลื่นเหมือนขับบนน้ำแข็ง (เข้าดื้อ-ออกปัด)")


def generate_chassis_notes(
    veh: VehicleSpec, trk: TrackSpec, tire: str,
    fn_f: float, is_no_aero: bool, is_controller: bool, is_widebody: bool
) -> List[str]:
    """Generate chassis, aero, and drivetrain engineering recommendations."""
    notes = []
    if is_controller:
        notes.append("• [Controller / DualSense Setup] ปรับ LSD Braking แน่น (80-100) เพื่อคุมเสถียรภาพตอนแตะเบรกเลี้ยว (แก้ Braking Instability บนยางเรซซิ่งตามฟิสิกส์ 1.71+) และเพิ่มระยะยุบหน้ารถกันระบบ Invisible Steering Limiter ล็อคมุมเลี้ยวในโค้งแบงค์")
    if is_no_aero:
        notes.append("• [No-Aero High Rake / Derpy Tune] รถไม่มีพาร์ทแอโร่บนยางเรซซิ่ง: ยกท้ายสูง (+20 ถึง +25 มม.) สร้างแรงกดเทียม (Rake Downforce) ลดอาการร่อนส่ายที่ความเร็วสูง")
    if is_widebody:
        notes.append("• [Widebody Clearance] เพิ่มระยะยุบตัวซุ้มล้อหน้า +5 มม. เพื่อป้องกันหน้ายางขัดกับซุ้มล้อ (Fender Scrub) ขณะแตะเบรกลึก")
    _append_tire_and_endurance_notes(notes, trk, tire, fn_f)
    _append_drivetrain_notes(notes, veh, is_controller)
    return notes


def _append_drivetrain_notes(notes: List[str], veh: VehicleSpec, is_controller: bool) -> None:
    """Append drivetrain-specific stability and balance recommendations."""
    if veh.drivetrain in ['MR', 'RR'] and veh.group == 'Road Car':
        notes.append("• [MR/RR Balance (Update 1.71)] ปรับ Downforce หลังมากกว่าหน้า ~100 จุด (เช่น หน้า 150 / หลัง 250) และเพิ่ม Ballast หน้า (-50 position, 20-50 kg) เพื่อตัดอาการหน้าไวสะบัดหมุน (Liftoff Snap-Oversteer)")
    if veh.front_weight_ratio >= 0.55 and veh.drivetrain == 'FR':
        if not is_controller:
            notes.append("• [Anti-Understeer] ปลดล็อค LSD Braking = 22-26 (บนสเกล 0-100) และ ARB หน้าอ่อน/หลังแข็ง เพื่อให้ท้ายช่วยหมุนเข้าเอเปกซ์")
        if any(yr in veh.name for yr in ["'6", "'7", "196", "197"]):
            notes.append("• [CRITICAL WARNING] ห้ามติดตั้ง Steering Angle Adapter (ตัวปรับมุมเลี้ยว) สำหรับวิ่งกริป! มันเป็นอะไหล่ดริฟต์ที่ลบ Ackermann geometry ทำให้ล้อหน้าไถต้านกันและดื้อโค้งสนิทเมื่อแตะเบรก")
            notes.append("• [Driving Assists] ปิด ASM (Active Stability Management) และ Countersteering Assistance เป็น OFF เพื่อให้ทำ Trail Braking ได้")
            notes.append("• [Chassis Rigidity] ติดตั้ง Roll Cage (โรลเคจ) ใน GT Auto เพื่อลดการบิดตัวของโครงสร้างตัวถังยุคคลาสสิก")
    elif veh.drivetrain in ['MR', 'RR']:
        notes.append("• [MR/RR Stability] LSD Braking ล็อคแน่น 52-65 (บนสเกล 0-100) ป้องกันอาการท้ายสะบัดหมุน (Snap Oversteer) ขณะแตะเบรกเลี้ยว (Trail-Braking)")
    if veh.group == 'Gr.4' and veh.drivetrain in ['AWD', '4WD', '4x4']:
        notes.append("• [Gr.4 AWD Center Diff] รถแข่ง Gr.4 ขับเคลื่อน 4 ล้อ (AWD/4WD) ล็อค Center Diff จากโรงงาน ไม่สามารถติดตั้งหรือปรับ Torque-Distributing Center Diff ได้ (Fixed Homologation)")
        notes.append("  ↳ วิธีแก้หน้าดื้อ: ให้คลาย LSD ล้อหน้าให้อ่อน (Accel 14-16 / Braking 18-20), ปรับ ARB หน้าอ่อน/หลังแข็ง (3/7 หรือ 2/8), ปรับสมดุลเบรกไปหลัง (-2), และใช้ Front Toe-Out ช่วยดึงหน้ารถเข้าโค้ง")


def generate_simulation_notes(
    sim: Dict[str, Any],
    eq_proof: Dict[str, Any],
    speed_kmh: float
) -> List[str]:
    """Generate dynamic compliance verification and bottoming warning notes."""
    notes = []
    if sim['bottoming_or_fender_hit']:
        bump = sim['recommended_front_rh_bump_mm']
        comp = sim['total_outside_front_compression_mm']
        notes.append(f"⚠️ [Bottoming/Fender Guard] ตรวจพบความเสี่ยงล้อหน้ากระแทกซุ้มล้อ/Bump Stop ที่ความเร็ว {speed_kmh:.0f} km/h (ยุบรวม {comp} มม.) -> แนะนำยกหน้าขึ้น +{bump} มม.")

    clearance = eq_proof['min_dynamic_clearance_mm']
    if not eq_proof['trail_braking_feasible']:
        boost = eq_proof['recommended_front_fn_boost_hz']
        notes.append(f"⚠️ [Trail-Braking Compliance Warning] ยุบตัวล้อหน้าระหว่างแตะเบรกเลี้ยวลึก (Trail-Braking) เสี่ยงกระแทก Bump Stop เหลือระยะเพียง {clearance} มม. -> แนะนำเพิ่มสปริงหน้า +{boost} Hz หรือยกหน้าขึ้น")
    else:
        notes.append(f"✅ [Trail-Braking Physical Proof] ผ่านการทดสอบฟิสิกส์: มีระยะยุบตัวเหลือ {clearance} มม. ขณะแตะเบรกเลี้ยวที่ {speed_kmh:.0f} km/h (ไม่กระแทก Bump Stop)")
    return notes


def generate_trim_notes(
    stability: Optional[Tuple[float, float]],
    symptoms: Optional[List[str]]
) -> List[str]:
    """Generate notes indicating applied closed-loop and symptom trims."""
    notes = []
    if stability:
        notes.append(f"• [Closed-Loop Stability Trim] ปรับจูนชดเชยค่าความเสถียร (Stability Index: Low {stability[0]}, High {stability[1]})")
    if symptoms:
        notes.append(f"• [Symptom Trim] ปรับจูนแก้อาการขับขี่: {', '.join(symptoms)}")
    return notes
