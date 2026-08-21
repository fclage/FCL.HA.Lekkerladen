#!/usr/bin/env python3
"""Bump integration version in manifest.json and const.py.

Usage: python scripts/bump_version.py 0.1.1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "lekkerladen" / "manifest.json"
CONST = ROOT / "custom_components" / "lekkerladen" / "const.py"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def main() -> int:
    if len(sys.argv) != 2 or not VERSION_RE.match(sys.argv[1]):
        print("Usage: python scripts/bump_version.py <major.minor.patch>", file=sys.stderr)
        return 2
    version = sys.argv[1]

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old = manifest.get("version")
    manifest["version"] = version
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    const_text = CONST.read_text(encoding="utf-8")
    new_const, n = re.subn(
        r'^VERSION: Final = "[^"]+"',
        f'VERSION: Final = "{version}"',
        const_text,
        count=1,
        flags=re.M,
    )
    if n != 1:
        print("Could not update VERSION in const.py", file=sys.stderr)
        return 1
    CONST.write_text(new_const, encoding="utf-8")

    print(f"Version {old} → {version}")
    print("Next:")
    print(f"  git commit -am 'Release {version}'")
    print(f"  git tag v{version}")
    print("  git push origin main --tags")
    print(f"  gh release create v{version} --title {version} --generate-notes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
