-- =====================================================================
-- CantinaPro SaaS — SQL Schema Multi-Tenant
-- Da eseguire nell'SQL Editor di Supabase
-- =====================================================================

-- 1) Tabella tenants (clienti / utenti)
-- =====================================================================
CREATE TABLE IF NOT EXISTS tenants (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome          TEXT NOT NULL,
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  ruolo         TEXT DEFAULT 'admin',        -- 'superadmin' | 'admin' | 'viewer'
  attivo        BOOLEAN DEFAULT true,
  piano         TEXT DEFAULT 'base',         -- 'base' | 'pro' | 'enterprise'
  portale_attivo BOOLEAN DEFAULT false,
  portale_slug  TEXT UNIQUE,                 -- es. "cantina-gianCarlo"
  logo_url      TEXT DEFAULT '',
  telefono      TEXT DEFAULT '',
  note_admin    TEXT DEFAULT '',
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 2) Aggiungi tenant_id alle tabelle esistenti
-- =====================================================================
ALTER TABLE vini   ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE mignon ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

-- 3) Policy RLS aggiornate
-- =====================================================================
-- (Le policy esistenti "allow_all" restano per ora — in produzione
--  andrebbero rafforzate con auth.uid() = tenant_id)

-- 4) Index per performance
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_vini_tenant    ON vini(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mignon_tenant  ON mignon(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_email  ON tenants(email);
CREATE INDEX IF NOT EXISTS idx_tenants_slug   ON tenants(portale_slug);

-- Policy tenants (accesso libero per ora, gestito a livello applicativo)
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_tenants" ON tenants FOR ALL TO anon USING (true) WITH CHECK (true);
