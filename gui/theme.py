"""Global dark-cockpit theme (Design Spec tokens, plan 2026-07-12-gt7-suspension-gui).

Dark chrome + light document sheet. Single accent color. Keep QSS <= 70 lines.
"""
from PyQt6.QtWidgets import QApplication

QSS = """
QMainWindow, QSplitter, QStatusBar { background: #1b1d23; color: #e6e8ee; font-size: 13px; }
QSplitter::handle { background: #3a3f4d; }
QStatusBar { font-size: 12px; }
QStatusBar::item { border: none; }
QWidget#statusLabel { font-size: 12px; }
QWidget#statusLabel[ok="true"] { color: #4ade80; }
QWidget#statusLabel[warn="true"] { color: #ffb454; font-weight: bold; }
QWidget#statusLabel[error="true"] { color: #ff6369; font-weight: bold; }
QLabel { color: #e6e8ee; font-size: 13px; }
QLabel#dbInfoLabel, QLabel#hintLabel { color: #9aa0ae; font-size: 12px; }
QLabel#warningsLabel { color: #ffb454; font-weight: bold; }
QGroupBox { background: #23262e; border: 1px solid #3a3f4d; border-radius: 8px; margin-top: 12px; padding: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #e6e8ee; font-weight: bold; font-size: 13px; }
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background: #14161a; color: #e6e8ee; border: 1px solid #3a3f4d; border-radius: 4px; padding: 4px 8px; min-height: 28px; }
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus { border: 2px solid #e5484d; }
QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled, QLineEdit:disabled { color: #9aa0ae; opacity: 0.5; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #14161a; color: #e6e8ee; border: 1px solid #3a3f4d; selection-background-color: #e5484d; }
QPushButton { background: #23262e; color: #e6e8ee; border: 1px solid #3a3f4d; border-radius: 4px; padding: 6px 12px; }
QPushButton:hover { border-color: #9aa0ae; }
QPushButton#computeButton { background: #e5484d; color: #ffffff; font-weight: bold; min-height: 40px; }
QPushButton#computeButton:hover { background: #f2555a; }
QPushButton#computeButton:pressed { background: #c73a3f; }
QTextBrowser#sheetBrowser { background: #ffffff; color: #16181d; font-family: monospace; font-size: 12.5px; padding: 16px; }
/* error-on-sheet #c62828: error text rendered inside the white sheet (applied inline by ResultsView; QSS cannot target browser text spans) */
QScrollBar:vertical { width: 10px; background: transparent; }
QScrollBar::handle:vertical { background: #3a3f4d; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 10px; background: transparent; }
QScrollBar::handle:horizontal { background: #3a3f4d; border-radius: 5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def apply(app: QApplication) -> None:
    """Apply the theme stylesheet to the application."""
    app.setStyleSheet(QSS)
