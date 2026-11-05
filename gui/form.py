"""SetupForm — left-pane input form (Task 4: vehicle, tire, ranges, overrides).

Picking a car prefills everything derivable from the DB; `collect()` reads
the Task 4 panels into a partial `GuiRequest` (calibration/session fields
stay at defaults until Task 5).
"""
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from gui.components import RangePair
from gui.request import DRIVETRAINS, TIRE_COMPOUNDS, GuiRequest
from gui.service import TuningService

_STATUS_KINDS = ('ok', 'warn', 'error')


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
        self.df_f = RangePair('DF front', kind='int', max_v=1000)
        self.df_r = RangePair('DF rear', kind='int', max_v=1000)
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
        saved = self.service.save_sliders(car_id, non_empty)
        if saved:
            self.set_status(f'Saved {len(non_empty)} range(s) to DB', 'ok')
        else:
            self.set_status('Save failed: car not found in DB', 'error')

    # ------------------------------------------------------------- collect

    def collect(self) -> GuiRequest:
        """Read the Task 4 panels into a GuiRequest.

        RangePair.value() None (0/0) → None for that pair; unchecked
        *_use_db → spinbox value becomes the override (checked → None);
        balance only when balance_use_db is off. Session/calibration
        fields keep their dataclass defaults until Task 5.
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
        return req

    # ------------------------------------------------------------- status

    def set_status(self, text: str, kind: Optional[str] = None) -> None:
        """Flash a status message; kind ∈ {ok, warn, error} drives the theme."""
        for prop in _STATUS_KINDS:
            self.status_label.setProperty(prop, kind == prop)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(text)