"""Reusable form widgets (Task 4).

`RangePair` owns the Global Constraint rule: a range pair is "unset"
(None) iff both min and max are 0. The form's `collect()` only reads
`RangePair.value()`, so the rule lives here and nowhere else.
"""
from typing import Optional, Tuple

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

PAIR_SPIN_WIDTH = 92
PAIR_SEP_WIDTH = 16
PAIR_ROW_SPACING = 4
INPUT_COL_WIDTH = PAIR_SPIN_WIDTH * 2 + PAIR_SEP_WIDTH + PAIR_ROW_SPACING * 2


class _WheelGuard(QObject):
    """Ignore mouse wheel events on inputs unless the widget holds focus."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel and isinstance(obj, QWidget):
            if not obj.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(obj, event)


def install_wheel_guard(widget: QWidget) -> None:
    """Prevent accidental mouse-wheel mutations when scrolling a parent panel."""
    if widget.property('_wheel_guarded'):
        return
    widget.setProperty('_wheel_guarded', True)
    widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    guard = _WheelGuard(widget)
    widget.installEventFilter(guard)


def _make_spin_pair(kind: str, max_v: float) -> Tuple[QAbstractSpinBox, QAbstractSpinBox]:
    """Create aligned min/max spinboxes of uniform width regardless of `kind`."""
    spins = []
    for _ in range(2):
        if kind == 'float':
            spin: QAbstractSpinBox = QDoubleSpinBox(decimals=2)
            spin.setRange(0.0, max_v)
        else:
            spin = QSpinBox()
            spin.setRange(0, int(max_v))
        spin.setFixedWidth(PAIR_SPIN_WIDTH)
        install_wheel_guard(spin)
        spins.append(spin)
    return spins[0], spins[1]


class RangePair(QWidget):
    """Label + min/max spinbox pair; owns the (0,0)→None rule from Global Constraints."""

    def __init__(self, label: str, kind: str = 'int', max_v: float = 1000,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind = kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PAIR_ROW_SPACING)

        name = QLabel(label)
        name.setObjectName('hintLabel')
        layout.addWidget(name, 1)

        self.min_spin, self.max_spin = _make_spin_pair(kind, max_v)
        sep = QLabel('–')
        sep.setObjectName('hintLabel')
        sep.setFixedWidth(PAIR_SEP_WIDTH)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.min_spin)
        layout.addWidget(sep)
        layout.addWidget(self.max_spin)

    def value(self) -> Optional[Tuple[float, float]]:
        """(min, max); None when both values are 0."""
        lo, hi = self.min_spin.value(), self.max_spin.value()
        if lo == 0 and hi == 0:
            return None
        return (lo, hi)

    def set_value(self, pair: Optional[Tuple[float, float]]) -> None:
        """Set (min, max); None → both 0."""
        lo, hi = (0, 0) if pair is None else pair
        self.min_spin.setValue(lo)
        self.max_spin.setValue(hi)
