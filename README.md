# Lekkerladen for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/fclage/FCL.HA.Lekkerladen?include_prereleases)](https://github.com/fclage/FCL.HA.Lekkerladen/releases)
[![HA](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Unofficial custom integration for [Lekkerladen](https://www.lekkerladen.com/) — Dutch **ERE** compensation for home EV charging. It logs in the same way as the Lekkerladen app: your email, then a 6-digit code from the inbox.

**Not affiliated with Lekkerladen.** Reverse-engineered from the public web app. Use at your own risk.

Built with **agentic coding** using **Grok 4.6** (xAI).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=fclage&repository=FCL.HA.Lekkerladen&category=integration)

## Install with HACS (recommended)

1. Install [HACS](https://hacs.xyz/) if you do not have it yet.
2. Click the badge above, **or** in Home Assistant: **HACS → Integrations → ⋮ → Custom repositories**
   - Repository: `https://github.com/fclage/FCL.HA.Lekkerladen`
   - Type: **Integration**
3. Find **Lekkerladen** in HACS and download it.
4. Restart Home Assistant.
5. **Settings → Devices & services → Add integration → Lekkerladen**

### Manual install

Copy `custom_components/lekkerladen` into your Home Assistant config:

```text
<config>/custom_components/lekkerladen/
```

Restart Home Assistant, then add the integration from the UI.

## Setup

1. Enter the email address of your Lekkerladen account.
2. Wait for the 6-digit login code (same mail as [app.lekkerladen.com/inloggen](https://app.lekkerladen.com/inloggen)).
3. Paste the code. Home Assistant stores the session token, not the code.

The Lekkerladen session lasts about **7 days**. When it expires, Home Assistant asks you to re-authenticate (new email code).

## What you get

Polled every 15 minutes from `api.lekkerladen.com`:

| Entity | Meaning |
|--------|---------|
| Month / year energy | kWh of certified home sessions |
| Month / year sessions | Session counts |
| ERE price | Live € per ERE |
| ERE per kWh | Gross €/kWh from Lekkerladen |
| Net per kWh | Gross €/kWh after Lekkerladen commission |
| Month / year estimated payout | Energy × net €/kWh (**estimate**, not a bank payout) |
| Contract active / expires | Current mandate |
| Provider last fetched / token valid | Linked charger-provider OAuth (e.g. Tesla) |
| Login session expires | When you need a new email code |
| Per charger | Latest session energy + timestamps, serial, MID certified |

Payout sensors are estimates from the published rate. Actual settlement follows Lekkerladen’s trading calendar.

## Requirements

- Home Assistant **2024.12** or newer (tested against 2026.8)
- A Lekkerladen account
- Internet access from the Home Assistant host to `app.lekkerladen.com` and `api.lekkerladen.com`

No extra Python packages. The integration uses `aiohttp`, which ships with Home Assistant.

## Snapshots
<img width="1539" height="976" alt="image" src="https://github.com/user-attachments/assets/f1a72891-610c-4eeb-8c9a-8ee280717b0d" />


## Privacy

Diagnostics redact the session token, email, EAN, phone, and address. Do not commit tokens or OTP codes.

## Development

```bash
python -m unittest discover -s tests -v
```

Bump the integration version on **every** user-facing change (see [CONTRIBUTING.md](CONTRIBUTING.md)):

```bash
python scripts/bump_version.py 0.1.1
```

API notes: [docs/api.md](docs/api.md).

## License

[MIT](LICENSE)
