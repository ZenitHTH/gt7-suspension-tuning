"""SetupForm — left-pane input form (Tasks 4-5).

Picking a car prefills everything derivable from the DB; `collect()` reads
all panels into a fully-populated `GuiRequest`; `validate()` runs
`service.validate()` and renders errors/warnings into the status label.
"""
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from db.interface import TRACKS_DB
from gui.components import RangePair
from gui.request import (
    DRIVETRAINS,
    MODES,
    SOLVE_OBJECTIVES,
    SYMPTOMS,
    TIRE_COMPOUNDS,
    GuiRequest,
)
from gui.service import TuningService

_STATUS_KINDS = ('ok', 'warn', 'error')

# Human display names for the six SYMPTOMS keys (checkbox labels).
_SYMPTOM_DISPLAY = {
    'entry_push': 'Entry push / understeer',
    'exit_snap': 'Exit snap / oversteer',
    'bottoming': 'Bottoming',
    'curb_hop': 'Curb hop',
    'front_tire_wear': 'Front tire wear',
    'rear_tire_wear': 'Rear tire wear',
}


class SetupForm(QWidget):
    """All input panels; `collect()` → partial `GuiRequest` (Task 4 subset)."""

    def __init__(self, service: TuningService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.service = service
        self._current_car: Optional[Dict[str, Any]] = None

        root = QVBoxLayout(self)

        # ---- Vehicle group ------------------------------------------------
        vehicle_group = QGroupBox('Vehicle')
        vlayout = QVBoxLayout(vehicle_group)

        self.car_search = QLineEdit()
        self.car_search.setPlaceholderText('Search cars by name, maker or ID')
        self.car_search.textChanged.connect(self._refill_cars)
        vlayout.addWidget(self.car_search)

        self.car_combo = QComboBox()
        self.car_combo.currentIndexChanged[int].connect(self._on_car_index_changed)
        vlayout.addWidget(self.car_combo)

        swap_row = QHBoxLayout()
        swap_hint = QLabel('Engine swap')
        swap_hint.setObjectName('hintLabel')
        swap_row.addWidget(swap_hint)
        self.swap_combo = QComboBox()
        self.swap_combo.currentIndexChanged[int].connect(self._on_swap_index_changed)
        swap_row.addWidget(self.swap_combo)
        vlayout.addLayout(swap_row)

        self.db_info_label = QLabel()
        self.db_info_label.setObjectName('dbInfoLabel')  # theme: secondary 12px
        self.db_info_label.setWordWrap(True)
        self.db_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        vlayout.addWidget(self.db_info_label)

        root.addWidget(vehicle_group)

        # ---- Tire group ---------------------------------------------------
        tire_group = QGroupBox('Tire compound')
        tlayout = QHBoxLayout(tire_group)
        tire_hint = QLabel('Compound')
        tire_hint.setObjectName('hintLabel')
        tlayout.addWidget(tire_hint)
        self.tire_combo = QComboBox()
        for compound in TIRE_COMPOUNDS:
            self.tire_combo.addItem(compound, compound)
        self.tire_combo.setCurrentIndex(self.tire_combo.findText('SS'))
        tlayout.addWidget(self.tire_combo)
        root.addWidget(tire_group)

        # ---- Slider ranges group -----------------------------------------
        ranges_group = QGroupBox('In-game slider ranges')
        rlayout = QVBoxLayout(ranges_group)
        # max_v 2000: preseeded DF ranges in the DB reach 1700 (cars
        # 3342/3374/3517); the old 1000 cap silently clamped prefills.
        self.df_f = RangePair('DF front', kind='int', max_v=2000)
        self.df_r = RangePair('DF rear', kind='int', max_v=2000)
        self.hf = RangePair('Height front', kind='int', max_v=400)
        self.hr = RangePair('Height rear', kind='int', max_v=400)
        self.fn_f = RangePair('Nat freq front', kind='float', max_v=10.0)
        self.fn_r = RangePair('Nat freq rear', kind='float', max_v=10.0)
        for pair in (self.df_f, self.df_r, self.hf, self.hr, self.fn_f, self.fn_r):
            rlayout.addWidget(pair)
        r_hint = QLabel('0/0 = use saved/preseeded DB values')
        r_hint.setObjectName('hintLabel')
        rlayout.addWidget(r_hint)
        self.save_ranges_btn = QPushButton('Save ranges to DB')
        self.save_ranges_btn.clicked.connect(self._on_save_ranges)
        rlayout.addWidget(self.save_ranges_btn)
        root.addWidget(ranges_group)

        # ---- Overrides group ---------------------------------------------
        overrides_group = QGroupBox('Build overrides')
        olayout = QVBoxLayout(overrides_group)

        self.mass_use_db = QCheckBox('Mass (use DB)')
        self.mass_use_db.setChecked(True)
        mass_row = QHBoxLayout()
        mass_row.addWidget(self.mass_use_db)
        mass_row.addWidget(QLabel('or custom mass (kg)'))
        self.mass_spin = QSpinBox()
        self.mass_spin.setRange(0, 3000)
        mass_row.addWidget(self.mass_spin)
        olayout.addLayout(mass_row)

        self.power_use_db = QCheckBox('Power (use DB)')
        self.power_use_db.setChecked(True)
        power_row = QHBoxLayout()
        power_row.addWidget(self.power_use_db)
        power_row.addWidget(QLabel('or custom power (hp)'))
        self.power_spin = QSpinBox()
        self.power_spin.setRange(0, 3000)
        power_row.addWidget(self.power_spin)
        olayout.addLayout(power_row)

        self.torque_use_db = QCheckBox('Torque (use DB)')
        self.torque_use_db.setChecked(True)
        torque_row = QHBoxLayout()
        torque_row.addWidget(self.torque_use_db)
        torque_row.addWidget(QLabel('or custom torque (Nm)'))
        self.torque_spin = QDoubleSpinBox(decimals=1)
        self.torque_spin.setRange(0.0, 1500.0)
        torque_row.addWidget(self.torque_spin)
        olayout.addLayout(torque_row)

        self.balance_use_db = QCheckBox('Weight balance (use DB)')
        self.balance_use_db.setChecked(True)
        balance_row = QHBoxLayout()
        balance_row.addWidget(self.balance_use_db)
        balance_row.addWidget(QLabel('or front % / rear %'))
        self.bal_f_spin = QSpinBox()
        self.bal_f_spin.setRange(0, 100)
        self.bal_r_spin = QSpinBox()
        self.bal_r_spin.setRange(0, 100)
        balance_row.addWidget(self.bal_f_spin)
        balance_row.addWidget(self.bal_r_spin)
        olayout.addLayout(balance_row)

        drivetrain_row = QHBoxLayout()
        dt_hint = QLabel('Drivetrain')
        dt_hint.setObjectName('hintLabel')
        drivetrain_row.addWidget(dt_hint)
        self.drivetrain_combo = QComboBox()
        for dt in DRIVETRAINS:
            self.drivetrain_combo.addItem(dt, dt)
        drivetrain_row.addWidget(self.drivetrain_combo)
        olayout.addLayout(drivetrain_row)

        root.addWidget(overrides_group)

        # ---- Calibration / Session / Symptoms groups (Task 5) -------------
        self._build_calibration_group(root)
        self._build_session_group(root)
        self._build_symptoms_group(root)

        # ---- Status label --------------------------------------------------
        self.status_label = QLabel()
        self.status_label.setObjectName('statusLabel')  # theme: ok/warn/error colors
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        # Initial state: full car list; selecting car 0 prefills the form.
        self._refill_cars('')

    # ------------------------------------------------------------------ wiring

    def _on_car_index_changed(self, _index: int) -> None:
        car_id = self.car_combo.currentData()
        if car_id:
            self.on_car_selected(car_id)

    def _on_swap_index_changed(self, _index: int) -> None:
        self._on_swap_selected(self.swap_combo.currentData() or '')

    # ------------------------------------------------------- group builders

    def _build_calibration_group(self, root: QVBoxLayout) -> None:
        group = QGroupBox('Calibration')
        layout = QVBoxLayout(group)

        for attr, text in (('g60_spin', 'G @ 60 km/h'),
                           ('g120_spin', 'G @ 120 km/h'),
                           ('g240_spin', 'G @ 240 km/h')):
            row = QHBoxLayout()
            hint = QLabel(text)
            hint.setObjectName('hintLabel')
            row.addWidget(hint)
            spin = QDoubleSpinBox(decimals=2)
            spin.setRange(0.0, 9.0)
            spin.setSpecialValueText('')
            setattr(self, attr, spin)
            spin.valueChanged.connect(self._update_solve_gate)
            row.addWidget(spin)
            layout.addLayout(row)

        ref_row = QHBoxLayout()
        ref_hint = QLabel('Ref downforce (front / rear)')
        ref_hint.setObjectName('hintLabel')
        ref_row.addWidget(ref_hint)
        self.gref_f_spin = QSpinBox()
        self.gref_f_spin.setRange(0, 1000)
        self.gref_r_spin = QSpinBox()
        self.gref_r_spin.setRange(0, 1000)
        ref_row.addWidget(self.gref_f_spin)
        ref_row.addWidget(self.gref_r_spin)
        layout.addLayout(ref_row)

        solve_row = QHBoxLayout()
        solve_hint = QLabel('Solve')
        solve_hint.setObjectName('hintLabel')
        solve_row.addWidget(solve_hint)
        self.solve_combo = QComboBox()
        self.solve_combo.addItem('—', '')
        for objective in SOLVE_OBJECTIVES:
            self.solve_combo.addItem(objective, objective)
        self.solve_combo.setEnabled(False)  # gated on G-force calibration
        solve_row.addWidget(self.solve_combo)
        layout.addLayout(solve_row)

        hint = QLabel('Measure peak lateral G in-game at 60/120/240 km/h '
                      'and the downforce you were running.')
        hint.setObjectName('hintLabel')
        hint.setWordWrap(True)
        layout.addWidget(hint)

        root.addWidget(group)
        self._update_solve_gate()

    def _build_session_group(self, root: QVBoxLayout) -> None:
        group = QGroupBox('Session')
        layout = QVBoxLayout(group)

        track_row = QHBoxLayout()
        track_hint = QLabel('Track')
        track_hint.setObjectName('hintLabel')
        track_row.addWidget(track_hint)
        self.track_combo = QComboBox()
        self.track_combo.setEditable(True)
        self.track_combo.addItem('— (no track)', '')
        for track in TRACKS_DB:
            self.track_combo.addItem(track['name'], track['id'])
        self.track_combo.setCompleter(QCompleter([t['name'] for t in TRACKS_DB]))
        track_row.addWidget(self.track_combo)
        layout.addLayout(track_row)

        mode_row = QHBoxLayout()
        mode_hint = QLabel('Mode')
        mode_hint.setObjectName('hintLabel')
        mode_row.addWidget(mode_hint)
        self.mode_combo = QComboBox()
        for mode in MODES:
            self.mode_combo.addItem(mode, mode)
        mode_row.addWidget(self.mode_combo)
        layout.addLayout(mode_row)

        speed_row = QHBoxLayout()
        speed_hint = QLabel('Speed (km/h)')
        speed_hint.setObjectName('hintLabel')
        speed_row.addWidget(speed_hint)
        self.speed_spin = QDoubleSpinBox(decimals=1)
        self.speed_spin.setRange(30.0, 400.0)
        self.speed_spin.setValue(240.0)
        speed_row.addWidget(self.speed_spin)
        layout.addLayout(speed_row)

        self.widebody_check = QCheckBox('Widebody kit')
        layout.addWidget(self.widebody_check)
        self.controller_check = QCheckBox('Controller driving')
        layout.addWidget(self.controller_check)

        root.addWidget(group)

    def _build_symptoms_group(self, root: QVBoxLayout) -> None:
        group = QGroupBox('Symptoms & stability')
        layout = QVBoxLayout(group)

        self.symptom_checks: Dict[str, QCheckBox] = {}
        for key in SYMPTOMS:
            check = QCheckBox(_SYMPTOM_DISPLAY[key])
            self.symptom_checks[key] = check
            layout.addWidget(check)

        stab_row = QHBoxLayout()
        stab_hint = QLabel('Stability (lo / hi)')
        stab_hint.setObjectName('hintLabel')
        stab_row.addWidget(stab_hint)
        self.stab_low_spin = QDoubleSpinBox(decimals=2)
        self.stab_low_spin.setRange(0.0, 1.0)
        self.stab_low_spin.setSpecialValueText('')
        self.stab_high_spin = QDoubleSpinBox(decimals=2)
        self.stab_high_spin.setRange(0.0, 1.0)
        self.stab_high_spin.setSpecialValueText('')
        stab_row.addWidget(self.stab_low_spin)
        stab_row.addWidget(self.stab_high_spin)
        layout.addLayout(stab_row)

        root.addWidget(group)

    # ------------------------------------------------------- collect helpers

    def _update_solve_gate(self, *_args: Any) -> None:
        """Enable solve_combo only when all three G spins are non-zero."""
        calibrated = all(s.value() > 0.0
                         for s in (self.g60_spin, self.g120_spin, self.g240_spin))
        self.solve_combo.setEnabled(calibrated)

    def _track_id(self) -> Optional[str]:
        """Resolve the track combo to a track id.

        Placeholder or empty text → None. Edited text matching no track →
        None + a status note (the service never sees a bogus id).
        """
        text = self.track_combo.currentText()
        if not text or text == self.track_combo.itemText(0):
            return None
        for i in range(self.track_combo.count()):
            if self.track_combo.itemText(i) == text:
                return self.track_combo.itemData(i)
        self.set_status('Unknown track ignored', 'warn')
        return None

    def _ref_df(self) -> Optional[Tuple[int, int]]:
        """(front, rear) when either ref spin is non-zero (else None); a
        single set value is used for both axes (the service warning covers
        the gap)."""
        lo, hi = self.gref_f_spin.value(), self.gref_r_spin.value()
        if lo == 0 and hi == 0:
            return None
        if lo == 0:
            return (hi, hi)
        if hi == 0:
            return (lo, lo)
        return (lo, hi)

    def _refill_cars(self, text: str) -> None:
        """Refill car_combo from service.search_cars(text); preserve the
        selection when it survives, otherwise select the first match and
        (re)trigger the car prefill."""
        keep_id = self.car_combo.currentData()
        self.car_combo.blockSignals(True)
        self.car_combo.clear()
        for car in self.service.search_cars(text):
            self.car_combo.addItem(car['name'], car['id'])
        if keep_id is not None:
            self.car_combo.setCurrentIndex(self.car_combo.findData(keep_id))
        self.car_combo.blockSignals(False)
        new_id = self.car_combo.currentData()
        if new_id and new_id != (self._current_car or {}).get('id'):
            self.on_car_selected(new_id)

    # ------------------------------------------------------- car prefill

    def on_car_selected(self, car_id: str) -> None:
        """Prefill everything derivable from the DB for `car_id`."""
        car = self.service.get_car(car_id)
        if car is None:
            self._current_car = None
            self._clear_prefills()
            self.set_status('Car not found', 'error')
            return
        self._current_car = car
        self._fill_db_info(car)
        self._apply_db_overrides(car)
        self._prefill_ranges(car)
        self._refill_swaps(car)
        self.set_status('')

    def _fill_db_info(self, car: Dict[str, Any]) -> None:
        engine = car.get('engine') or {}
        balance = car.get('balance') or {}
        lines = [
            car.get('name') or car.get('short_name') or '',
            f"Mass: {car.get('mass_kg', '?')} kg",
            f"Power: {engine.get('power_hp', '?')} hp",
            f"Torque: {engine.get('torque_nm', '?')} Nm",
            f"Drivetrain: {car.get('drivetrain', '?')}",
            f"Weight balance: {balance.get('front_pct', '?')}:{balance.get('rear_pct', '?')}",
        ]
        code = engine.get('code')
        if code:
            lines.append(f"Engine: {code} ({engine.get('type') or '?'})")
        self.db_info_label.setText('\n'.join(lines))

    def _apply_db_overrides(self, car: Dict[str, Any]) -> None:
        """Checkboxes → checked (use DB); spinboxes → DB values."""
        engine = car.get('engine') or {}
        balance = car.get('balance') or {}
        for cb in (self.mass_use_db, self.power_use_db,
                   self.torque_use_db, self.balance_use_db):
            cb.setChecked(True)
        self.mass_spin.setValue(int(car.get('mass_kg') or 0))
        self.power_spin.setValue(int(engine.get('power_hp') or 0))
        self.torque_spin.setValue(float(engine.get('torque_nm') or 0.0))
        self.bal_f_spin.setValue(int(balance.get('front_pct') or 0))
        self.bal_r_spin.setValue(int(balance.get('rear_pct') or 0))
        dt = car.get('drivetrain')
        idx = self.drivetrain_combo.findText(dt) if dt else -1
        self.drivetrain_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _prefill_ranges(self, car: Dict[str, Any]) -> None:
        """Range pairs from get_slider_ranges; missing key → 0/0 (None)."""
        ranges = self.service.get_slider_ranges(car.get('id', ''))
        mapping = {
            'df_front': self.df_f, 'df_rear': self.df_r,
            'height_front': self.hf, 'height_rear': self.hr,
            'fn_front': self.fn_f, 'fn_rear': self.fn_r,
        }
        for key, pair in mapping.items():
            value = ranges.get(key)
            pair.set_value(tuple(value) if value else None)

    def _refill_swaps(self, car: Dict[str, Any]) -> None:
        """Item 0 = 'Stock engine' (data ''), then each swap (donor_id)."""
        self.swap_combo.blockSignals(True)
        self.swap_combo.clear()
        self.swap_combo.addItem('Stock engine', '')
        for swap in self.service.get_swaps(car.get('id', '')):
            self.swap_combo.addItem(swap['engine'], swap['donor_id'])
        self.swap_combo.blockSignals(False)
        # Re-arm: index 0 ('Stock engine') fires the stock-restore handler.
        self._on_swap_index_changed(0)

    def _on_swap_selected(self, donor_id: str) -> None:
        if not donor_id:
            # Stock engine: restore DB power/torque, re-enable use-DB.
            if self._current_car:
                engine = self._current_car.get('engine') or {}
                self.power_spin.setValue(int(engine.get('power_hp') or 0))
                self.torque_spin.setValue(float(engine.get('torque_nm') or 0.0))
            self.power_use_db.setChecked(True)
            self.torque_use_db.setChecked(True)
            return
        donor = self.service.get_car(donor_id)
        if donor is None:
            self.set_status(f'Swap donor {donor_id} not found in DB', 'error')
            return
        engine = donor.get('engine') or {}
        self.power_spin.setValue(int(engine.get('power_hp') or 0))
        self.torque_spin.setValue(float(engine.get('torque_nm') or 0.0))
        self.power_use_db.setChecked(False)
        self.torque_use_db.setChecked(False)
        self.set_status(f"Swap: {donor.get('name', donor_id)} "
                        f"({engine.get('power_hp')} hp / {engine.get('torque_nm')} Nm)",
                        'ok')

    def _clear_prefills(self) -> None:
        self.db_info_label.setText('')
        self.swap_combo.blockSignals(True)
        self.swap_combo.clear()
        self.swap_combo.addItem('Stock engine', '')
        self.swap_combo.blockSignals(False)
        for cb in (self.mass_use_db, self.power_use_db,
                   self.torque_use_db, self.balance_use_db):
            cb.setChecked(True)
        for spin in (self.mass_spin, self.power_spin,
                     self.bal_f_spin, self.bal_r_spin):
            spin.setValue(0)
        self.torque_spin.setValue(0.0)
        for pair in (self.df_f, self.df_r, self.hf, self.hr,
                     self.fn_f, self.fn_r):
            pair.set_value(None)

    # ------------------------------------------------------------- actions

    def _on_save_ranges(self) -> None:
        car_id = self.car_combo.currentData()
        if not car_id:
            self.set_status('Select a car first to save ranges', 'warn')
            return
        pairs = {
            'df_front': self.df_f.value(), 'df_rear': self.df_r.value(),
            'height_front': self.hf.value(), 'height_rear': self.hr.value(),
            'fn_front': self.fn_f.value(), 'fn_rear': self.fn_r.value(),
        }
        non_empty = {k: v for k, v in pairs.items() if v is not None}
        if not non_empty:
            self.set_status('Nothing to save: all ranges are 0/0', 'warn')
            return
        try:
            saved = self.service.save_sliders(car_id, non_empty)
        except Exception as exc:
            # Read-only volume / AV lock must never crash the GUI (qFatal).
            self.set_status(f'Save failed: {exc}', 'error')
            return
        if saved:
            self.set_status(f'Saved {len(non_empty)} range(s) to DB', 'ok')
        else:
            self.set_status('Save failed: car not found in DB', 'error')

    # ------------------------------------------------------------- collect

    def collect(self) -> GuiRequest:
        """Read all panels into a GuiRequest.

        RangePair.value() None (0/0) → None for that pair; unchecked
        *_use_db → spinbox value becomes the override (checked → None);
        balance only when balance_use_db is off. Calibration/session:
        g_forces only when all 3 G spins non-zero; g_ref_df when either ref
        spin non-zero; solve_objective / track_id from combo data ('' →
        None, edited unknown track → None + status note); stability only
        when both spins non-zero; symptoms = checked keys (empty → None).
        """
        req = GuiRequest(
            car_id=self.car_combo.currentData() or '',
            tire=self.tire_combo.currentText(),
            df_front=self.df_f.value(),
            df_rear=self.df_r.value(),
            height_front=self.hf.value(),
            height_rear=self.hr.value(),
            fn_front=self.fn_f.value(),
            fn_rear=self.fn_r.value(),
        )
        if not self.mass_use_db.isChecked():
            req.custom_mass = self.mass_spin.value()
        if not self.power_use_db.isChecked():
            req.custom_power = self.power_spin.value()
        if not self.torque_use_db.isChecked():
            req.custom_torque = self.torque_spin.value()
        req.custom_drivetrain = self.drivetrain_combo.currentText()
        if not self.balance_use_db.isChecked():
            req.custom_balance = (self.bal_f_spin.value(), self.bal_r_spin.value())

        g60, g120, g240 = (self.g60_spin.value(), self.g120_spin.value(),
                           self.g240_spin.value())
        if g60 > 0 and g120 > 0 and g240 > 0:
            req.g_forces = (g60, g120, g240)
        req.g_ref_df = self._ref_df()
        req.solve_objective = self.solve_combo.currentData() or None
        req.track_id = self._track_id()
        req.mode = self.mode_combo.currentText()
        req.speed_kmh = self.speed_spin.value()
        lo, hi = self.stab_low_spin.value(), self.stab_high_spin.value()
        if lo > 0 and hi > 0:
            req.stability = (lo, hi)
        checked = [key for key, check in self.symptom_checks.items()
                   if check.isChecked()]
        req.symptoms = checked or None
        req.is_widebody = self.widebody_check.isChecked()
        req.is_controller = self.controller_check.isChecked()
        return req

    # ------------------------------------------------------------- validate

    def validate(self) -> List[str]:
        """`collect()` → `service.validate()`; render errors (red) and
        warnings (⚠-prefixed, amber) into status_label; return the errors."""
        req = self.collect()
        errors, warnings = self.service.validate(req)
        if errors:
            self.set_status('\n'.join(errors), 'error')
        elif warnings:
            self.set_status('\n'.join(f'⚠ {w}' for w in warnings), 'warn')
        else:
            self.set_status('', 'ok')
        return errors

    # ------------------------------------------------------------- status

    def set_status(self, text: str, kind: Optional[str] = None) -> None:
        """Flash a status message; kind ∈ {ok, warn, error} drives the theme."""
        for prop in _STATUS_KINDS:
            self.status_label.setProperty(prop, kind == prop)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(text)