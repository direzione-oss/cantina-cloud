"""
supabase_client.py — CantinaPro SaaS (Persistenza SQLite + Storage Locale VPS)
Client database locale con supporto multi-tenant, autenticazione custom, CRUD e immagini.
"""
import os
import json
import shutil
import sqlite3
import hashlib
import secrets
import datetime
import bcrypt
import streamlit as st

BUCKET = "cantina-images"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_DIR = os.path.join(BASE_DIR, "seed_storage")
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "storage"))
IMAGES_DIR = os.path.join(DATA_DIR, "images")
DB_PATH = os.path.join(DATA_DIR, "cantina.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")


def _ensure_storage():
    """Inizializza la cartella storage persistente copiando i dati seed al primo avvio."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(IMAGES_DIR, "vini"), exist_ok=True)
    os.makedirs(os.path.join(IMAGES_DIR, "mignon"), exist_ok=True)

    # Se esiste seed_storage (nel container Docker), copia DB e immagini mancanti
    if os.path.exists(SEED_DIR) and os.path.abspath(SEED_DIR) != os.path.abspath(DATA_DIR):
        seed_db = os.path.join(SEED_DIR, "cantina.db")
        if os.path.exists(seed_db) and not os.path.exists(DB_PATH):
            shutil.copy2(seed_db, DB_PATH)
        seed_imgs = os.path.join(SEED_DIR, "images")
        if os.path.exists(seed_imgs):
            for root, _, files in os.walk(seed_imgs):
                rel = os.path.relpath(root, seed_imgs)
                target_dir = os.path.join(IMAGES_DIR, rel) if rel != "." else IMAGES_DIR
                os.makedirs(target_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(target_dir, fn)
                    if not os.path.exists(dst_f):
                        shutil.copy2(src_f, dst_f)

    # Assicura che /app/static punti a IMAGES_DIR per lo static serving di Streamlit
    if not os.path.exists(STATIC_DIR):
        try:
            os.symlink(IMAGES_DIR, STATIC_DIR, target_is_directory=True)
        except Exception:
            pass


def _get_conn() -> sqlite3.Connection:
    _ensure_storage()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_foto_url(url: str) -> str:
    if not url:
        return ""
    if "/cantina-images/" in url:
        rel = url.split("/cantina-images/")[1].split("?")[0]
        return f"/app/static/{rel}"
    return url


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            ruolo TEXT DEFAULT 'admin',
            attivo INTEGER DEFAULT 1,
            piano TEXT DEFAULT 'base',
            portale_attivo INTEGER DEFAULT 0,
            portale_slug TEXT UNIQUE,
            logo_url TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            note_admin TEXT DEFAULT '',
            created_at TEXT,
            sito_web TEXT DEFAULT '',
            reset_token TEXT,
            reset_token_expires TEXT,
            trial_expires_at TEXT,
            login_attempts INTEGER DEFAULT 0,
            login_blocked_until TEXT
        );

        CREATE TABLE IF NOT EXISTS vini (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT DEFAULT '',
            azienda TEXT DEFAULT '',
            provenienza TEXT DEFAULT '',
            luogo TEXT DEFAULT '',
            collocazione TEXT DEFAULT '',
            annata TEXT DEFAULT '',
            gradi TEXT DEFAULT '',
            formato TEXT DEFAULT '0.75 L',
            vitigno TEXT DEFAULT '',
            tipo_vino TEXT DEFAULT '',
            zucchero TEXT DEFAULT '',
            prezzo REAL DEFAULT 0,
            qta INTEGER DEFAULT 0,
            foto_url TEXT DEFAULT '',
            note TEXT DEFAULT '',
            giudizio TEXT DEFAULT '',
            tipo_cat TEXT DEFAULT '',
            cat_origine TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS mignon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            nome TEXT DEFAULT '',
            azienda TEXT DEFAULT '',
            provenienza TEXT DEFAULT '',
            luogo TEXT DEFAULT '',
            collocazione TEXT DEFAULT '',
            annata TEXT DEFAULT '',
            gradi TEXT DEFAULT '',
            formato TEXT DEFAULT '',
            vitigno TEXT DEFAULT '',
            tipo_vino TEXT DEFAULT '',
            zucchero TEXT DEFAULT '',
            prezzo REAL DEFAULT 0,
            qta INTEGER DEFAULT 0,
            foto_url TEXT DEFAULT '',
            note TEXT DEFAULT '',
            giudizio TEXT DEFAULT '',
            tipo_cat TEXT DEFAULT '',
            cat_origine TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_vini_tenant ON vini(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_mignon_tenant ON mignon(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_tenants_email ON tenants(email);
        CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(portale_slug);
        """)

        # Se il DB è vuoto e abbiamo supabase_backup.json, importa automaticamente
        cur = conn.execute("SELECT COUNT(*) FROM tenants")
        if cur.fetchone()[0] == 0:
            backup_candidates = [
                os.path.join(DATA_DIR, "supabase_backup.json"),
                os.path.join(SEED_DIR, "supabase_backup.json"),
            ]
            for bp in backup_candidates:
                if os.path.exists(bp):
                    with open(bp, "r", encoding="utf-8") as f:
                        dump = json.load(f)
                    for t in dump.get("tenants", []):
                        conn.execute("""
                            INSERT OR IGNORE INTO tenants (
                                id, nome, email, password_hash, ruolo, attivo, piano,
                                portale_attivo, portale_slug, logo_url, telefono, note_admin,
                                created_at, sito_web, reset_token, reset_token_expires,
                                trial_expires_at, login_attempts, login_blocked_until
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            t.get("id"), t.get("nome", ""), t.get("email", ""), t.get("password_hash", ""),
                            t.get("ruolo", "admin"), 1 if t.get("attivo", True) else 0, t.get("piano", "base"),
                            1 if t.get("portale_attivo", False) else 0, t.get("portale_slug"),
                            _normalize_foto_url(t.get("logo_url", "")), t.get("telefono", ""),
                            t.get("note_admin", ""), t.get("created_at"), t.get("sito_web", ""),
                            t.get("reset_token"), t.get("reset_token_expires"), t.get("trial_expires_at"),
                            t.get("login_attempts", 0) or 0, t.get("login_blocked_until")
                        ))
                    for table_name in ("vini", "mignon"):
                        for v in dump.get(table_name, []):
                            conn.execute(f"""
                                INSERT OR IGNORE INTO {table_name} (
                                    id, tenant_id, nome, azienda, provenienza, luogo, collocazione,
                                    annata, gradi, formato, vitigno, tipo_vino, zucchero,
                                    prezzo, qta, foto_url, note, giudizio, tipo_cat, cat_origine, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                v.get("id"), v.get("tenant_id", ""), v.get("nome", ""), v.get("azienda", ""),
                                v.get("provenienza", ""), v.get("luogo", ""), v.get("collocazione", ""),
                                v.get("annata", ""), v.get("gradi", ""), v.get("formato", ""),
                                v.get("vitigno", ""), v.get("tipo_vino", ""), v.get("zucchero", ""),
                                v.get("prezzo", 0) or 0, v.get("qta", 0) or 0,
                                _normalize_foto_url(v.get("foto_url", "")),
                                v.get("note", ""), v.get("giudizio", ""), v.get("tipo_cat", ""),
                                v.get("cat_origine", ""), v.get("created_at")
                            ))
                    conn.commit()
                    break


_init_db()


def _row_to_tenant(r: sqlite3.Row | None) -> dict:
    if not r:
        return {}
    d = dict(r)
    d["attivo"] = bool(d.get("attivo", 1))
    d["portale_attivo"] = bool(d.get("portale_attivo", 0))
    d["logo_url"] = _normalize_foto_url(d.get("logo_url", ""))
    return d


def _row_to_vino(r: sqlite3.Row | None) -> dict:
    if not r:
        return {}
    d = dict(r)
    d["foto_url"] = _normalize_foto_url(d.get("foto_url", ""))
    return d


# ── Mock Storage compatibile con cantina_app.py ──────────────────────────────

class _LocalBucket:
    def remove(self, paths: list[str]):
        for p in paths:
            rel = p.lstrip("/").replace("/", os.sep)
            full = os.path.join(IMAGES_DIR, rel)
            if os.path.exists(full):
                try:
                    os.remove(full)
                except Exception:
                    pass


class _LocalStorage:
    def from_(self, _bucket: str) -> _LocalBucket:
        return _LocalBucket()


class _LocalClient:
    def __init__(self):
        self.storage = _LocalStorage()


def get_sb() -> _LocalClient:
    return _LocalClient()


# ── Auth ──────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        if stored_hash.startswith(("$2b$", "$2a$", "$2y$")):
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash
    except Exception:
        return False


def verify_login(email: str, password: str):
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tenants WHERE lower(email) = lower(?) AND attivo = 1",
            (email.strip(),)
        ).fetchone()
        if not row:
            return None
        tenant = _row_to_tenant(row)
        tid = tenant["id"]
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        blocked_until = tenant.get("login_blocked_until")
        if blocked_until and blocked_until > now_utc:
            return "__blocked__"

        if not _verify_password(password, tenant.get("password_hash", "")):
            attempts = (tenant.get("login_attempts") or 0) + 1
            if attempts >= 5:
                bl = (datetime.datetime.now(datetime.timezone.utc)
                      + datetime.timedelta(minutes=5)).isoformat()
                conn.execute(
                    "UPDATE tenants SET login_attempts = 0, login_blocked_until = ? WHERE id = ?",
                    (bl, tid)
                )
            else:
                conn.execute(
                    "UPDATE tenants SET login_attempts = ? WHERE id = ?",
                    (attempts, tid)
                )
            conn.commit()
            return None

        stored = tenant.get("password_hash", "")
        if not stored.startswith(("$2b$", "$2a$", "$2y$")):
            new_hash = hash_password(password)
            conn.execute(
                "UPDATE tenants SET login_attempts = 0, login_blocked_until = NULL, password_hash = ? WHERE id = ?",
                (new_hash, tid)
            )
            tenant["password_hash"] = new_hash
        else:
            conn.execute(
                "UPDATE tenants SET login_attempts = 0, login_blocked_until = NULL WHERE id = ?",
                (tid,)
            )
        conn.commit()
        return tenant


def generate_reset_token(email: str) -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM tenants WHERE lower(email) = lower(?) AND attivo = 1",
            (email.strip(),)
        ).fetchone()
        if not row:
            return None
        token = secrets.token_urlsafe(32)
        expires = (datetime.datetime.now(datetime.timezone.utc)
                   + datetime.timedelta(minutes=30)).isoformat()
        conn.execute(
            "UPDATE tenants SET reset_token = ?, reset_token_expires = ? WHERE id = ?",
            (token, expires, row["id"])
        )
        conn.commit()
        return token


def verify_reset_token(token: str) -> dict | None:
    if not token or len(token) < 10:
        return None
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, email, nome FROM tenants WHERE reset_token = ? AND reset_token_expires > ?",
            (token, now)
        ).fetchone()
        return dict(row) if row else None


def update_password_by_token(token: str, new_password: str) -> bool:
    tenant = verify_reset_token(token)
    if not tenant:
        return False
    with _get_conn() as conn:
        conn.execute(
            "UPDATE tenants SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL WHERE id = ?",
            (hash_password(new_password), tenant["id"])
        )
        conn.commit()
    return True


def email_exists(email: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM tenants WHERE lower(email) = lower(?)",
            (email.strip(),)
        ).fetchone()
        return row is not None


# ── Tenants (clienti) ─────────────────────────────────────────────────────────

def get_all_tenants() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY created_at DESC").fetchall()
        return [_row_to_tenant(r) for r in rows]


def get_tenant(tenant_id: str) -> dict:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        return _row_to_tenant(row)


def create_tenant(data: dict) -> dict:
    import uuid as _uuid
    payload = dict(data)
    if "password" in payload:
        payload["password_hash"] = hash_password(payload.pop("password"))
    tid = payload.get("id") or str(_uuid.uuid4())
    now = payload.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO tenants (
                id, nome, email, password_hash, ruolo, attivo, piano,
                portale_attivo, portale_slug, logo_url, telefono, note_admin,
                created_at, sito_web, trial_expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tid,
            payload.get("nome", ""),
            payload.get("email", "").strip().lower(),
            payload.get("password_hash", ""),
            payload.get("ruolo", "admin"),
            1 if payload.get("attivo", True) else 0,
            payload.get("piano", "base"),
            1 if payload.get("portale_attivo", False) else 0,
            payload.get("portale_slug"),
            payload.get("logo_url", ""),
            payload.get("telefono", ""),
            payload.get("note_admin", ""),
            now,
            payload.get("sito_web", ""),
            payload.get("trial_expires_at"),
        ))
        conn.commit()
    return get_tenant(tid)


def update_tenant(tenant_id: str, data: dict) -> dict:
    payload = dict(data)
    if "password" in payload and payload["password"]:
        payload["password_hash"] = hash_password(payload.pop("password"))
    elif "password" in payload:
        payload.pop("password")
    if "attivo" in payload:
        payload["attivo"] = 1 if payload["attivo"] else 0
    if "portale_attivo" in payload:
        payload["portale_attivo"] = 1 if payload["portale_attivo"] else 0
    if not payload:
        return get_tenant(tenant_id)
    cols = ", ".join(f"{k} = ?" for k in payload.keys())
    vals = list(payload.values()) + [tenant_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE tenants SET {cols} WHERE id = ?", vals)
        conn.commit()
    return get_tenant(tenant_id)


def toggle_tenant(tenant_id: str, attivo: bool):
    with _get_conn() as conn:
        conn.execute("UPDATE tenants SET attivo = ? WHERE id = ?", (1 if attivo else 0, tenant_id))
        conn.commit()


def get_tenant_by_slug(slug: str) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tenants WHERE portale_slug = ? AND portale_attivo = 1",
            (slug,)
        ).fetchone()
        return _row_to_tenant(row)


def get_tenant_by_slug_lista(slug: str) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tenants WHERE portale_slug = ? AND attivo = 1",
            (slug,)
        ).fetchone()
        return _row_to_tenant(row)


# ── Vini / Mignon (filtrati per tenant) ───────────────────────────────────────

@st.cache_data(ttl=60)
def get_vini(tenant_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM vini WHERE tenant_id = ? ORDER BY id", (tenant_id,)).fetchall()
        return [_row_to_vino(r) for r in rows]


@st.cache_data(ttl=60)
def get_mignon(tenant_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM mignon WHERE tenant_id = ? ORDER BY id", (tenant_id,)).fetchall()
        return [_row_to_vino(r) for r in rows]


@st.cache_data(ttl=60)
def get_vini_portale(tenant_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vini WHERE tenant_id = ? AND qta > 0 AND tipo_cat != 'Provati' ORDER BY tipo_cat",
            (tenant_id,)
        ).fetchall()
        return [_row_to_vino(r) for r in rows]


VINI_COLS = {
    "tenant_id", "nome", "azienda", "provenienza", "luogo", "collocazione",
    "annata", "gradi", "formato", "vitigno", "tipo_vino", "zucchero",
    "prezzo", "qta", "foto_url", "note", "giudizio", "tipo_cat", "cat_origine", "created_at"
}

MIGNON_COLS = {
    "tenant_id", "nome", "azienda", "annata", "vitigno", "gradi",
    "prezzo", "qta", "formato", "provenienza", "luogo",
    "note", "foto_url", "tipo_cat", "collocazione", "tipo_vino", "zucchero", "giudizio", "cat_origine"
}


def insert_vino(tenant_id: str, data: dict) -> dict:
    payload = {k: v for k, v in data.items() if k in VINI_COLS}
    payload["tenant_id"] = tenant_id
    payload.setdefault("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
    cols = ", ".join(payload.keys())
    placeholders = ", ".join("?" for _ in payload)
    with _get_conn() as conn:
        cur = conn.execute(f"INSERT INTO vini ({cols}) VALUES ({placeholders})", list(payload.values()))
        conn.commit()
        row = conn.execute("SELECT * FROM vini WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_vino(row)


def insert_mignon(tenant_id: str, data: dict) -> dict:
    payload = {k: v for k, v in data.items() if k in MIGNON_COLS}
    payload["tenant_id"] = tenant_id
    cols = ", ".join(payload.keys())
    placeholders = ", ".join("?" for _ in payload)
    with _get_conn() as conn:
        cur = conn.execute(f"INSERT INTO mignon ({cols}) VALUES ({placeholders})", list(payload.values()))
        conn.commit()
        row = conn.execute("SELECT * FROM mignon WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_vino(row)


def update_vino(record_id: int, tenant_id: str, data: dict) -> dict:
    payload = {k: v for k, v in data.items() if k in VINI_COLS and k != "tenant_id"}
    if not payload:
        return {}
    cols = ", ".join(f"{k} = ?" for k in payload.keys())
    vals = list(payload.values()) + [record_id, tenant_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE vini SET {cols} WHERE id = ? AND tenant_id = ?", vals)
        conn.commit()
        row = conn.execute("SELECT * FROM vini WHERE id = ? AND tenant_id = ?", (record_id, tenant_id)).fetchone()
        return _row_to_vino(row)


def update_mignon(record_id: int, tenant_id: str, data: dict) -> dict:
    payload = {k: v for k, v in data.items() if k in MIGNON_COLS and k != "tenant_id"}
    if not payload:
        return {}
    cols = ", ".join(f"{k} = ?" for k in payload.keys())
    vals = list(payload.values()) + [record_id, tenant_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE mignon SET {cols} WHERE id = ? AND tenant_id = ?", vals)
        conn.commit()
        row = conn.execute("SELECT * FROM mignon WHERE id = ? AND tenant_id = ?", (record_id, tenant_id)).fetchone()
        return _row_to_vino(row)


def delete_vino(record_id: int, tenant_id: str):
    with _get_conn() as conn:
        conn.execute("DELETE FROM vini WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
        conn.commit()


def delete_mignon(record_id: int, tenant_id: str):
    with _get_conn() as conn:
        conn.execute("DELETE FROM mignon WHERE id = ? AND tenant_id = ?", (record_id, tenant_id))
        conn.commit()


# ── Storage Immagini Locale ──────────────────────────────────────────────────

def upload_image(file_bytes: bytes, filename: str, folder: str = "vini") -> str:
    _ensure_storage()
    target_dir = os.path.join(IMAGES_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return f"/app/static/{folder}/{filename}"


def get_public_url(path: str) -> str:
    clean = path.lstrip("/")
    return f"/app/static/{clean}"


# ── Statistiche globali (superadmin) ─────────────────────────────────────────

def get_stats_globali() -> dict:
    with _get_conn() as conn:
        n_clienti = conn.execute("SELECT COUNT(*) FROM tenants WHERE attivo = 1").fetchone()[0]
        rows = conn.execute("SELECT qta, prezzo FROM vini WHERE qta > 0 AND tipo_cat != 'Provati'").fetchall()
        tot_bottiglie = sum(int(r["qta"] or 0) for r in rows)
        tot_valore = sum(int(r["qta"] or 0) * float(str(r["prezzo"] or 0).replace(",", ".")) for r in rows)
        return {
            "n_clienti": n_clienti,
            "n_bottiglie": tot_bottiglie,
            "valore_totale": tot_valore,
            "n_vini_records": len(rows),
        }
