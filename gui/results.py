"""Results pane (Task 6): warnings label + white sheet browser + copy button.

The browser is the "paper spec sheet": white document panel (theme tokens
`sheet-bg`/`sheet-text` via the `sheetBrowser` objectName), monospace. Errors
are rendered INSIDE the white sheet in `error-on-sheet` #c62828 — Qt cannot
style QTextBrowser HTML spans through QSS, so the color is applied inline in
the HTML we set.
"""
import html
from typing import Optional

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

# Design Spec token: error text on the white sheet (inline — QSS cannot target
# browser HTML spans).
_ERROR_ON_SHEET = '#c62828'


class ResultsView(QWidget):
    """Right pane: amber warnings label, white monospace sheet browser, and a
    copy-to-clipboard button for the raw sheet text."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._raw_sheet = ''

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.warnings_label = QLabel()
        self.warnings_label.setObjectName('warningsLabel')  # theme: amber bold
        self.warnings_label.setWordWrap(True)
        self.warnings_label.hide()  # shown only when there is something to warn
        root.addWidget(self.warnings_label)

        self.browser = QTextBrowser()
        self.browser.setObjectName('sheetBrowser')  # theme: white bg, mono 12.5px
        self.browser.setOpenExternalLinks(False)
        root.addWidget(self.browser, 1)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self.copy_btn = QPushButton('Copy sheet')
        self.copy_btn.clicked.connect(self._copy)
        bar.addWidget(self.copy_btn)
        root.addLayout(bar)

    # ------------------------------------------------------------- rendering

    def show_result(self, r: GuiResult) -> None:
        """Render `r`: sheet + warnings; error results route to show_error()."""
        if r.error is not None:
            self.show_error(r.error)
            return
        self._raw_sheet = r.sheet
        self.browser.setText(
            '<pre style="font-family: monospace; margin: 0;">'
            + html.escape(r.sheet)
            + '</pre>')
        if r.warnings:
            self.warnings_label.setText('⚠ ' + '\n⚠ '.join(r.warnings))
            self.warnings_label.show()
        else:
            self.warnings_label.setText('')
            self.warnings_label.hide()

    def show_error(self, msg: str) -> None:
        """Render an error inside the white sheet (error-on-sheet red); the
        sheet is cleared and copy is disabled."""
        self._raw_sheet = ''
        self.browser.setText(
            f'<pre style="font-family: monospace; margin: 0;">'
            f'<span style="color:{_ERROR_ON_SHEET}; font-weight: bold;">'
            f'{html.escape(msg)}</span></pre>')
        self.warnings_label.setText('')
        self.warnings_label.hide()
        self.copy_btn.setEnabled(False)

    def clear(self) -> None:
        """Empty the pane and restore the copy button."""
        self._raw_sheet = ''
        self.browser.clear()
        self.warnings_label.setText('')
        self.warnings_label.hide()
        self.copy_btn.setEnabled(True)

    # ------------------------------------------------------------- actions

    def _copy(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.clipboard().setText(self._raw_sheet)
