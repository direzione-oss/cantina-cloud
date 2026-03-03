"""
Modulo client Supabase per Le Cantine di Gian Carlo.
Gestisce connessione, CRUD e storage immagini.
"""
import streamlit as st
from supabase import create_client, Client

# ── Inizializzazione ──────────────────────────────────────────────────────────

@st.cache_resource
def init_supabase() -> Client:
    """Crea e restituisce il client Supabase (cached)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

BUCKET = "cantina-images"

# ── CRUD Generiche ────────────────────────────────────────────────────────────

def get_all(table: str) -> list[dict]:
    """Legge tutti i record da una tabella, ordinati per id."""
    sb = init_supabase()
    resp = sb.table(table).select("*").order("id").execute()
    return resp.data or []

def insert_record(table: str, data: dict) -> dict:
    """Inserisce un record e ritorna il record appena creato."""
    sb = init_supabase()
    resp = sb.table(table).insert(data).execute()
    return resp.data[0] if resp.data else {}

def update_record(table: str, record_id: int, data: dict) -> dict:
    """Aggiorna un record per ID."""
    sb = init_supabase()
    resp = sb.table(table).update(data).eq("id", record_id).execute()
    return resp.data[0] if resp.data else {}

def delete_record(table: str, record_id: int):
    """Elimina un record per ID."""
    sb = init_supabase()
    sb.table(table).delete().eq("id", record_id).execute()

# ── Storage Immagini ──────────────────────────────────────────────────────────

def upload_image(file_bytes: bytes, filename: str, folder: str = "vini") -> str:
    """
    Carica un'immagine su Supabase Storage e ritorna l'URL pubblico.
    folder: 'vini' o 'mignon'
    """
    sb = init_supabase()
    path = f"{folder}/{filename}"
    # Rimuovi file esistente (ignora errore se non esiste)
    try:
        sb.storage.from_(BUCKET).remove([path])
    except:
        pass
    sb.storage.from_(BUCKET).upload(path, file_bytes, file_options={"content-type": "image/jpeg"})
    return get_public_url(path)

def get_public_url(path: str) -> str:
    """Genera l'URL pubblico di un file nello storage."""
    sb = init_supabase()
    return sb.storage.from_(BUCKET).get_public_url(path)
