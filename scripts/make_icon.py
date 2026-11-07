"""Generate the GT7Tuner app icon as a PNG (pure stdlib, no PIL needed).

Draws a suspension spring (zigzag) with mount bars on a dark background --
the AppImage/`linuxdeploy` tooling only needs a valid file at the path
referenced by the .desktop `Icon=` entry.

Usage: python scripts/make_icon.py OUT.png [SIZE]
"""
import struct
import sys
import zlib


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack('>I', len(data))
        + tag
        + data
        + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _seg_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    t = ((px - ax) * dx + (py - ay) * dy) / denom if denom else 0.0
    t = max(0.0, min(1.0, t))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def make_icon(path: str, size: int = 256) -> str:
    """Write an RGBA-free RGB PNG to `path`; returns the path."""
    # Zigzag spring, normalized coords (top-left origin).
    spring = [(0.22, 0.78), (0.35, 0.30), (0.50, 0.78), (0.65, 0.30), (0.78, 0.78)]
    # Mount bars above/below the spring ends.
    bars = [(0.22, 0.20, 0.35, 0.20), (0.65, 0.20, 0.78, 0.20),
            (0.22, 0.88, 0.35, 0.88), (0.65, 0.88, 0.78, 0.88)]
    segs = [spring[i] + spring[i + 1] for i in range(len(spring) - 1)] + bars
    segs = [tuple(float(v) * size for v in s) for s in segs]
    width = size * 0.045

    bg = (15, 19, 26)
    fg = (96, 165, 250)
    row = bytearray()
    rows = []
    for y in range(size):
        row.append(0)  # PNG filter type: None
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            near = any(_seg_dist(px, py, *s) <= width for s in segs)
            row.extend(fg if near else bg)
        rows.append(bytes(row))
    raw = b''.join(rows)
    png = (
        b'\x89PNG\r\n\x1a\n'
        + _chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
        + _chunk(b'IDAT', zlib.compress(raw, 9))
        + _chunk(b'IEND', b'')
    )
    with open(path, 'wb') as fh:
        fh.write(png)
    return path


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'GT7Tuner.png'
    sz = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    print(f'wrote {make_icon(out, sz)}')
