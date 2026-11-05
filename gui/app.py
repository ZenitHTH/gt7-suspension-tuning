"""GT7 Suspension Tuner — MainWindow + app entry point (Task 6).

`MainWindow` wires the left `SetupForm` (in a scroll area) and the right
`ResultsView` through a `QSplitter`, with a bottom bar holding the Compute
button and status label. Compute runs `TuningService.compute()` on a worker
`QObject` moved to a `QThread` so the heavy solver never blocks the event
loop; the cross-thread `finished`/`failed` signals are queued by default.
"""
from typing import Optional

from PyQt6.QtCore import QThread, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import gui.theme
from gui.form import SetupForm
from gui.request import GuiResult
from gui.results import ResultsView
from gui.service import TuningService, Worker

_STATUS_KINDS = ('ok', 'warn', 'error')


class MainWindow(QMainWindow):
    """Top-level window: form (left) / results (right) + compute bar (bottom)."""

    def __init__(self, service: Optional[TuningService] = None) -> None:
        super().__init__()
        self.service = service if service is not None else TuningService()
        self._thread: Optional[QThread] = None
        self._worker = None  # keep the worker alive until its thread ends

        self.setWindowTitle('GT7 Suspension Tuner')

        central = QWidget()
        root = QVBoxLayout(central)

        self.form = SetupForm(self.service)
        self.results = ResultsView()

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self.results)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 1000])  # design: sheet pane dominates
        root.addWidget(splitter, 1)

        bar = QHBoxLayout()
        self.compute_btn = QPushButton('Compute Setup')
        self.compute_btn.setObjectName('computeButton')  # theme: accent button
        self.compute_btn.clicked.connect(self._on_compute)
        bar.addWidget(self.compute_btn)
        self.status = QLabel()
        self.status.setObjectName('statusLabel')
        bar.addWidget(self.status, 1)
        root.addLayout(bar)

        self.setCentralWidget(central)

    # ------------------------------------------------------------- status

    def _set_status(self, text: str, kind: Optional[str] = None) -> None:
        """Status bar text; kind ∈ {ok, warn, error} drives the theme."""
        for prop in _STATUS_KINDS:
            self.status.setProperty(prop, kind == prop)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.setText(text)

    # ------------------------------------------------------------- compute

    def _on_compute(self) -> None:
        """Validate, then run `compute()` off the UI thread."""
        errors = self.form.validate()
        if errors:
            self._set_status(errors[0], 'error')
            return

        self.results.clear()
        self.compute_btn.setEnabled(False)
        self.compute_btn.setText('Computing…')
        self._set_status('Computing…', None)

        worker = Worker(self.service, self.form.collect())
        thread = QThread(self)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        thread.finished.connect(thread.deleteLater)
        worker.moveToThread(thread)
        self._thread = thread
        self._worker = worker  # prevent GC mid-run (C++ object dies → hang)
        thread.start()

    def _on_finished(self, r: GuiResult) -> None:
        """Worker done (queued cross-thread signal): render + re-enable."""
        if self._thread is not None:
            self._thread.quit()
        self.results.show_result(r)
        self.compute_btn.setEnabled(True)
        self.compute_btn.setText('Compute Setup')
        if r.error is None:
            n = len(r.warnings)
            if n:
                self._set_status(f'{n} warning(s)', 'warn')
            else:
                self._set_status('OK', 'ok')
        else:
            self._set_status(r.error, 'error')

    def _on_failed(self, msg: str) -> None:
        """Belt-and-braces teardown (compute() never raises by contract)."""
        if self._thread is not None:
            self._thread.quit()
        self.results.show_error(msg)
        self.compute_btn.setEnabled(True)
        self.compute_btn.setText('Compute Setup')
        self._set_status(msg, 'error')


def main(auto_quit: int = 0) -> int:
    """Create the app, apply the theme, show the window, run the event loop.

    `auto_quit` (ms): when > 0, schedule app.quit via QTimer.singleShot so the
    window closes by itself (used by the smoke test; `__main__` passes 0 for
    normal use, optionally via the GT7_GUI_AUTO_QUIT_MS env var).
    """
    app = QApplication([])
    gui.theme.apply(app)
    win = MainWindow()
    win.resize(1400, 900)
    win.show()
    if auto_quit > 0:
        QTimer.singleShot(auto_quit, app.quit)
    return app.exec()
