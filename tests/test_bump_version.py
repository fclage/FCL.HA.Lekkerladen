"""Version bump script: accept only x.y.z and stay inside the repo."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bump_version  # noqa: E402


class BumpVersionTest(unittest.TestCase):
    def test_require_version(self) -> None:
        self.assertEqual(bump_version.require_version("1.2.3"), "1.2.3")
        self.assertEqual(bump_version.require_version("01.2.3"), "01.2.3")
        self.assertEqual(bump_version.require_version(""), "")
        self.assertEqual(bump_version.require_version("1.2"), "")
        self.assertEqual(bump_version.require_version("v1.2.3"), "")
        self.assertEqual(bump_version.require_version("../1.2.3"), "")

    def test_repo_file_stays_inside_root(self) -> None:
        manifest = bump_version.repo_file("custom_components", "lekkerladen", "manifest.json")
        self.assertTrue(manifest.is_file())
        self.assertTrue(manifest.is_relative_to(bump_version.ROOT))
        with self.assertRaises(RuntimeError):
            bump_version.repo_file("..", "outside.txt")

    def test_replace_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text('{"version": "0.1.0"}\n', encoding="utf-8")
            old = bump_version.replace_version(
                path, bump_version.MANIFEST_VERSION_RE, "0.2.0", path.name
            )
            self.assertEqual(old, "0.1.0")
            self.assertIn('"0.2.0"', path.read_text(encoding="utf-8"))

            missing = Path(tmp) / "empty.json"
            missing.write_text("{}\n", encoding="utf-8")
            with (
                self.assertRaises(SystemExit) as raised,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                bump_version.replace_version(
                    missing, bump_version.MANIFEST_VERSION_RE, "0.2.0", missing.name
                )
            self.assertEqual(raised.exception.code, 1)

    def test_main_usage(self) -> None:
        cases = (
            ["bump_version.py"],
            ["bump_version.py", "nope"],
            ["bump_version.py", "1.2.3", "extra"],
        )
        for argv in cases:
            with (
                patch.object(sys, "argv", argv),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(bump_version.main(), 2)

    def test_main_writes_temp_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "custom_components" / "lekkerladen"
            package.mkdir(parents=True)
            manifest = package / "manifest.json"
            const = package / "const.py"
            manifest.write_text('{"version": "0.1.0"}\n', encoding="utf-8")
            const.write_text('VERSION: Final = "0.1.0"\n', encoding="utf-8")
            with (
                patch.object(bump_version, "ROOT", root),
                patch.object(sys, "argv", ["bump_version.py", "0.2.0"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(bump_version.main(), 0)
            self.assertIn('"0.2.0"', manifest.read_text(encoding="utf-8"))
            self.assertIn('VERSION: Final = "0.2.0"', const.read_text(encoding="utf-8"))
            self.assertNotIn("0.1.0", manifest.read_text(encoding="utf-8"))
            self.assertNotIn("0.1.0", const.read_text(encoding="utf-8"))
