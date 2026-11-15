"""Reusable form widgets (Task 4).

`RangePair` owns the Global Constraint rule: a range pair is "unset"
(None) iff both min and max are 0. The form's `collect()` only reads
`RangePair.value()`, so the rule lives here and nowhere else.
"""
from typing import Optional, Tuple

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QWidget,
)


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


class RangePair(QWidget):
    """Label + min/max spinbox pair; owns the (0,0)→None rule from Global Constraints."""

    def __init__(self, label: str, kind: str = 'int', max_v: float = 1000,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind = kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        name = QLabel(label)
        name.setObjectName('hintLabel')  # theme: secondary text 12px
        layout.addWidget(name, 1)

        if kind == 'float':
            self.min_spin = QDoubleSpinBox(decimals=2)
            self.max_spin = QDoubleSpinBox(decimals=2)
            self.min_spin.setMaximum(max_v)
            self.max_spin.setMaximum(max_v)
        else:
            self.min_spin = QSpinBox()
            self.max_spin = QSpinBox()
            self.min_spin.setMaximum(int(max_v))
            self.max_spin.setMaximum(int(max_v))

        for spin in (self.min_spin, self.max_spin):
            spin.setMinimum(0)
            spin.setMinimumWidth(76)
            install_wheel_guard(spin)

        sep = QLabel('–')
        sep.setObjectName('hintLabel')
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
