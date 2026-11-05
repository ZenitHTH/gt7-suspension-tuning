"""Reusable form widgets (Task 4).

`RangePair` owns the Global Constraint rule: a range pair is "unset"
(None) iff both min and max are 0. The form's `collect()` only reads
`RangePair.value()`, so the rule lives here and nowhere else.
"""
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QWidget,
)


class RangePair(QWidget):
    """Label + min/max spinbox pair; owns the (0,0)→None rule from Global Constraints."""

    def __init__(self, label: str, kind: str = 'int', max_v: float = 1000,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind = kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        name = QLabel(label)
        name.setObjectName('hintLabel')  # theme: secondary text 12px
        layout.addWidget(name)

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
            layout.addWidget(spin)

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
