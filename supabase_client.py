"""
supabase_client.py — CantinaPro SaaS
Client Supabase con supporto multi-tenant, autenticazione custom e CRUD.
"""
import streamlit as st
from supabase import create_client, Client
import hashlib, secrets, time, uuid, datetime

BUCKET = "cantina-images"

# ── Chiavi Supabase (la anon key è una chiave pubblica by design) ─────────────
_SB_URL = "https://ltssduxqpmvuzvpitmpx.supabase.co"
_SB_ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
             ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx0c3NkdXhxcG12dXp2cGl0bXB4"
             "Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI1Nzg2MDIsImV4cCI6MjA4ODE1"
             "NDYwMn0.ufMro1pGIoPiQ4SIKsDVTfqaV9FnadWcSjA1JBgCvhY")

# ── Init ──────────────────────────────────────────────────────────────────────

def _valid_jwt(key: str) -> bool:
    """Controlla che la stringa sia un JWT formato minimo valido."""
    return isinstance(key, str) and key.count('.') == 2 and len(key) > 100

@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL", _SB_URL) or _SB_URL
        key = st.secrets.get("SUPABASE_KEY", _SB_ANON)
    except Exception:
        url, key = _SB_URL, _SB_ANON
    # Se il secret è corrotto o mancante, usa la anon key pubblica
    if not _valid_jwt(key):
        key = _SB_ANON
    return create_client(url, key)

def get_sb() -> Client:
    """Ritorna il client Supabase, ricreandolo se la connessione è stale."""
    try:
        return init_supabase()
    except Exception:
        # Svuota la cache e riprova una volta
        init_supabase.clear()
        return init_supabase()

# ── Auth ──────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(email: str, password: str) -> dict | None:
    """Verifica credenziali e ritorna il tenant (utente) o None."""
    sb = get_sb()
    pw_hash = hash_password(password)
    resp = sb.table("tenants").select("*").eq("email", email).eq("password_hash", pw_hash).eq("attivo", True).execute()
    return resp.data[0] if resp.data else None

def generate_reset_token(email: str) -> str | None:
    """Genera un token di reset password valido 30 minuti. Ritorna il token o None se email non trovata."""
    sb = get_sb()
    resp = sb.table("tenants").select("id").eq("email", email).eq("attivo", True).execute()
    if not resp.data:
        return None  # Non rivela se l'email esiste (sicurezza)
    token = secrets.token_urlsafe(32)
    expires = (datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(minutes=30)).isoformat()
    sb.table("tenants").update({
        "reset_token": token,
        "reset_token_expires": expires
    }).eq("email", email).execute()
    return token

def verify_reset_token(token: str) -> dict | None:
    """Verifica il token di reset e ritorna il tenant se valido e non scaduto."""
    if not token or len(token) < 10:
        return None
    sb = get_sb()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resp = (sb.table("tenants")
            .select("id, email, nome")
            .eq("reset_token", token)
            .gt("reset_token_expires", now)
            .execute())
    return resp.data[0] if resp.data else None

def update_password_by_token(token: str, new_password: str) -> bool:
    """Aggiorna la password e invalida il token. Ritorna True se riuscito."""
    tenant = verify_reset_token(token)
    if not tenant:
        return False
    sb = get_sb()
    sb.table("tenants").update({
        "password_hash": hash_password(new_password),
        "reset_token": None,
        "reset_token_expires": None
    }).eq("id", tenant["id"]).execute()
    return True

def email_exists(email: str) -> bool:
    """Controlla se una email è già registrata."""
    sb = get_sb()
    resp = sb.table("tenants").select("id").eq("email", email).execute()
    return len(resp.data) > 0

# ── Tenants (clienti) ─────────────────────────────────────────────────────────

def get_all_tenants() -> list[dict]:
    sb = get_sb()
    return sb.table("tenants").select("*").order("created_at", desc=True).execute().data or []

def get_tenant(tenant_id: str) -> dict:
    sb = get_sb()
    resp = sb.table("tenants").select("*").eq("id", tenant_id).execute()
    return resp.data[0] if resp.data else {}

def create_tenant(data: dict) -> dict:
    sb = get_sb()
    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))
    resp = sb.table("tenants").insert(data).execute()
    return resp.data[0] if resp.data else {}

def update_tenant(tenant_id: str, data: dict) -> dict:
    sb = get_sb()
    if "password" in data and data["password"]:
        data["password_hash"] = hash_password(data.pop("password"))
    elif "password" in data:
        data.pop("password")
    resp = sb.table("tenants").update(data).eq("id", tenant_id).execute()
    return resp.data[0] if resp.data else {}

def toggle_tenant(tenant_id: str, attivo: bool):
    sb = get_sb()
    sb.table("tenants").update({"attivo": attivo}).eq("id", tenant_id).execute()

def get_tenant_by_slug(slug: str) -> dict:
    sb = get_sb()
    resp = sb.table("tenants").select("*").eq("portale_slug", slug).eq("portale_attivo", True).execute()
    return resp.data[0] if resp.data else {}

def get_tenant_by_slug_lista(slug: str) -> dict:
    """Cerca tenant per slug senza richiedere portale_attivo (usato per lista ospiti QR)."""
    sb = get_sb()
    resp = sb.table("tenants").select("*").eq("portale_slug", slug).eq("attivo", True).execute()
    return resp.data[0] if resp.data else {}

# ── Vini / Mignon (filtrati per tenant) ───────────────────────────────────────

@st.cache_data(ttl=60)
def get_vini(tenant_id: str) -> list[dict]:
    sb = get_sb()
    return sb.table("vini").select("*").eq("tenant_id", tenant_id).order("id").execute().data or []

@st.cache_data(ttl=60)
def get_mignon(tenant_id: str) -> list[dict]:
    sb = get_sb()
    return sb.table("mignon").select("*").eq("tenant_id", tenant_id).order("id").execute().data or []

@st.cache_data(ttl=60)
def get_vini_portale(tenant_id: str) -> list[dict]:
    """Vini pubblici (in vendita) per il portale."""
    sb = get_sb()
    return sb.table("vini").select("*").eq("tenant_id", tenant_id).gt("qta", 0).neq("tipo_cat", "Provati").order("tipo_cat").execute().data or []

def insert_vino(tenant_id: str, data: dict) -> dict:
    sb = get_sb()
    data["tenant_id"] = tenant_id
    resp = sb.table("vini").insert(data).execute()
    return resp.data[0] if resp.data else {}

# Colonne sicure della tabella mignon (esclude campi solo-vini)
MIGNON_COLS = {
    "tenant_id", "nome", "azienda", "annata", "vitigno", "gradi",
    "prezzo", "qta", "formato", "provenienza", "luogo",
    "note", "foto_url", "tipo_cat",
}

def _mignon_payload(data: dict) -> dict:
    """Filtra il payload tenendo solo le colonne della tabella mignon."""
    return {k: v for k, v in data.items() if k in MIGNON_COLS}

def insert_mignon(tenant_id: str, data: dict) -> dict:
    sb = get_sb()
    payload = _mignon_payload(data)
    payload["tenant_id"] = tenant_id
    resp = sb.table("mignon").insert(payload).execute()
    return resp.data[0] if resp.data else {}

def update_vino(record_id: int, tenant_id: str, data: dict) -> dict:
    """Aggiorna un vino verificando l'appartenenza al tenant (previene IDOR)."""
    sb = get_sb()
    resp = (sb.table("vini").update(data)
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)  # isolamento tenant garantito DB-side
            .execute())
    return resp.data[0] if resp.data else {}

def update_mignon(record_id: int, tenant_id: str, data: dict) -> dict:
    """Aggiorna un mignon verificando l'appartenenza al tenant (previene IDOR)."""
    sb = get_sb()
    payload = _mignon_payload(data)
    payload.pop("tenant_id", None)
    resp = (sb.table("mignon").update(payload)
            .eq("id", record_id)
            .eq("tenant_id", tenant_id)  # isolamento tenant garantito DB-side
            .execute())
    return resp.data[0] if resp.data else {}

def delete_vino(record_id: int, tenant_id: str):
    """Elimina un vino verificando l'appartenenza al tenant (previene IDOR)."""
    sb = get_sb()
    sb.table("vini").delete().eq("id", record_id).eq("tenant_id", tenant_id).execute()

def delete_mignon(record_id: int, tenant_id: str):
    """Elimina un mignon verificando l'appartenenza al tenant (previene IDOR)."""
    sb = get_sb()
    sb.table("mignon").delete().eq("id", record_id).eq("tenant_id", tenant_id).execute()

# ── Storage ───────────────────────────────────────────────────────────────────

def upload_image(file_bytes: bytes, filename: str, folder: str = "vini") -> str:
    sb = get_sb()
    path = f"{folder}/{filename}"
    try:
        sb.storage.from_(BUCKET).remove([path])
    except Exception:
        pass  # File non esistente, procediamo
    sb.storage.from_(BUCKET).upload(path, file_bytes, file_options={"content-type": "image/jpeg"})
    return sb.storage.from_(BUCKET).get_public_url(path)

def get_public_url(path: str) -> str:
    sb = get_sb()
    return sb.storage.from_(BUCKET).get_public_url(path)

# ── Statistiche globali (superadmin) ─────────────────────────────────────────

def get_stats_globali() -> dict:
    sb = get_sb()
    tenants = sb.table("tenants").select("id", count="exact").eq("attivo", True).execute()
    vini = sb.table("vini").select("qta, prezzo", count="exact").gt("qta", 0).neq("tipo_cat","Provati").execute()
    tot_bottiglie = sum(int(v.get("qta", 0)) for v in (vini.data or []))
    tot_valore = sum(int(v.get("qta", 0)) * float(str(v.get("prezzo", 0)).replace(",", ".")) for v in (vini.data or []))
    return {
        "n_clienti": tenants.count or 0,
        "n_bottiglie": tot_bottiglie,
        "valore_totale": tot_valore,
        "n_vini_records": vini.count or 0,
    }

# Legacy API rimossa: usava accesso diretto senza verifica tenant.
# Usare le funzioni specifiche (get_vini, update_vino, delete_vino, ecc.)
