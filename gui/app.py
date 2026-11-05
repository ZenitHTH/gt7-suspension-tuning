"""Minimal skeleton GUI entry point (Task 1).

Launches a themed empty window. Later tasks build the form/results on top.
"""
import gui.theme
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow


def main(auto_quit: int = 0) -> int:
    """Create the app, apply the theme, show the window, run the event loop.

    `auto_quit` (ms): when > 0, schedule app.quit via QTimer.singleShot so the
    window closes by itself (used by the smoke test; `__main__` passes 0 for
    normal use, optionally via the GT7_GUI_AUTO_QUIT_MS env var).
    """
    app = QApplication([])
    gui.theme.apply(app)
    win = QMainWindow()
    win.setWindowTitle("GT7 Suspension Tuner")
    win.resize(600, 400)
    win.show()
    if auto_quit > 0:
        QTimer.singleShot(auto_quit, app.quit)
    return app.exec()

