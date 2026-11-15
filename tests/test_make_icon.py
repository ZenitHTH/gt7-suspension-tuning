"""Tests for scripts.make_icon (AppImage icon generator)."""
import os
import struct
import sys
import tempfile
import unittest
import zlib
from importlib import util as _importlib_util
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

_spec = _importlib_util.spec_from_file_location(
    'make_icon', os.path.join(BASE_DIR, 'scripts', 'make_icon.py'))
make_icon = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(make_icon)


class TestMakeIcon(unittest.TestCase):
    def test_writes_valid_png(self):
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        try:
            make_icon.make_icon(path, size=64)
            data = Path(path).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            w, h = struct.unpack('>II', data[16:24])
            self.assertEqual((w, h), (64, 64))
            self.assertIn(b'IEND', data)
        finally:
            os.unlink(path)

    def test_creates_valid_png_with_exact_idat_scanline_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'icon.png')
            make_icon.make_icon(path, size=64)
            data = Path(path).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            w, h = struct.unpack('>II', data[16:24])
            self.assertEqual((w, h), (64, 64))
            # IDAT starts immediately after 8-byte PNG signature + 25-byte IHDR chunk.
            idat_len = struct.unpack('>I', data[33:37])[0]
            self.assertEqual(data[37:41], b'IDAT')
            raw = zlib.decompress(data[41:41 + idat_len])
            self.assertEqual(len(raw), 64 * (1 + 3 * 64))


if __name__ == '__main__':
    unittest.main()
