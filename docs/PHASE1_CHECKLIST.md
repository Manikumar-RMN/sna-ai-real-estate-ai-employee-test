# Phase 1 — Foundation checklist

Follow the product guide: verify sign-up, sign-in, workspace, session, sign-out, isolation.

## 1. Supabase SQL (required)

1. Open Supabase → **SQL Editor** → New query
2. Paste and run: `docs/supabase_phase1_setup.sql`
3. Confirm no errors

## 2. Auth URL config

**Authentication → URL Configuration**

- Site URL: `https://sna-ai-real-estate-ai-employee-test.vercel.app`
- Redirect URLs: same URL and `/**`

## 3. Email confirmation (optional for testing)

**Authentication → Sign In / Providers → Email**

- Confirm email: OFF for fast testing, ON for production-like flow

## 4. App smoke test

1. Create account / Sign in
2. Set up workspace (name + business name)
3. Save an AI employee
4. Run lead qualification (demo, no login required)
5. Sign out and sign in again — workspace data still there

## Blockers fixed by this setup

- RLS was blocking `INSERT` on `businesses` / `users`
- Missing columns would cause 400 from PostgREST
