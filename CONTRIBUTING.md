# Contributing

This is a Home Assistant **custom integration**. HACS installs it from GitHub **releases**.

## Version on every change

**Update the plugin version whenever you ship a change.** HACS users only see a new version when `manifest.json` and a GitHub release tag move together.

Current version lives in two places (keep them identical):

| File | Field |
|------|--------|
| `custom_components/lekkerladen/manifest.json` | `"version"` |
| `custom_components/lekkerladen/const.py` | `VERSION` |

`USER_AGENT` is derived from `VERSION`.

Helper:

```bash
python scripts/bump_version.py 0.1.1
```

Then:

```bash
git add custom_components/lekkerladen/manifest.json custom_components/lekkerladen/const.py
git commit -m "Release 0.1.1"
git tag v0.1.1
git push origin main --tags
gh release create v0.1.1 --title "0.1.1" --generate-notes
```

Use [semver](https://semver.org/):

- **patch** (`0.1.1`) — bugfixes, docs, translations
- **minor** (`0.2.0`) — new sensors or config-flow steps
- **major** (`1.0.0`) — breaking entity/config changes

Do not push to `main` with a changed integration and the same `0.1.0`.

## Tests

```bash
python -m unittest discover -s tests -v
```

No Home Assistant install is required for these tests.

## Secrets

Never commit session tokens, OTP codes, or live account dumps. Diagnostics already redact token, email, EAN, phone, and address.

## Brand images

Icons live in `custom_components/lekkerladen/brand/` (Home Assistant 2026.3+ local brands).

```bash
python scripts/generate_brand.py
```

## Pull requests

- One concern per PR
- Include a version bump if the integration code or translations change
- Unofficial API: if Lekkerladen changes endpoints, update `const.py` / `api.py` and `docs/api.md`
