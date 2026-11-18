"""Build dist/pkp-departures.zip (flat, as Larapaper and TRMNL expect) from src/."""

import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / "dist" / "pkp-departures.zip"
out.parent.mkdir(exist_ok=True)

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted((root / "src").iterdir()):
        zf.write(f, f.name)

print(out, [n for n in zipfile.ZipFile(out).namelist()])
