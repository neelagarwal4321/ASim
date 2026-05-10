# Auth/Login Fix Handoff - 2026-05-09

## Context

Codex ran the current ASim app locally from `C:\Neel\CODING\ASim` without editing unrelated Claude Code work. The frontend rendered, but real login failed and demo login showed dashboard API errors.

Observed runtime state before this fix:

- Vite frontend: `http://127.0.0.1:5173/`
- Node API: `http://127.0.0.1:3000/health`
- `POST /api/v1/auth/login` with a dummy account returned `500`.
- `DATABASE_URL_NODE` pointed to `localhost:5432`, and no Postgres server was listening there.
- `Continue as Demo` stored empty frontend tokens, then `Dashboard.tsx` immediately called `GET /api/v1/simulate`, causing `401` and visible "Failed to load simulations" toasts.
- Google OAuth buttons on login/signup were no-ops.
- Node OAuth callback redirected to `/auth/callback`, but the frontend had no `/auth/callback` route.

## Changes Made

### Node auth behavior

- Added `POST /api/v1/auth/demo` in `server/routes/auth.js`.
  - Returns a signed demo access token and refresh token.
  - Does not touch Postgres.

- Updated `POST /api/v1/auth/refresh` in `server/routes/auth.js`.
  - Demo refresh tokens now rotate without database access.
  - Normal user refresh tokens still use the existing `refresh_tokens` table.

- Refactored session issuing in `server/routes/auth.js`.
  - Email signup/login and OAuth callbacks now use the same refresh-token persistence path.
  - OAuth-created sessions now insert refresh token hashes into `refresh_tokens`, matching email login behavior.

- Added OAuth success redirect handling in `server/routes/auth.js`.
  - Google/GitHub callbacks redirect to frontend `/auth/callback`.
  - Frontend callback base is read from `FRONTEND_URL`, then `OAUTH_FRONTEND_CALLBACK_BASE`, then defaults to `http://localhost:5173`.
  - Keep `OAUTH_CALLBACK_BASE` as the Node/API public base used by Passport callback URLs.

- Updated `server/middleware/errorHandler.js`.
  - Database connectivity failures now return `503`.
  - Auth routes return `{ "error": "Authentication service unavailable" }` instead of a generic `500`.
  - Log formatting now includes actual method/path/message instead of uninterpreted `%s` placeholders.

### Node simulation behavior

- Updated `GET /api/v1/simulate` in `server/routes/simulation.js`.
  - Demo sessions return `{ simulations: [], page, limit }` without querying Postgres.
  - Real user sessions still query Postgres normally.

### Frontend auth behavior

- Exported `API_BASE` from `frontend/src/api/client.ts`.
- Added `demoLogin()` and `getOAuthUrl()` in `frontend/src/api/auth.ts`.
- Updated login page:
  - Google button redirects to `GET /api/v1/auth/oauth/google`.
  - Demo button calls `POST /api/v1/auth/demo`, stores real signed tokens, then navigates to dashboard.
- Updated signup page:
  - Google button redirects to `GET /api/v1/auth/oauth/google`.
- Added `frontend/src/pages/auth/OAuthCallback.tsx`.
  - Reads `accessToken`, `refreshToken`, `email`, and optional `name` from the callback URL.
  - Stores the session in `authStore`.
  - Navigates to `/app/dashboard`.
  - Redirects back to `/login?error=oauth_failed` if callback tokens are missing.
- Added `/auth/callback` route in `frontend/src/App.tsx`.
- Fixed refresh interceptor in `frontend/src/api/client.ts`.
  - Stores the rotated refresh token returned by `/auth/refresh`, not the stale one.

### Environment documentation

- Added `FRONTEND_URL=http://localhost:5173` to `.env.example`.

For local Google OAuth, set:

```env
GOOGLE_CLIENT_ID=<your Google OAuth client id>
GOOGLE_CLIENT_SECRET=<your Google OAuth client secret>
OAUTH_CALLBACK_BASE=http://localhost:3000
FRONTEND_URL=http://localhost:5173
VITE_API_BASE_URL=http://localhost:3000/api/v1
```

In Google Cloud Console, the authorized redirect URI must be:

```text
http://localhost:3000/api/v1/auth/oauth/google/callback
```

## Tests Added

- `server/tests/auth.test.js`
  - Login returns `503` when the DB is unavailable.
  - Demo login returns signed tokens without database access.
  - Demo refresh rotates tokens without database access.

- `server/tests/simulation.test.js`
  - Demo simulation listing returns an empty list without database access.

- `frontend/src/__tests__/api/auth.test.ts`
  - OAuth URL helper points to the Node API.
  - Demo login API helper normalizes the response.

- `frontend/src/__tests__/auth/OAuthCallback.test.tsx`
  - Callback stores tokens and user data.
  - Callback rejects missing tokens.

## Verification Commands Run

```powershell
cd C:\Neel\CODING\ASim\server
npm.cmd test -- auth.test.js simulation.test.js --runInBand
```

Result: 2 test suites passed, 10 tests passed.

```powershell
cd C:\Neel\CODING\ASim\frontend
npm.cmd test -- src/__tests__/api/auth.test.ts src/__tests__/auth/OAuthCallback.test.tsx
```

Result: 2 test files passed, 4 tests passed.

## Remaining Operational Requirement

Real email/password signup/login still requires a reachable Postgres database and migrated tables. This fix changes the failure mode from a generic `500` to a clear `503`, but it does not replace the required database.

Demo login now works without Postgres. Google OAuth still needs Postgres because OAuth users and refresh tokens are persisted by Node, as required by the architecture.
