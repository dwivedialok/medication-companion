#!/usr/bin/env python3
"""
Generate a synthetic prescription image for local smoke tests.

Four curated Indian brands with two known dataset interactions (drugs.db):
  - Ecosprin (aspirin) + Nise (nimesulide)  → HIGH
  - Warf (warfarin) + Flagyl (metronidazole) → HIGH

Within-visit pair count for 4 resolved generics: C(4,2) = 6.

Usage:
    uv run python scripts/generate_smoke_prescription.py
    uv run python scripts/generate_smoke_prescription.py --output data/sample/custom.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit(
        "Pillow is required to generate the image. Run: uv pip install pillow"
    ) from exc

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "sample" / "smoke_4drug_2interactions.png"

LINES = [
    "Dr. R. Sharma, MBBS",
    "City Clinic, Bengaluru",
    "Date: 21-Jun-2026",
    "",
    "Rx",
    "1. Tab Ecosprin 75 mg    — 1 od × 30 days",
    "2. Tab Nise 100 mg       — 1 bd × 5 days",
    "3. Tab Warf 2 mg         — 1 od × 30 days",
    "4. Tab Flagyl 400 mg     — 1 tds × 7 days",
    "",
    "Signature: ____________",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_prescription(output: Path) -> None:
    width, height = 900, 1100
    img = Image.new("RGB", (width, height), color=(252, 250, 245))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(28)
    body_font = _load_font(24)

    draw.rectangle((40, 40, width - 40, height - 40), outline=(120, 120, 120), width=2)
    y = 70
    for line in LINES:
        font = title_font if line.startswith("Dr.") else body_font
        draw.text((70, y), line, fill=(20, 20, 20), font=font)
        y += 44 if line else 20

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, format="PNG", optimize=True)
    print(f"Wrote {output} ({output.stat().st_size // 1024} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output PNG path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    args = parser.parse_args()
    render_prescription(args.output.resolve())


if __name__ == "__main__":
    main()
