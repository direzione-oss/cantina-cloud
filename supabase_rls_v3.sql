-- =====================================================================
-- CantinaPro SaaS — RLS Policy v3 (SICURA)
-- Da eseguire nell'SQL Editor di Supabase DOPO aver sostituito
-- SUPABASE_KEY in secrets.toml con la SERVICE ROLE KEY.
--
-- ISTRUZIONI:
-- 1. Vai su Supabase > Project Settings > API
-- 2. Copia "service_role secret" (NON la anon key)
-- 3. Metti quella chiave come SUPABASE_KEY in .streamlit/secrets.toml
-- 4. Esegui questo SQL nell'SQL Editor di Supabase
--
-- LOGICA: la service role bypassa automaticamente l'RLS.
-- La anon key (usata da chiunque via API) viene bloccata da default.
-- =====================================================================

-- ── Tabella tenants ──────────────────────────────────────────────────
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Rimuovi policy permissiva esistente
DROP POLICY IF EXISTS "allow_all_tenants" ON tenants;

-- Nessuna policy = accesso anon negato by default (service role bypassa)
-- Se in futuro si vuole un accesso pubblico limitato, aggiungere qui.

-- ── Tabella vini ──────────────────────────────────────────────────────
ALTER TABLE vini ENABLE ROW LEVEL SECURITY;

-- Rimuovi policy permissive esistenti
DROP POLICY IF EXISTS "allow_all" ON vini;
DROP POLICY IF EXISTS "allow_all_vini" ON vini;

-- ── Tabella mignon ────────────────────────────────────────────────────
ALTER TABLE mignon ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "allow_all" ON mignon;
DROP POLICY IF EXISTS "allow_all_mignon" ON mignon;

-- ── Accesso pubblico limitato al portale ospiti ───────────────────────
-- Solo lettura su vini con qta > 0 (per portale pubblico via anon key)
-- OPZIONALE: decommentare se si vuole il portale pubblico funzionante
-- con anon key (richiede separazione delle chiamate autenticate).
--
-- CREATE POLICY "portale_pubblico_vini" ON vini
--   FOR SELECT TO anon
--   USING (qta > 0 AND tipo_cat != 'Provati');

-- ── NOTA FINALE ───────────────────────────────────────────────────────
-- Con service role key nel backend, tutta l'autenticazione/autorizzazione
-- è gestita a livello applicativo (verify_login + tenant_id filtering).
-- Le policy RLS garantiscono che nessun accesso diretto all'API Supabase
-- (via anon key) possa leggere o modificare i dati.
-- =====================================================================
