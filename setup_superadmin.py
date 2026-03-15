# -*- coding: utf-8 -*-
"""
setup_superadmin.py — Da eseguire UNA SOLA VOLTA.
Crea il tenant superadmin (Gian Carlo) e collega tutti i vini/mignon
già migrati a questo tenant.

Prerequisiti:
  - supabase_schema_v2.sql già eseguito su Supabase
  - .streamlit/secrets.toml con SUPABASE_URL e SUPABASE_KEY
  - SUPERADMIN_PASSWORD: imposta la password desiderata qui sotto
"""
import sys, io, os, tomllib, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from supabase import create_client

# ── CONFIGURAZIONE ────────────────────────────────────────────────────────────
SUPERADMIN_NOME     = "Gian Carlo"
SUPERADMIN_EMAIL    = "admin@cantina.pro"   # <-- cambia se vuoi
SUPERADMIN_PASSWORD = "CambiaMe2024!"       # <-- CAMBIA questa password!
SUPERADMIN_SLUG     = "cantina-gianCarlo"
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
SECRETS  = BASE_DIR / ".streamlit" / "secrets.toml"

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def main():
    print("\n" + "="*55)
    print("  CantinaPro — Setup Superadmin")
    print("="*55)

    if not SECRETS.exists():
        print(f"ERRORE: {SECRETS} non trovato.")
        sys.exit(1)

    with open(SECRETS, "rb") as f:
        secrets = tomllib.load(f)

    sb = create_client(secrets["SUPABASE_URL"], secrets["SUPABASE_KEY"])
    print("Connesso a Supabase!")

    # 1) Crea o aggiorna il superadmin
    print(f"\nCreo superadmin: {SUPERADMIN_EMAIL} ...")
    payload = {
        "nome":          SUPERADMIN_NOME,
        "email":         SUPERADMIN_EMAIL,
        "password_hash": hash_password(SUPERADMIN_PASSWORD),
        "ruolo":         "superadmin",
        "attivo":        True,
        "piano":         "enterprise",
        "portale_attivo": True,
        "portale_slug":  SUPERADMIN_SLUG,
        "note_admin":    "Account principale superadmin"
    }

    # Controlla se esiste già
    existing = sb.table("tenants").select("id").eq("email", SUPERADMIN_EMAIL).execute()
    if existing.data:
        tid = existing.data[0]["id"]
        sb.table("tenants").update(payload).eq("id", tid).execute()
        print(f"  Superadmin aggiornato. ID: {tid}")
    else:
        resp = sb.table("tenants").insert(payload).execute()
        tid = resp.data[0]["id"]
        print(f"  Superadmin creato. ID: {tid}")

    # 2) Collega tutti i vini esistenti (senza tenant_id) al superadmin
    print("\nCollegamento vini esistenti al superadmin ...")
    resp = sb.table("vini").update({"tenant_id": tid}).is_("tenant_id", "null").execute()
    n_vini = len(resp.data) if resp.data else 0
    print(f"  {n_vini} vini collegati.")

    # 3) Collega tutti i mignon esistenti
    print("\nCollegamento mignon esistenti al superadmin ...")
    resp = sb.table("mignon").update({"tenant_id": tid}).is_("tenant_id", "null").execute()
    n_mignon = len(resp.data) if resp.data else 0
    print(f"  {n_mignon} mignon collegati.")

    print("\n" + "="*55)
    print("  SETUP COMPLETATO!")
    print("="*55)
    print(f"\n  Email:    {SUPERADMIN_EMAIL}")
    print(f"  Password: {SUPERADMIN_PASSWORD}")
    print(f"  Portale:  ?portale={SUPERADMIN_SLUG}")
    print("\n  *** CAMBIA LA PASSWORD dopo il primo accesso! ***\n")
    input("Premi INVIO per chiudere...")

if __name__ == "__main__":
    main()
