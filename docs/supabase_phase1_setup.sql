-- SNA AI Agent Studio — Supabase foundation setup
-- Run this in Supabase SQL Editor (Project → SQL Editor → New query)
-- Phase 1: workspace isolation + RLS so authenticated users can create workspaces

-- ========== 1) Ensure required tables / columns ==========
CREATE TABLE IF NOT EXISTS public.businesses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  owner_auth_user_id uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS owner_auth_user_id uuid REFERENCES auth.users(id);

ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';

ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS name text;

CREATE TABLE IF NOT EXISTS public.users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid REFERENCES public.businesses(id),
  auth_user_id uuid REFERENCES auth.users(id),
  name text,
  email text,
  role text DEFAULT 'owner',
  status text DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS business_id uuid;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS auth_user_id uuid;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role text DEFAULT 'owner';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';

CREATE TABLE IF NOT EXISTS public.agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid REFERENCES public.businesses(id),
  name text NOT NULL,
  description text DEFAULT '',
  system_prompt text,
  configuration jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS business_id uuid;
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS description text DEFAULT '';
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS system_prompt text;
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS configuration jsonb DEFAULT '{}'::jsonb;
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
ALTER TABLE public.agents ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

CREATE TABLE IF NOT EXISTS public.prospects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid REFERENCES public.businesses(id),
  name text NOT NULL,
  segment text DEFAULT 'services',
  city text DEFAULT '',
  website text DEFAULT '',
  contact_name text DEFAULT '',
  contact_email text DEFAULT '',
  contact_phone text DEFAULT '',
  source_url text DEFAULT '',
  evidence text DEFAULT '',
  score int DEFAULT 0,
  stage text DEFAULT 'researched',
  notes text DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS business_id uuid;
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS segment text DEFAULT 'services';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS city text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS website text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS contact_name text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS contact_email text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS contact_phone text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS source_url text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS evidence text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS score int DEFAULT 0;
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS stage text DEFAULT 'researched';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS notes text DEFAULT '';
ALTER TABLE public.prospects ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

-- ========== 2) Enable RLS ==========
ALTER TABLE public.businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prospects ENABLE ROW LEVEL SECURITY;

-- ========== 3) Drop old policies if re-running ==========
DROP POLICY IF EXISTS "authenticated_insert_businesses" ON public.businesses;
DROP POLICY IF EXISTS "authenticated_select_businesses" ON public.businesses;
DROP POLICY IF EXISTS "authenticated_update_businesses" ON public.businesses;
DROP POLICY IF EXISTS "authenticated_insert_users" ON public.users;
DROP POLICY IF EXISTS "authenticated_select_users" ON public.users;
DROP POLICY IF EXISTS "authenticated_update_users" ON public.users;
DROP POLICY IF EXISTS "authenticated_all_agents" ON public.agents;
DROP POLICY IF EXISTS "authenticated_all_prospects" ON public.prospects;

-- ========== 4) Policies: businesses ==========
CREATE POLICY "authenticated_insert_businesses"
ON public.businesses FOR INSERT TO authenticated
WITH CHECK (auth.uid() = owner_auth_user_id);

CREATE POLICY "authenticated_select_businesses"
ON public.businesses FOR SELECT TO authenticated
USING (auth.uid() = owner_auth_user_id);

CREATE POLICY "authenticated_update_businesses"
ON public.businesses FOR UPDATE TO authenticated
USING (auth.uid() = owner_auth_user_id)
WITH CHECK (auth.uid() = owner_auth_user_id);

-- ========== 5) Policies: users ==========
CREATE POLICY "authenticated_insert_users"
ON public.users FOR INSERT TO authenticated
WITH CHECK (auth.uid() = auth_user_id);

CREATE POLICY "authenticated_select_users"
ON public.users FOR SELECT TO authenticated
USING (auth.uid() = auth_user_id);

CREATE POLICY "authenticated_update_users"
ON public.users FOR UPDATE TO authenticated
USING (auth.uid() = auth_user_id)
WITH CHECK (auth.uid() = auth_user_id);

-- ========== 6) Policies: agents ==========
CREATE POLICY "authenticated_all_agents"
ON public.agents FOR ALL TO authenticated
USING (
  business_id IN (
    SELECT business_id FROM public.users WHERE auth_user_id = auth.uid()
  )
)
WITH CHECK (
  business_id IN (
    SELECT business_id FROM public.users WHERE auth_user_id = auth.uid()
  )
);

-- ========== 7) Policies: prospects ==========
CREATE POLICY "authenticated_all_prospects"
ON public.prospects FOR ALL TO authenticated
USING (
  business_id IN (
    SELECT business_id FROM public.users WHERE auth_user_id = auth.uid()
  )
)
WITH CHECK (
  business_id IN (
    SELECT business_id FROM public.users WHERE auth_user_id = auth.uid()
  )
);

-- ========== 8) Indexes ==========
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON public.users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_users_business_id ON public.users(business_id);
CREATE INDEX IF NOT EXISTS idx_businesses_owner ON public.businesses(owner_auth_user_id);
CREATE INDEX IF NOT EXISTS idx_agents_business_id ON public.agents(business_id);
CREATE INDEX IF NOT EXISTS idx_prospects_business_id ON public.prospects(business_id);
