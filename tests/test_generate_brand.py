"""Brand image helpers. Tests write to a temp directory, not the repo."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import ImageFont

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_brand  # noqa: E402


class GenerateBrandTest(unittest.TestCase):
    def test_icon_and_logo(self) -> None:
        icon = generate_brand.make_icon(64)
        dark = generate_brand.make_icon(64, dark=True)
        self.assertEqual(icon.size, (64, 64))
        self.assertEqual(icon.mode, "RGBA")
        self.assertNotEqual(icon.getpixel((32, 32)), dark.getpixel((32, 32)))
        logo = generate_brand.make_logo(64)
        night = generate_brand.make_logo(64, dark=True)
        self.assertGreater(logo.size[0], 64)
        self.assertEqual(logo.size[1], 64)
        self.assertEqual(night.mode, "RGBA")

    def test_save_png_creates_parents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "icon.png"
            generate_brand.save_png(generate_brand.make_icon(32), path)
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)

    def test_font_fallback(self) -> None:
        seen: list[str] = []
        original = ImageFont.truetype

        def missing_then_last(name: object, size: int = 0, **kwargs: object) -> object:
            if not isinstance(name, str):
                return original(name, size, **kwargs)
            seen.append(name)
            if name != "calibri.ttf":
                raise OSError(name)
            return original(name, size, **kwargs)

        with patch("generate_brand.ImageFont.truetype", missing_then_last):
            self.assertIsNotNone(generate_brand._font(12))
        self.assertEqual(
            seen,
            ["segoeui.ttf", "SegoeUI.ttf", "arial.ttf", "Arial.ttf", "calibri.ttf"],
        )

        def always_missing(name: object, size: int = 0, **kwargs: object) -> object:
            if isinstance(name, str):
                raise OSError(name)
            return original(name, size, **kwargs)

        with patch("generate_brand.ImageFont.truetype", always_missing):
            self.assertIsNotNone(generate_brand._font(12))

    def test_main_writes_eight_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with (
                patch.object(generate_brand, "OUT", out),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                generate_brand.main()
            names = sorted(path.name for path in out.iterdir())
        self.assertEqual(
            names,
            [
                "dark_icon.png",
                "dark_icon@2x.png",
                "dark_logo.png",
                "dark_logo@2x.png",
                "icon.png",
                "icon@2x.png",
                "logo.png",
                "logo@2x.png",
            ],
        )
