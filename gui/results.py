"""Results pane (Task 6): warnings label + dark telemetry sheet browser + copy button.

The browser renders the setup sheet on a recessed dark motorsport telemetry panel
(`#14161a` background, `#ffffff` monospace text via `sheetBrowser`). Errors render
inline inside the browser in coral-red (`#ff6369`) for crisp contrast on `#14161a`.
"""
import html
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.request import GuiResult

_ERROR_ON_SHEET = '#ff6369'
_MONO_STACK = '"Menlo", "Consolas", "DejaVu Sans Mono", monospace'
_PLACEHOLDER_HTML = (
    f'<div style="color:#8b93a7; font-family:{_MONO_STACK}; '
    'line-height:1.65; padding-top:8px;">'
    '<div style="color:#ffffff; font-weight:bold; margin-bottom:6px;">'
    'GT7 TELEMETRY SETUP SHEET</div>'
    '<div>Select a car &amp; track, then click Compute Setup.</div>'
    '<div style="margin-top:6px;">Optional: enter 60 / 120 / 240 km/h '
    'lateral G readings to unlock aero/mechanical solve.</div>'
    '</div>'
)


class ResultsView(QWidget):
    """Right pane: amber warnings label, dark monospace sheet browser, and a
    copy-to-clipboard button for the raw sheet text."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('resultsPane')
        self._raw_sheet = ''

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.warnings_label = QLabel()
        self.warnings_label.setObjectName('warningsLabel')
        self.warnings_label.setWordWrap(True)
        root.addWidget(self.warnings_label)

        self.browser = QTextBrowser()
        self.browser.setObjectName('sheetBrowser')
        self.browser.setOpenExternalLinks(False)
        root.addWidget(self.browser, 1)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self.copy_btn = QPushButton('Copy sheet')
        self.copy_btn.setMinimumWidth(120)
        self.copy_btn.clicked.connect(self._copy)
        bar.addWidget(self.copy_btn)
        root.addLayout(bar)

        self.clear()

    # ------------------------------------------------------------- rendering

    def show_result(self, r: GuiResult) -> None:
        """Render `r`: sheet + warnings; error results route to show_error()."""
        if r.error is not None:
            self.show_error(r.error)
            return
        self._raw_sheet = r.sheet
        self.browser.setText(
            f'<pre style="font-family:{_MONO_STACK}; white-space:pre-wrap; line-height:1.45; margin:0;">'
            + html.escape(r.sheet)
            + '</pre>')
        self.copy_btn.setText('Copy sheet')
        self.copy_btn.setEnabled(bool(r.sheet))
        if r.warnings:
            self.warnings_label.setText('⚠ ' + '\n⚠ '.join(r.warnings))
            self.warnings_label.show()
        else:
            self.warnings_label.setText('')
            self.warnings_label.hide()

    def show_error(self, msg: str) -> None:
        """Render an error inside the telemetry sheet; disable copy."""
        self._raw_sheet = ''
        self.browser.setText(
            f'<pre style="font-family:{_MONO_STACK}; line-height:1.45; margin:0;">'
            f'<span style="color:{_ERROR_ON_SHEET}; font-weight:bold;">'
            f'{html.escape(msg)}</span></pre>')
        self.warnings_label.setText('')
        self.warnings_label.hide()
        self.copy_btn.setText('Copy sheet')
        self.copy_btn.setEnabled(False)

    def clear(self) -> None:
        """Reset the pane to the empty telemetry standby prompt."""
        self._raw_sheet = ''
        self.browser.setHtml(_PLACEHOLDER_HTML)
        self.warnings_label.setText('')
        self.warnings_label.hide()
        self.copy_btn.setText('Copy sheet')
        self.copy_btn.setEnabled(False)

    # ------------------------------------------------------------- actions

    def _copy(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.clipboard().setText(self._raw_sheet)
        if self._raw_sheet:
            self.copy_btn.setText('Copied ✓')
            QTimer.singleShot(1200, self._restore_copy_btn)

    def _restore_copy_btn(self) -> None:
        try:
            self.copy_btn.setText('Copy sheet')
        except RuntimeError:
            pass
