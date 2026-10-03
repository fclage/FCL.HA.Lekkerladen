---
name: lekkerladen
description: >
  Maintain the unofficial Lekkerladen Home Assistant custom integration
  (HACS repo FCL.HA.Lekkerladen, domain lekkerladen). Use when changing
  sensors, config flow, API client, version, HACS metadata, brand icons,
  or when the user says Lekkerladen, ERE, ha-lekkerladen, or /lekkerladen.
---

# Lekkerladen HA integration

Repo: **https://github.com/fclage/FCL.HA.Lekkerladen**  
Domain: `lekkerladen`  
HACS type: Integration (`custom_components/lekkerladen/`)  
Not affiliated with Lekkerladen.

## Version on every change

HACS tracks **GitHub releases**, not loose commits.

1. `python scripts/bump_version.py x.y.z` (updates `manifest.json` and `const.py` `VERSION`)
2. Commit, tag `vx.y.z`, `git push --tags`
3. `gh release create vx.y.z --title x.y.z --generate-notes`

Do not ship integration/translation changes under the previous version.

## Layout

| Path | Role |
|------|------|
| `custom_components/lekkerladen/` | HA integration (only subdirectory under `custom_components/`) |
| `custom_components/lekkerladen/brand/` | Local brand images (HA 2026.3+) |
| `hacs.json` | HACS manifest |
| `docs/api.md` | Unofficial API map |
| `tests/` | HA-free unit tests |

## Tests

```bash
python -m pip install pillow tzdata
python -m unittest discover -s tests -v
```

## Auth / API

Email OTP via Better Auth on `app.lekkerladen.com`; data on `api.lekkerladen.com` with `Authorization: Bearer`. Details: `docs/api.md`. Never commit tokens or OTP codes.

## Brand

```bash
python scripts/generate_brand.py
```

Original charging-plug icon — do not copy Lekkerladen’s trademarked wordmark/logo.
