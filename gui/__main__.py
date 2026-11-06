import os
import sys

from gui.app import main

# Windows consoles (cp1252/cp874) would otherwise raise UnicodeEncodeError
# on Thai or symbol text and look like a fatal crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if __name__ == '__main__':
    # Passes 0 in normal use; GT7_GUI_AUTO_QUIT_MS lets the smoke test
    # auto-close the offscreen window without changing the launch command.
    auto_quit = int(os.environ.get('GT7_GUI_AUTO_QUIT_MS', '0') or 0)
    raise SystemExit(main(auto_quit=auto_quit))
