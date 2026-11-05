"""Global dark-cockpit theme (Design Spec tokens, plan 2026-07-12-gt7-suspension-gui).

Dark chrome + light document sheet. Single accent color. Keep QSS <= 70 lines.

Arrow glyphs (spinbox up/down, combo down-arrow) are generated as tiny PNGs at
start-up and referenced by file path: QSS cannot draw glyphs itself, Qt's QSS
`url()` does not accept `data:` URIs, and PyQt6's `qRegisterResourceData`
cannot register raw bytes. Without this the default platform style draws the
arrows near-black on the dark `bg-field` and they are invisible.
"""
import os
import struct
import tempfile
import zlib

from PyQt6.QtWidgets import QApplication

# Design Spec token `text-primary` — the arrow glyph color.
_ARROW_RGB = (0xE6, 0xE8, 0xEE)


def _arrow_png(up: bool) -> bytes:
    """14x14 RGBA PNG: filled triangle in `_ARROW_RGB`, transparent background."""
    n, rgb = 14, _ARROW_RGB
    rows = []
    for y in range(n):
        w = max(1, int(((y if up else n - 1 - y) + 1) * 2 * 0.75))
        cx = n // 2
        row = bytearray()
        for x in range(n):
            row += bytes(rgb + (255,)) if cx - w // 2 <= x <= cx + w // 2 else b'\x00' * 4
        rows.append(row)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))

    ihdr = struct.pack('>IIBBBBB', n, n, 8, 6, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + r for r in rows)))
            + chunk(b'IEND', b''))


def _arrow_paths() -> tuple:
    """Idempotently write the arrow PNGs to the OS temp dir; return (up, down)."""
    d = os.path.join(tempfile.gettempdir(), 'gt7-suspension-tuner')
    os.makedirs(d, exist_ok=True)
    up = os.path.join(d, 'arrow_up.png')
    down = os.path.join(d, 'arrow_down.png')
    if not (os.path.exists(up) and os.path.exists(down)):
        open(up, 'wb').write(_arrow_png(True))
        open(down, 'wb').write(_arrow_png(False))
    return up, down


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
QComboBox::down-arrow { image: url("__ARROW_DOWN__"); }
QComboBox QAbstractItemView { background: #14161a; color: #e6e8ee; border: 1px solid #3a3f4d; selection-background-color: #e5484d; }
QSpinBox::line-edit, QDoubleSpinBox::line-edit { background: #14161a; border: none; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 18px; border-left: 1px solid #3a3f4d; background: #1b1d23; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 18px; border-left: 1px solid #3a3f4d; border-top: 1px solid #3a3f4d; background: #1b1d23; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("__ARROW_UP__"); }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("__ARROW_DOWN__"); }
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
    """Apply the theme stylesheet to the application.

    `QSS` carries `__ARROW_UP__`/`__ARROW_DOWN__` placeholders which are
    replaced with the generated PNG paths so the spinbox/combo arrow glyphs
    stay visible regardless of the platform style.
    """
    up, down = _arrow_paths()
    app.setStyleSheet(
        QSS.replace('__ARROW_UP__', up).replace('__ARROW_DOWN__', down))
