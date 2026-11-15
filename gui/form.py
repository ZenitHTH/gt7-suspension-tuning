"""SetupForm — left-pane input form (Tasks 4-5).

Picking a car prefills everything derivable from the DB; `collect()` reads
all panels into a fully-populated `GuiRequest`; `validate()` runs
`service.validate()` and renders errors/warnings into the status label.
"""
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
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
from gui.components import (
    INPUT_COL_WIDTH,
    PAIR_ROW_SPACING,
    PAIR_SEP_WIDTH,
    PAIR_SPIN_WIDTH,
    RangePair,
    install_wheel_guard,
)
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
    """All input panels; `collect()` → `GuiRequest`."""

    def __init__(self, service: TuningService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('setupForm')
        self.service = service
        self._current_car: Optional[Dict[str, Any]] = None
        self._db_drivetrain_choice: Optional[str] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 10, 8)
        root.setSpacing(12)

        self._build_vehicle_group(root)
        self._build_tire_group(root)
        self._build_ranges_group(root)
        self._build_overrides_group(root)
        self._build_calibration_group(root)
        self._build_session_group(root)
        self._build_symptoms_group(root)

        self.status_label = QLabel()
        self.status_label.setObjectName('statusLabel')
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        root.addStretch(1)

        self._install_wheel_guards()
        self._refill_cars('')
        self._refill_tracks('')

    # ------------------------------------------------------- layout helpers

    def _make_group(self, title: str) -> Tuple[QGroupBox, QVBoxLayout]:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        return group, layout

    def _add_right_row(self, layout: QVBoxLayout, label_text: str, widget: QWidget) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setObjectName('hintLabel')
        row.addWidget(lbl, 1)
        widget.setFixedWidth(INPUT_COL_WIDTH)
        row.addWidget(widget)
        layout.addLayout(row)

    def _add_pair_row(self, layout: QVBoxLayout, label_text: str,
                      left: QWidget, right: QWidget, sep_text: str = '/') -> None:
        row = QHBoxLayout()
        row.setSpacing(PAIR_ROW_SPACING)
        lbl = QLabel(label_text)
        lbl.setObjectName('hintLabel')
        row.addWidget(lbl, 1)
        self._append_pair_widgets(row, left, right, sep_text)
        layout.addLayout(row)

    def _append_pair_widgets(self, row: QHBoxLayout, left: QWidget,
                             right: QWidget, sep_text: str) -> None:
        left.setFixedWidth(PAIR_SPIN_WIDTH)
        right.setFixedWidth(PAIR_SPIN_WIDTH)
        sep = QLabel(sep_text)
        sep.setObjectName('hintLabel')
        sep.setFixedWidth(PAIR_SEP_WIDTH)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(left)
        row.addWidget(sep)
        row.addWidget(right)

    def _add_override_row(self, layout: QVBoxLayout, check_label: str,
                          spin: QAbstractSpinBox) -> QCheckBox:
        cb = QCheckBox(check_label)
        cb.setChecked(True)
        spin.setEnabled(False)
        spin.setFixedWidth(INPUT_COL_WIDTH)
        cb.toggled.connect(lambda checked, s=spin: s.setEnabled(not checked))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(cb)
        row.addStretch(1)
        row.addWidget(spin)
        layout.addLayout(row)
        return cb

    # ------------------------------------------------------- wiring

    def _install_wheel_guards(self) -> None:
        for cls in (QSpinBox, QDoubleSpinBox, QComboBox):
            for widget in self.findChildren(cls):
                install_wheel_guard(widget)

    def _on_balance_use_db_toggled(self, checked: bool) -> None:
        self.bal_f_spin.setEnabled(not checked)
        self.bal_r_spin.setEnabled(not checked)

    def _on_car_index_changed(self, _index: int) -> None:
        car_id = self.car_combo.currentData()
        if car_id:
            self.on_car_selected(car_id)

    def _on_swap_index_changed(self, _index: int) -> None:
        self._on_swap_selected(self.swap_combo.currentData() or '')

    # ------------------------------------------------------- group builders

    def _build_vehicle_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('Vehicle')
        self.car_search = QLineEdit()
        self.car_search.setPlaceholderText('Search cars by name, maker or ID')
        self.car_search.textChanged.connect(self._refill_cars)
        layout.addWidget(self.car_search)

        self.car_combo = QComboBox()
        self.car_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.car_combo.setMinimumContentsLength(18)
        self.car_combo.currentIndexChanged[int].connect(self._on_car_index_changed)
        layout.addWidget(self.car_combo)

        self.swap_combo = QComboBox()
        self.swap_combo.currentIndexChanged[int].connect(self._on_swap_index_changed)
        self._add_right_row(layout, 'Engine swap', self.swap_combo)

        self.db_info_label = QLabel()
        self.db_info_label.setObjectName('dbInfoLabel')
        self.db_info_label.setWordWrap(True)
        self.db_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.db_info_label)
        root.addWidget(group)

    def _build_tire_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('Tire compound')
        self.tire_combo = QComboBox()
        for compound in TIRE_COMPOUNDS:
            self.tire_combo.addItem(compound, compound)
        self.tire_combo.setCurrentIndex(self.tire_combo.findText('SS'))
        self._add_right_row(layout, 'Compound', self.tire_combo)
        root.addWidget(group)

    def _build_ranges_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('In-game slider ranges')
        # max_v 2000: preseeded DF ranges in DB reach 1700 (cars 3342/3374/3517).
        self.df_f = RangePair('Downforce front', kind='int', max_v=2000)
        self.df_r = RangePair('Downforce rear', kind='int', max_v=2000)
        self.hf = RangePair('Height front', kind='int', max_v=400)
        self.hr = RangePair('Height rear', kind='int', max_v=400)
        self.fn_f = RangePair('Natural frequency front', kind='float', max_v=10.0)
        self.fn_r = RangePair('Natural frequency rear', kind='float', max_v=10.0)
        self.comp_range_pair = RangePair('Damping compression', kind='int', max_v=100)
        self.exp_range_pair = RangePair('Damping expansion', kind='int', max_v=100)
        for pair in (self.df_f, self.df_r, self.hf, self.hr, self.fn_f, self.fn_r,
                     self.comp_range_pair, self.exp_range_pair):
            layout.addWidget(pair)
        self._append_ranges_footer(layout)
        root.addWidget(group)

    def _append_ranges_footer(self, layout: QVBoxLayout) -> None:
        r_hint = QLabel('0/0 = use saved DB values (enter min and max to override)')
        r_hint.setObjectName('noteLabel')
        r_hint.setWordWrap(True)
        layout.addWidget(r_hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.save_ranges_btn = QPushButton('Save ranges to DB')
        self.save_ranges_btn.setFixedWidth(INPUT_COL_WIDTH)
        self.save_ranges_btn.clicked.connect(self._on_save_ranges)
        btn_row.addWidget(self.save_ranges_btn)
        layout.addLayout(btn_row)

    def _build_overrides_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('Build overrides')
        self.mass_spin = QSpinBox()
        self.mass_spin.setRange(0, 3000)
        self.mass_use_db = self._add_override_row(layout, 'Use DB mass (kg)', self.mass_spin)

        self.power_spin = QSpinBox()
        self.power_spin.setRange(0, 3000)
        self.power_use_db = self._add_override_row(layout, 'Use DB power (hp)', self.power_spin)

        self.torque_spin = QDoubleSpinBox(decimals=1)
        self.torque_spin.setRange(0.0, 1500.0)
        self.torque_use_db = self._add_override_row(layout, 'Use DB torque (Nm)', self.torque_spin)

        self._add_balance_override_row(layout)
        self.drivetrain_combo = QComboBox()
        for dt in DRIVETRAINS:
            self.drivetrain_combo.addItem(dt, dt)
        self._add_right_row(layout, 'Drivetrain', self.drivetrain_combo)
        root.addWidget(group)

    def _add_balance_override_row(self, layout: QVBoxLayout) -> None:
        self.balance_use_db = QCheckBox('Use DB balance (F/R %)')
        self.balance_use_db.setChecked(True)
        self.bal_f_spin = QSpinBox()
        self.bal_f_spin.setRange(0, 100)
        self.bal_f_spin.setEnabled(False)
        self.bal_r_spin = QSpinBox()
        self.bal_r_spin.setRange(0, 100)
        self.bal_r_spin.setEnabled(False)
        self.balance_use_db.toggled.connect(self._on_balance_use_db_toggled)

        row = QHBoxLayout()
        row.setSpacing(PAIR_ROW_SPACING)
        row.addWidget(self.balance_use_db)
        row.addStretch(1)
        self._append_pair_widgets(row, self.bal_f_spin, self.bal_r_spin, '/')
        layout.addLayout(row)

    def _build_calibration_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('Calibration')
        for attr, text in (('g60_spin', 'G @ 60 km/h'),
                           ('g120_spin', 'G @ 120 km/h'),
                           ('g240_spin', 'G @ 240 km/h')):
            spin = QDoubleSpinBox(decimals=2)
            spin.setRange(0.0, 9.0)
            spin.setSpecialValueText('')
            setattr(self, attr, spin)
            spin.valueChanged.connect(self._update_solve_gate)
            self._add_right_row(layout, text, spin)

        self.gref_f_spin = QSpinBox()
        self.gref_f_spin.setRange(0, 2000)
        self.gref_r_spin = QSpinBox()
        self.gref_r_spin.setRange(0, 2000)
        self._add_pair_row(layout, 'Ref downforce (F / R)',
                           self.gref_f_spin, self.gref_r_spin, '/')

        self.solve_combo = QComboBox()
        self.solve_combo.addItem('—', '')
        for objective in SOLVE_OBJECTIVES:
            self.solve_combo.addItem(objective, objective)
        self.solve_combo.setEnabled(False)
        self._add_right_row(layout, 'Solve', self.solve_combo)

        hint = QLabel('Measure peak lateral G in-game at 60/120/240 km/h '
                      'and the downforce you were running.')
        hint.setObjectName('noteLabel')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        root.addWidget(group)
        self._update_solve_gate()

    def _build_session_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('Session')
        self.track_search = QLineEdit()
        self.track_search.setPlaceholderText('Search tracks by name')
        self.track_search.textChanged.connect(self._refill_tracks)
        layout.addWidget(self.track_search)

        self.track_combo = QComboBox()
        self.track_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.track_combo.setMinimumContentsLength(18)
        layout.addWidget(self.track_combo)

        self.mode_combo = QComboBox()
        for mode in MODES:
            self.mode_combo.addItem(mode, mode)
        self._add_right_row(layout, 'Mode', self.mode_combo)

        self.speed_spin = QDoubleSpinBox(decimals=1)
        self.speed_spin.setRange(30.0, 400.0)
        self.speed_spin.setValue(240.0)
        self._add_right_row(layout, 'Speed (km/h)', self.speed_spin)

        checks_row = QHBoxLayout()
        checks_row.setSpacing(12)
        self.widebody_check = QCheckBox('Widebody kit')
        self.controller_check = QCheckBox('Controller driving')
        checks_row.addWidget(self.widebody_check, 1)
        checks_row.addWidget(self.controller_check, 1)
        layout.addLayout(checks_row)
        root.addWidget(group)

    def _build_symptoms_group(self, root: QVBoxLayout) -> None:
        group, layout = self._make_group('Symptoms && stability')
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        self.symptom_checks: Dict[str, QCheckBox] = {}
        for idx, key in enumerate(SYMPTOMS):
            check = QCheckBox(_SYMPTOM_DISPLAY[key])
            self.symptom_checks[key] = check
            grid.addWidget(check, idx // 2, idx % 2)
        layout.addLayout(grid)

        stab_hint = QLabel('Stability (low / high speed): −1.00 understeer … +1.00 oversteer')
        stab_hint.setObjectName('noteLabel')
        stab_hint.setWordWrap(True)
        layout.addWidget(stab_hint)

        self.stab_low_spin = QDoubleSpinBox(decimals=2)
        self.stab_low_spin.setRange(-1.0, 1.0)
        self.stab_low_spin.setSpecialValueText('')
        self.stab_high_spin = QDoubleSpinBox(decimals=2)
        self.stab_high_spin.setRange(-1.0, 1.0)
        self.stab_high_spin.setSpecialValueText('')
        self._add_pair_row(layout, 'Low / High', self.stab_low_spin, self.stab_high_spin, '/')
        root.addWidget(group)

    # ------------------------------------------------------- collect helpers

    def _update_solve_gate(self, *_args: Any) -> None:
        """Enable solve_combo only when all three G spins are non-zero."""
        calibrated = all(s.value() > 0.0
                         for s in (self.g60_spin, self.g120_spin, self.g240_spin))
        self.solve_combo.setEnabled(calibrated)

    def _track_id(self) -> Optional[str]:
        """Resolve the track combo to a track id; placeholder → None."""
        data = self.track_combo.currentData()
        return data if data else None

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

    def _refill_tracks(self, text: str) -> None:
        """Refill track_combo from TRACKS_DB filtered by `text`
        (case-insensitive substring); '— (no track)' stays at index 0."""
        keep = self.track_combo.currentData()
        self.track_combo.blockSignals(True)
        self.track_combo.clear()
        self.track_combo.addItem('— (no track)', '')
        for track in TRACKS_DB:
            if not text or text.lower() in track['name'].lower():
                self.track_combo.addItem(track['name'], track['id'])
        if keep:
            self.track_combo.setCurrentIndex(self.track_combo.findData(keep))
        self.track_combo.blockSignals(False)

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
        self._db_drivetrain_choice = self.drivetrain_combo.currentText()

    def _prefill_ranges(self, car: Dict[str, Any]) -> None:
        """Range pairs from get_slider_ranges; missing key → 0/0 (None)."""
        ranges = self.service.get_slider_ranges(car.get('id', ''))
        mapping = {
            'df_front': self.df_f, 'df_rear': self.df_r,
            'height_front': self.hf, 'height_rear': self.hr,
            'fn_front': self.fn_f, 'fn_rear': self.fn_r,
            'damping_comp': self.comp_range_pair,
            'damping_exp': self.exp_range_pair,
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
        self._db_drivetrain_choice = self.drivetrain_combo.currentText()
        for pair in (self.df_f, self.df_r, self.hf, self.hr,
                     self.fn_f, self.fn_r, self.comp_range_pair, self.exp_range_pair):
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
            'damping_comp': self.comp_range_pair.value(),
            'damping_exp': self.exp_range_pair.value(),
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
            compression_range=self.comp_range_pair.value(),
            expansion_range=self.exp_range_pair.value(),
        )
        if not self.mass_use_db.isChecked():
            req.custom_mass = self.mass_spin.value()
        if not self.power_use_db.isChecked():
            req.custom_power = self.power_spin.value()
        if not self.torque_use_db.isChecked():
            req.custom_torque = self.torque_spin.value()
        if self.drivetrain_combo.currentText() != getattr(self, '_db_drivetrain_choice', None):
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
        # 0.0/0.0 is a neutral reading = no trim, so treat it as unset
        # (keeps the setup notes free of a no-op stability line).
        if lo != 0.0 or hi != 0.0:
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