"""Shared step-by-step modal picker dialog and card button helpers."""
from typing import Callable, List, Optional, Sequence, Tuple

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

_PICKER_QSS = (
    'QDialog#stepPickerDialog, QWidget#pickerPage, QScrollArea { background: #1b1d23; color: #ffffff; border: none; }\n'
    'QLineEdit#pickerSearchEdit { background: #14161a; color: #ffffff; border: 1px solid #3a3f4d; border-radius: 5px; padding: 5px 10px; min-height: 28px; }\n'
    'QLineEdit#pickerSearchEdit:focus { border: 1px solid #e5484d; }\n'
    'QPushButton#pickerBackBtn { background: #23262e; color: #ffffff; border: 1px solid #3a3f4d; border-radius: 6px; padding: 6px 12px; font-weight: bold; }\n'
    'QPushButton#pickerBackBtn:disabled { color: #9aa3b5; background: #14161a; border-color: #3a3f4d; }\n'
    'QPushButton#pickerCrumbBtn, QPushButton#pickerCrumbCurrent { background: transparent; border: none; padding: 4px 6px; font-size: 13px; color: #9aa3b5; }\n'
    'QPushButton#pickerCrumbBtn:hover { color: #ffffff; text-decoration: underline; }\n'
    'QPushButton#pickerCrumbCurrent, QLabel#pickerCardTitle, QLabel#pickerCountryLabel { color: #ffffff; font-weight: bold; background: transparent; }\n'
    'QLabel#pickerCrumbSep, QLabel#pickerCardSubtitle, QLabel#pickerEmptyLabel { color: #9aa3b5; background: transparent; }\n'
    'QLabel#pickerCrumbSep, QLabel#pickerCardTitle, QLabel#pickerCountryLabel { font-size: 13px; }\n'
    'QLabel#pickerCardSubtitle { font-size: 11.5px; } QLabel#pickerEmptyLabel { font-size: 13px; padding: 24px; }\n'
    'QPushButton#pickerCard, QPushButton#pickerContinentCard { background: #23262e; color: #ffffff; border: 1px solid #3a3f4d; border-radius: 8px; padding: 2px; text-align: left; }\n'
    'QPushButton#pickerBackBtn:hover, QPushButton#pickerCard:hover, QPushButton#pickerContinentCard:hover { border-color: #e5484d; background: #23262e; }\n'
    'QPushButton#pickerCard:pressed, QPushButton#pickerContinentCard:pressed { background: #14161a; border-color: #e5484d; }\n'
)


def picker_stylesheet() -> str:
    """Return the local dark-cockpit QSS for step-by-step picker dialogs."""
    return _PICKER_QSS


def clear_layout(layout: QLayout) -> None:
    """Remove and delete all widgets, sub-layouts, and spacers from `layout`."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
            continue
        sub = item.layout() if item is not None else None
        if sub is not None:
            clear_layout(sub)
            sub.deleteLater()


class _PickerCardButton(QPushButton):
    """QPushButton whose size hint follows its inner wrapped card layout."""

    def sizeHint(self) -> QSize:
        return self.layout().sizeHint() if self.layout() is not None else super().sizeHint()
    def minimumSizeHint(self) -> QSize:
        return self.layout().minimumSize() if self.layout() is not None else super().minimumSizeHint()
    def hasHeightForWidth(self) -> bool:
        return self.layout().hasHeightForWidth() if self.layout() is not None else super().hasHeightForWidth()
    def heightForWidth(self, width: int) -> int:
        return self.layout().heightForWidth(width) if self.layout() is not None else super().heightForWidth(width)


def _configure_button(btn: QPushButton, object_name: str,
                      callback: Optional[Callable[[], None]] = None) -> QPushButton:
    btn.setObjectName(object_name)
    btn.setAutoDefault(False)
    btn.setDefault(False)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if callback is not None:
        btn.clicked.connect(lambda _=False, cb=callback: cb())
    return btn


def make_picker_button(title: str, subtitle: str = '',
                       object_name: str = 'pickerCard') -> QPushButton:
    """Build a pure-text card button with title and optional muted subtitle."""
    btn = _configure_button(_PickerCardButton(), object_name)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    btn.setAccessibleName(f'{title} — {subtitle}' if subtitle else title)
    box = QVBoxLayout(btn)
    box.setContentsMargins(12, 10, 12, 10)
    box.setSpacing(3)
    for text, name in ((title, 'pickerCardTitle'), (subtitle, 'pickerCardSubtitle')):
        if text or name == 'pickerCardTitle':
            lbl = QLabel(text, objectName=name, wordWrap=True)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            box.addWidget(lbl)
    return btn


def _add_scroll_page(stack: QStackedWidget) -> QVBoxLayout:
    scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    page = QWidget(objectName='pickerPage')
    layout = QVBoxLayout(page)
    layout.setContentsMargins(4, 4, 8, 4)
    layout.setSpacing(12)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    scroll.setWidget(page)
    stack.addWidget(scroll)
    return layout


class StepPickerDialog(QDialog):
    """Shared modal 3-step picker shell with breadcrumbs, Back, and live search."""

    def __init__(self, title: str, root_crumb: str, search_placeholder: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, objectName='stepPickerDialog', windowTitle=title, modal=True)
        self._active_step = 0
        self.resize(780, 560)
        self.setMinimumSize(620, 440)
        self.setStyleSheet(picker_stylesheet())
        self._build_ui(root_crumb, search_placeholder)
        self.show_step(0)

    def _build_ui(self, root_crumb: str, search_placeholder: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(12)
        root.addLayout(self._build_header(search_placeholder))
        self.stack = QStackedWidget()
        self._containers: List[QVBoxLayout] = [_add_scroll_page(self.stack) for _ in range(4)]
        self.search_results_layout = self._containers[3]
        root.addWidget(self.stack, 1)
        self.set_breadcrumbs([(root_crumb, lambda: self.show_step(0))])

    def _build_header(self, search_placeholder: str) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(10)
        self.back_btn = _configure_button(QPushButton('← Back'), 'pickerBackBtn', self._handle_back_clicked)
        header.addWidget(self.back_btn)
        self.breadcrumb_bar = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_bar)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(4)
        header.addWidget(self.breadcrumb_bar, 1)
        self.search_edit = QLineEdit(objectName='pickerSearchEdit', placeholderText=search_placeholder)
        self.search_edit.setFixedWidth(230)
        self.search_edit.textChanged.connect(self._handle_search_text)
        header.addWidget(self.search_edit)
        return header

    def set_breadcrumbs(self, segments: Sequence[Tuple[str, Callable[[], None]]]) -> None:
        """Render clickable breadcrumb segments inside the top header bar."""
        clear_layout(self.breadcrumb_layout)
        last_idx = len(segments) - 1
        for idx, (label, callback) in enumerate(segments):
            if idx > 0:
                self.breadcrumb_layout.addWidget(QLabel('›', objectName='pickerCrumbSep'))
            obj = 'pickerCrumbCurrent' if idx == last_idx else 'pickerCrumbBtn'
            self.breadcrumb_layout.addWidget(_configure_button(QPushButton(label), obj, callback))
        self.breadcrumb_layout.addStretch(1)

    def step_container(self, step_index: int) -> QVBoxLayout:
        """Return the scrollable content layout for step index 0, 1, 2, or 3."""
        return self._containers[step_index]

    def show_step(self, step_index: int) -> None:
        """Switch to step 0..2, clearing any active search view state."""
        if step_index not in (0, 1, 2):
            raise ValueError(f'Invalid step index: {step_index}')
        self._active_step = step_index
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        self._activate_step_view(step_index)

    def _activate_step_view(self, step_index: int) -> None:
        clear_layout(self.search_results_layout)
        self.stack.setCurrentIndex(step_index)
        self.back_btn.setEnabled(step_index > 0)

    def _handle_back_clicked(self) -> None:
        if self.search_edit.text().strip():
            self.search_edit.clear()
            return
        self._on_back()

    def _handle_search_text(self, text: str) -> None:
        query = text.strip()
        if not query:
            self._activate_step_view(self._active_step)
            return
        self.stack.setCurrentIndex(3)
        self.back_btn.setEnabled(True)
        self._on_search_changed(query)

    def _on_back(self) -> None:
        """Navigate one step back; subclasses override to update content."""
        if self._active_step > 0:
            self.show_step(self._active_step - 1)

    def _on_search_changed(self, query: str) -> None:
        """Populate `search_results_layout` for `query`; overridden by subclasses."""
