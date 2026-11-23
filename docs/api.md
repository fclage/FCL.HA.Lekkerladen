# Lekkerladen API (unofficial)

Reverse-engineered from [app.lekkerladen.com](https://app.lekkerladen.com/) (Vite SPA + Better Auth + Hono RPC). Not a public documented API. Paths can change without notice.

## Hosts

| Role | Base URL |
|------|----------|
| Web app + auth | `https://app.lekkerladen.com` |
| Data API | `https://api.lekkerladen.com` |

Auth client in the SPA: Better Auth `baseURL = APP_URL`, `basePath = /auth`. Data client sends `Authorization: Bearer <session.token>`.

## Login (email OTP)

Same flow as **Inloggen** in the app.

1. **Send code**

   `POST https://app.lekkerladen.com/auth/email-otp/send-verification-otp`

   ```json
   { "email": "user@example.com", "type": "sign-in" }
   ```

   Header: `X-Sign-Up-Flow: false`

2. **Verify code**

   `POST https://app.lekkerladen.com/auth/sign-in/email-otp`

   ```json
   { "email": "user@example.com", "otp": "123456" }
   ```

   Response includes `{ "token": "...", "user": { "id", "email", ... } }`.

3. **Session**

   `GET https://app.lekkerladen.com/auth/get-session`  
   `Authorization: Bearer <token>`

   Returns `{ session: { token, expiresAt, ... }, user: { ... } }` or `null`.

Sessions last about seven days (`expiresAt`). Home Assistant triggers re-auth on HTTP 401.

## Data (Bearer token)

| Method | Path | Used for |
|--------|------|----------|
| GET | `/api/chargers` | Charger list |
| GET | `/api/accounts` | Linked provider OAuth |
| GET | `/api/profiles/current` | Profile (payout frequency, partner) |
| GET | `/api/ere-rate` | `{ date, erePrice, perKwh }` |
| GET | `/api/contracts/current` | Mandate (EAN, commission, expiry) |
| GET | `/api/sessions/monthly` | Monthly kWh + session counts |
| GET | `/api/sessions/years` | Years that have session data (ints) |
| GET | `/api/sessions/years/{year}` | Sessions for that calendar year |

`POST /api/sessions` (`{ "limit": 20 }`) was removed by Lekkerladen and now returns 404.
The web app lists recent sessions via `GET /api/sessions/years` and `GET /api/sessions/years/{year}`.
Session objects still include `energyDeliveredKwh`, `startTime`, `endTime`, `sessionId`, and `chargerId`.
As of 0.1.1 the integration uses the year endpoint (newest first). A failure there is logged and the rest of the dashboard still loads.

Chargers use ids like `tesla:<remoteId>`. Session `chargerId` matches `remoteId`.

Estimated payout in this integration:

```text
net_eur_per_kwh = ere_rate.perKwh * (1 - mandate.commissionRate)
payout = energy_kwh * net_eur_per_kwh
```

That is **not** a guaranteed bank payout.

## Other RPC paths (not polled)

The SPA also calls charger-document uploads, OCPP import, referrals, rewards, zipcode/EAN lookup, and partner onboarding. Those are out of scope for v0.1.
