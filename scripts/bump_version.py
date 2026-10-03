#!/usr/bin/env python3
"""Bump integration version in manifest.json and const.py.

Usage: python scripts/bump_version.py 0.1.1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
MANIFEST_VERSION_RE = re.compile(r'("version"\s*:\s*")(\d+\.\d+\.\d+)(")')
CONST_VERSION_RE = re.compile(
    r'^(VERSION: Final = ")(\d+\.\d+\.\d+)(")\s*$',
    re.MULTILINE,
)


def repo_file(*parts: str) -> Path:
    """Resolve a repository path and refuse one that leaves ROOT."""
    root = ROOT.resolve()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise RuntimeError(f"Refusing to write outside the repository: {path}")
    return path


def require_version(raw: str) -> str:
    matched = VERSION_RE.fullmatch(raw)
    if matched is None:
        return ""
    return matched.group(0)


def replace_version(path: Path, pattern: re.Pattern[str], version: str, label: str) -> str:
    text = path.read_text(encoding="utf-8")
    found = pattern.search(text)
    if found is None:
        print(f"Could not update version in {label}", file=sys.stderr)
        raise SystemExit(1)
    old = found.group(2)
    updated = pattern.sub(rf"\g<1>{version}\g<3>", text, count=1)
    path.write_text(updated, encoding="utf-8")
    return old


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/bump_version.py <major.minor.patch>",
            file=sys.stderr,
        )
        return 2
    version = require_version(sys.argv[1])
    if not version:
        print(
            "Usage: python scripts/bump_version.py <major.minor.patch>",
            file=sys.stderr,
        )
        return 2

    manifest = repo_file("custom_components", "lekkerladen", "manifest.json")
    const = repo_file("custom_components", "lekkerladen", "const.py")
    old = replace_version(manifest, MANIFEST_VERSION_RE, version, manifest.name)
    replace_version(const, CONST_VERSION_RE, version, const.name)

    print(f"Version {old} → {version}")
    print("Next:")
    print(f"  git commit -am 'Release {version}'")
    print(f"  git tag v{version}")
    print("  git push origin main --tags")
    print(f"  gh release create v{version} --title {version} --generate-notes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
