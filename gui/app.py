"""GT7 Suspension Tuner — MainWindow + app entry point (Task 6).

`MainWindow` wires the left `SetupForm` (in a scroll area) and the right
`ResultsView` through a `QSplitter`, with a bottom bar holding the Compute
button and status label. Compute runs `TuningService.compute()` on a worker
`QObject` moved to a `QThread` so the heavy solver never blocks the event
loop; the cross-thread `finished`/`failed` signals are queued by default.
"""
import time
from typing import Optional

from PyQt6.QtCore import QThread, QTimer, Qt
from PyQt6.QtGui import QCloseEvent
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

# closeEvent: how long (s) to wait for a running solve thread before the
# close is blocked (event ignored) so the window stays open.
_CLOSE_WAIT_S = 1.5


class MainWindow(QMainWindow):
    """Top-level window: form (left) / results (right) + compute bar (bottom)."""

    def __init__(self, service: Optional[TuningService] = None) -> None:
        super().__init__()
        self.service = service if service is not None else TuningService()
        self._thread: Optional[QThread] = None
        self._worker = None  # keep the worker alive until its thread ends
        self._in_flight = False  # True while a solve thread runs
        self._closing = False  # re-entrancy guard for closeEvent

        self.setWindowTitle('GT7 Suspension Tuner')

        central = QWidget()
        central.setObjectName('centralPane')
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        self.form = SetupForm(self.service)
        self.results = ResultsView()
        root.addWidget(self._build_splitter(), 1)
        root.addLayout(self._build_bottom_bar())
        self.setCentralWidget(central)

    def _build_splitter(self) -> QSplitter:
        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(450)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.addWidget(scroll)
        splitter.addWidget(self.results)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([470, 870])
        return splitter

    def _build_bottom_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(12)
        self.compute_btn = QPushButton('Compute Setup')
        self.compute_btn.setObjectName('computeButton')
        self.compute_btn.clicked.connect(self._on_compute)
        bar.addWidget(self.compute_btn)
        self.status = QLabel()
        self.status.setObjectName('statusLabel')
        self.status.setWordWrap(True)
        bar.addWidget(self.status, 1)
        return bar

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
        thread.finished.connect(self._on_thread_stopped)
        worker.moveToThread(thread)
        self._thread = thread
        self._worker = worker  # prevent GC mid-run (C++ object dies → hang)
        self._in_flight = True  # closed only once the thread is stopped
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
                self._set_status(f'{n} input warning(s) — check ranges/calibration', 'warn')
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

    def _on_thread_stopped(self) -> None:
        """Thread fully stopped (queued cross-thread ``thread.finished``):
        the solve is done, so a pending/next close may proceed."""
        self._in_flight = False

    # ------------------------------------------------------------- close

    def closeEvent(self, event: QCloseEvent) -> None:
        """Only close once the solve thread has *stopped* (bounded wait)."""
        if not self._in_flight:
            event.accept()
            return
        if self._closing:
            event.ignore()
            return
        self._closing = True
        self._set_status('Solve in progress — finishing before close…', 'warn')
        try:
            self._wait_for_thread()
            if self._in_flight:
                event.ignore()
            else:
                self._thread = None
                self._worker = None
                event.accept()
        finally:
            self._closing = False

    def _wait_for_thread(self) -> None:
        deadline = time.monotonic() + _CLOSE_WAIT_S
        app = QApplication.instance()
        while self._in_flight and time.monotonic() < deadline:
            thread = self._thread
            if thread is not None and thread.isRunning():
                thread.quit()
                if thread.wait(50) and app is not None:
                    app.processEvents()
            if app is not None:
                app.processEvents()
            time.sleep(0.005)


def main(auto_quit: int = 0) -> int:
    """Create the app, apply the theme, show the window, run the event loop."""
    app = QApplication([])
    gui.theme.apply(app)
    win = MainWindow()
    win.resize(1340, 860)
    win.show()
    if auto_quit > 0:
        QTimer.singleShot(auto_quit, app.quit)
    return app.exec()
