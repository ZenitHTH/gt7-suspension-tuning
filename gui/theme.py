"""Global dark-cockpit theme (Design Spec tokens, plan 2026-07-12-gt7-suspension-gui).

Dark chrome + dark telemetry sheet. Single crimson accent color. Keep QSS <= 70 lines.

Arrow and checkmark glyphs (spinbox up/down, combo down-arrow, checkbox check)
are generated as tiny RGBA PNGs at start-up and referenced by file path because
QSS cannot draw vector glyphs inline or load `data:` URIs reliably across Qt
styles.
"""
import os
import struct
import tempfile
import zlib
from typing import List, Tuple

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

import db.loader

_ARROW_RGB = (0xFF, 0xFF, 0xFF)
_FONT_STACK = ['Noto Sans', 'Segoe UI', 'SF Pro Text', 'Arial']
_FONTS_REGISTERED = False


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    c = tag + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))


def _encode_png(size: int, pixels: set) -> bytes:
    """Encode an `size`x`size` RGBA PNG with white glyphs at `pixels`."""
    white = bytes(_ARROW_RGB + (255,))
    clear = b'\x00' * 4
    rows = [
        b''.join(white if (x, y) in pixels else clear for x in range(size))
        for y in range(size)
    ]
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    raw = b''.join(b'\x00' + r for r in rows)
    return (b'\x89PNG\r\n\x1a\n' + _png_chunk(b'IHDR', ihdr)
            + _png_chunk(b'IDAT', zlib.compress(raw)) + _png_chunk(b'IEND', b''))


def _arrow_png(up: bool) -> bytes:
    """13x13 RGBA PNG: crisp centered 9x5 triangle in `_ARROW_RGB`."""
    size, cx = 13, 6
    pixels = set()
    for step in range(5):
        y = (4 + step) if up else (8 - step)
        for x in range(cx - step, cx + step + 1):
            pixels.add((x, y))
    return _encode_png(size, pixels)


def _check_png() -> bytes:
    """13x13 RGBA PNG: crisp centered checkmark in `_ARROW_RGB`."""
    pts = [
        (2, 6), (3, 7), (4, 8), (5, 7), (6, 6), (7, 5), (8, 4), (9, 3), (10, 2),
        (2, 7), (3, 8), (4, 9), (5, 8), (6, 7), (7, 6), (8, 5), (9, 4), (10, 3),
    ]
    return _encode_png(13, set(pts))


def _glyph_paths() -> Tuple[str, str, str]:
    """Write versioned glyph PNGs to the temp dir; return POSIX (up, down, check)."""
    d = os.path.join(tempfile.gettempdir(), 'gt7-suspension-tuner')
    os.makedirs(d, exist_ok=True)
    specs = (
        ('arrow_up_v2.png', _arrow_png(True)),
        ('arrow_down_v2.png', _arrow_png(False)),
        ('check_v2.png', _check_png()),
    )
    paths: List[str] = []
    for fname, data in specs:
        p = os.path.join(d, fname)
        with open(p, 'wb') as f:
            f.write(data)
        paths.append(p.replace('\\', '/'))
    return paths[0], paths[1], paths[2]


QSS = """
QMainWindow, QSplitter, QStatusBar, QScrollArea, QWidget#setupForm, QWidget#centralPane, QWidget#resultsPane { background: #1b1d23; color: #ffffff; font-size: 13px; }
QSplitter::handle { background: #2d313d; margin: 8px 2px; border-radius: 1px; }
QSplitter::handle:hover { background: #e5484d; }
QStatusBar { font-size: 12px; }
QStatusBar::item { border: none; }
QWidget#statusLabel { font-size: 12px; }
QWidget#statusLabel[ok="true"] { color: #4ade80; }
QWidget#statusLabel[warn="true"] { color: #ffb454; font-weight: bold; }
QWidget#statusLabel[error="true"] { color: #ff6369; font-weight: bold; }
QLabel { color: #ffffff; font-size: 13px; }
QLabel#hintLabel { color: #ffffff; font-size: 12px; }
QLabel#noteLabel { color: #9aa3b5; font-size: 11.5px; }
QLabel#dbInfoLabel { background: #14161a; border: 1px solid #2e323d; border-radius: 6px; padding: 8px 10px; color: #ffffff; font-size: 12px; }
QLabel#warningsLabel { color: #ffb454; background: #23262e; border: 1px solid #ffb454; border-radius: 6px; padding: 8px 12px; font-weight: bold; font-size: 12px; }
QGroupBox { background: #23262e; border: 1px solid #3a3f4d; border-radius: 8px; margin-top: 12px; padding: 20px 14px 14px 14px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; padding: 0 6px; background: #1b1d23; color: #ffffff; font-weight: bold; font-size: 12.5px; }
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background: #14161a; color: #ffffff; border: 1px solid #3a3f4d; border-radius: 5px; padding: 4px 8px; min-height: 28px; }
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus { border: 1px solid #e5484d; }
QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled, QLineEdit:disabled { color: #7a8194; background: #181a20; border-color: #2a2e38; }
QComboBox::drop-down { subcontrol-origin: border; subcontrol-position: top right; width: 24px; margin: 1px 1px 1px 0; border-left: 1px solid #3a3f4d; background: #23262e; border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
QComboBox::drop-down:hover { background: #2c303b; }
QComboBox::drop-down:disabled { background: #181a20; border-color: #2a2e38; }
QComboBox::down-arrow { image: url("__ARROW_DOWN__"); width: 9px; height: 9px; }
QComboBox QAbstractItemView { background: #14161a; color: #ffffff; border: 1px solid #3a3f4d; selection-background-color: #e5484d; }
QSpinBox::line-edit, QDoubleSpinBox::line-edit { background: transparent; border: none; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; margin: 1px 1px 0 0; border-left: 1px solid #3a3f4d; background: #23262e; border-top-right-radius: 4px; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; margin: 0 1px 1px 0; border-left: 1px solid #3a3f4d; border-top: 1px solid #3a3f4d; background: #23262e; border-bottom-right-radius: 4px; }
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: #2c303b; }
QSpinBox::up-button:disabled, QDoubleSpinBox::up-button:disabled, QSpinBox::down-button:disabled, QDoubleSpinBox::down-button:disabled { background: #181a20; border-color: #2a2e38; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("__ARROW_UP__"); width: 8px; height: 8px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("__ARROW_DOWN__"); width: 8px; height: 8px; }
QCheckBox { color: #ffffff; font-size: 13px; spacing: 8px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #3a3f4d; border-radius: 4px; background: #14161a; }
QCheckBox::indicator:hover { border-color: #ffffff; }
QCheckBox::indicator:checked { background: #e5484d; border-color: #e5484d; image: url("__CHECK__"); }
QPushButton { background: #23262e; color: #ffffff; border: 1px solid #3a3f4d; border-radius: 6px; padding: 7px 14px; font-weight: 500; }
QPushButton:hover { background: #2c303b; border-color: #8b93a7; }
QPushButton:pressed { background: #181a20; }
QPushButton:disabled { color: #6e7585; background: #181a20; border-color: #2a2e38; }
QPushButton#computeButton { background: #e5484d; border-color: #e5484d; color: #ffffff; font-weight: bold; min-width: 150px; min-height: 38px; padding: 8px 20px; border-radius: 6px; }
QPushButton#computeButton:hover { background: #f2555a; border-color: #f2555a; }
QPushButton#computeButton:pressed { background: #c73a3f; border-color: #c73a3f; }
QPushButton#computeButton:disabled { background: #6b2629; border-color: #6b2629; color: #c7cdd8; }
QTextBrowser#sheetBrowser { background: #14161a; color: #ffffff; border: 1px solid #3a3f4d; border-radius: 8px; padding: 16px; font-family: "Menlo", "Consolas", "DejaVu Sans Mono", monospace; font-size: 12.5px; }
/* error-on-sheet #ff6369: high-contrast coral-red error text rendered inside dark sheet (applied inline by ResultsView) */
QScrollBar:vertical { width: 8px; background: transparent; margin: 2px 0; }
QScrollBar::handle:vertical { background: #3a3f4d; border-radius: 4px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #5a6275; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { height: 0; background: none; }
QScrollBar:horizontal { height: 8px; background: transparent; }
QScrollBar::handle:horizontal { background: #3a3f4d; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { width: 0; background: none; }
"""


def _register_fonts(app: QApplication) -> None:
    """Register the bundled Noto Sans TTFs once so the family resolves on any OS."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    fonts_dir = os.path.join(db.loader.get_data_dir(), 'fonts')
    for name in ('NotoSans-Regular.ttf', 'NotoSans-Bold.ttf'):
        path = os.path.join(fonts_dir, name)
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)
    _FONTS_REGISTERED = True


def apply(app: QApplication) -> None:
    """Apply the dark-cockpit theme: register bundled fonts, set font, set QSS."""
    _register_fonts(app)
    font = QFont()
    font.setFamilies(_FONT_STACK)
    app.setFont(font)
    up, down, check = _glyph_paths()
    styled = (QSS.replace('__ARROW_UP__', up)
                 .replace('__ARROW_DOWN__', down)
                 .replace('__CHECK__', check))
    app.setStyleSheet(styled)
