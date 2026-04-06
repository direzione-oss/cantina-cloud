# -*- coding: utf-8 -*-
"""
cantina_app.py — CantinaPro SaaS Platform
Piattaforma multi-tenant per la gestione di cantine vino.
Ruoli: superadmin | admin (cliente) | portale pubblico
"""
import streamlit as st
import os, random, base64, datetime, hashlib, re, smtplib, uuid
import html as _html  # html.escape() per prevenire XSS in unsafe_allow_html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from fpdf import FPDF
from PIL import Image

import supabase_client as db

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & STILE
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CantinaPro — Gestionale",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

PRIMARY    = "#8B1A1A"   # bordeaux
ACCENT     = "#C9A84C"   # oro
BG_DARK    = "#0D0D0D"
CARD_BG    = "#1A1A1A"
SIDEBAR_BG = "#111111"
TEXT_MAIN  = "#F0EDE8"
TEXT_MUTED = "#888888"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── SFONDO GLOBALE ── */
html, body {{
    background-color: {BG_DARK} !important;
    font-family: 'Inter', sans-serif !important;
    color: {TEXT_MAIN} !important;
}}
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="block-container"] {{
    background-color: {BG_DARK} !important;
}}

/* ── TESTO GLOBALE — solo tag semantici, NO div generico ── */
p, h1, h2, h3, h4, h5, h6, li, span, label,
.stMarkdown p, .stMarkdown span,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {{ color: {TEXT_MAIN} !important; }}

/* ── DIALOG / MODAL: sfondo scuro — selettori multipli per Streamlit ── */
div[role="dialog"],
[data-baseweb="dialog"],
[data-baseweb="modal"],
[data-baseweb="block"][role="dialog"],
[data-testid="stModal"],
[data-testid="stDialog"],
[data-testid="stDialog"] > div,
[data-testid="stDialog"] > div > div {{
    background-color: #1A1A1A !important;
    border: 1px solid #2A2A2A !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.8) !important;
}}
/* Overlay */
[data-baseweb="modal-backdrop"],
[data-baseweb="overlay"] {{
    background: rgba(0,0,0,0.75) !important;
    backdrop-filter: blur(4px) !important;
}}
/* Testo nel dialog */
[data-testid="stDialog"] p,
[data-testid="stDialog"] span,
[data-testid="stDialog"] h1,
[data-testid="stDialog"] h2,
[data-testid="stDialog"] h3,
[data-testid="stDialog"] h4,
[data-testid="stDialog"] div,
[data-testid="stDialog"] label,
div[role="dialog"] p,
div[role="dialog"] span,
div[role="dialog"] label {{
    color: {TEXT_MAIN} !important;
}}
/* Titolo dialog */
[data-testid="stDialogTitle"] p, [data-testid="stDialogTitle"] * {{
    color: {ACCENT} !important; font-weight: 700 !important;
}}
/* Input dentro dialog */
div[role="dialog"] input, div[role="dialog"] textarea {{
    background: #252525 !important; color: {TEXT_MAIN} !important;
    border-color: #3A3A3A !important;
}}


/* ── LABEL FORM ── */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stFileUploader"] label,
[data-testid="stCheckbox"] label,
[data-testid="stForm"] label,
.stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label {{
    color: {TEXT_MAIN} !important; font-weight: 500 !important; opacity: 1 !important;
}}
[data-testid="stCheckbox"] label span {{ color: {TEXT_MAIN} !important; }}

/* ── INPUT FIELDS ── */
div[data-baseweb="input"], div[data-baseweb="textarea"] {{
    background-color: #252525 !important; border-radius: 8px !important;
}}
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {{
    background-color: #252525 !important; border: 1px solid #3A3A3A !important;
    color: {TEXT_MAIN} !important; border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}}
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {{ color: #666 !important; }}
div[data-baseweb="input"] input:focus {{ border-color: {ACCENT} !important; }}
[data-testid="stNumberInput"] input {{
    background-color: #252525 !important; color: {TEXT_MAIN} !important;
    border: 1px solid #3A3A3A !important;
}}

/* ── SELECTBOX ── */
div[data-baseweb="select"] > div, div[data-baseweb="select"] {{
    background-color: #252525 !important; border-color: #3A3A3A !important;
    color: {TEXT_MAIN} !important; border-radius: 8px !important;
}}
div[data-baseweb="select"] span, div[data-baseweb="select"] div {{
    color: {TEXT_MAIN} !important; background-color: transparent !important;
}}
[data-baseweb="menu"] li, ul[data-testid="stSelectboxVirtualDropdown"] li {{
    background-color: #1A1A1A !important; color: {TEXT_MAIN} !important;
}}
[data-baseweb="menu"] li:hover {{ background-color: {PRIMARY}44 !important; }}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG} !important; border-right: 1px solid #222 !important; }}
[data-testid="stSidebar"] * {{ color: {TEXT_MAIN} !important; }}
[data-testid="stSidebar"] input {{ background-color: #252525 !important; color: {TEXT_MAIN} !important; }}

/* ── PULSANTI: approccio inverso — tutti scuri, poi primary bordeaux ── */
/* Step 1: forza TUTTI i button a scuro di default */
.stButton button,
[data-testid^="baseButton"],
[data-testid^="stBaseButton"] {{
    background: #252525 !important;
    border: 1px solid #444 !important;
    color: {TEXT_MAIN} !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}}
.stButton button:hover,
[data-testid^="baseButton"]:hover,
[data-testid^="stBaseButton"]:hover {{
    background: #1E1E1E !important;
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
    transform: none !important;
}}
/* Step 2: primary button — stile bordeaux */
[data-testid="baseButton-primary"],
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, {PRIMARY}, #6B1414) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(139,26,26,0.3) !important;
}}
[data-testid="baseButton-primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #a32020, {PRIMARY}) !important;
    border: none !important;
    color: white !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(139,26,26,0.5) !important;
}}

/* ── METRICHE ── */
[data-testid="stMetric"] {{
    background: {CARD_BG}; border-radius: 12px; padding: 16px;
    border: 1px solid #2A2A2A; border-top: 3px solid {PRIMARY};
}}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {{ color: {ACCENT} !important; font-weight: 700 !important; }}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div,
[data-testid="stMetricLabel"] span,
[data-testid="stMetricLabel"] label {{
    color: #CCCCCC !important; font-size: 0.85em !important; opacity: 1 !important;
}}

/* ── TABS ── */
[data-testid="stTabs"] button {{
    background: transparent !important; color: #AAAAAA !important;
    border-bottom: 2px solid transparent !important;
    box-shadow: none !important; border-radius: 0 !important;
    padding: 8px 16px !important; font-weight: 500 !important;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {ACCENT} !important; border-bottom-color: {ACCENT} !important;
}}

/* ── EXPANDER ── */
details summary {{ color: {TEXT_MAIN} !important; font-weight: 500 !important; }}
[data-testid="stExpander"] {{
    border-color: #2A2A2A !important; background: {CARD_BG} !important; border-radius: 10px !important;
}}
[data-testid="stExpander"] summary p {{ color: {TEXT_MAIN} !important; }}

/* ── CAPTION ── */
[data-testid="stCaptionContainer"] p, .stCaption p {{ color: #888 !important; font-size: 0.8em !important; }}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {{
    background: #1E1E1E !important; border: 1px dashed #3A3A3A !important; border-radius: 8px !important;
}}
[data-testid="stFileUploader"] p, [data-testid="stFileUploader"] span {{ color: #AAAAAA !important; }}

/* ── ALERT BOXES ── */
[data-testid="stAlert"] p, [data-testid="stAlert"] div {{ color: {TEXT_MAIN} !important; }}

/* ── TOOLTIP scuri ── */
[data-testid="stTooltipContent"],
[data-baseweb="tooltip"] div,
div[role="tooltip"],
.stTooltipContent,
[data-placement] div[role="tooltip"] {{
    background-color: #252525 !important;
    color: {TEXT_MAIN} !important;
    border: 1px solid #3A3A3A !important;
    border-radius: 8px !important;
    font-size: 1em !important;
    padding: 8px 12px !important;
    line-height: 1.5 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.6) !important;
}}
/* Freccia del tooltip */
[data-baseweb="tooltip"] [data-placement] {{
    background-color: #252525 !important;
}}


/* ── CARD VINO ── */
.wine-card {{
    background: {CARD_BG}; border-radius: 14px; border: 1px solid #252525;
    margin-bottom: 16px; overflow: hidden; transition: all 0.2s ease;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}}
.wine-card:hover {{ border-color: {PRIMARY}; box-shadow: 0 6px 24px rgba(139,26,26,0.25); }}
.wine-card-header {{
    background: linear-gradient(90deg, {PRIMARY}22, transparent);
    padding: 10px 14px; border-bottom: 1px solid #2A2A2A;
    font-weight: 600; font-size: 0.95em; color: {TEXT_MAIN};
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.wine-badge {{
    display: inline-block; padding: 2px 8px; border-radius: 20px;
    font-size: 0.72em; font-weight: 600; background: {PRIMARY}33;
    color: {ACCENT}; border: 1px solid {PRIMARY}44; margin-left: 6px;
}}

/* ── STAT BOX ── */
.stat-box {{
    flex: 1; min-width: 140px; background: {CARD_BG};
    border-radius: 10px; padding: 14px 16px;
    border: 1px solid #222; border-left: 4px solid {PRIMARY};
}}
.stat-box .val {{ font-size: 1.6em; font-weight: 700; color: {ACCENT}; }}
.stat-box .lbl {{ font-size: 0.78em; color: #AAAAAA; margin-top: 2px; }}

/* ── BADGE ── */
.badge-attivo {{ background: #14532d33; color: #4ade80; padding: 2px 10px; border-radius: 20px; font-size: 0.75em; }}
.badge-disattivo {{ background: #7f1d1d33; color: #f87171; padding: 2px 10px; border-radius: 20px; font-size: 0.75em; }}
.badge-piano {{ background: {ACCENT}22; color: {ACCENT}; padding: 2px 10px; border-radius: 20px; font-size: 0.75em; }}

/* ── MISC ── */
hr {{ border-color: #2A2A2A !important; margin: 20px 0 !important; }}
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {BG_DARK}; }}
::-webkit-scrollbar-thumb {{ background: #3A3A3A; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {PRIMARY}; }}

/* ── PORTALE ── */
.portale-hero {{
    background: linear-gradient(135deg, {PRIMARY}, #3d0000);
    padding: 60px 40px; text-align: center; border-radius: 0 0 30px 30px; margin-bottom: 40px;
}}
.portale-wine-card {{
    background: white; border-radius: 12px; overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1); transition: transform 0.2s; height: 100%;
}}
.portale-wine-card:hover {{ transform: translateY(-4px); }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COSTANTI
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIE_BASE = ["⚠️ DA CATALOGARE","Rossi","Bianchi","Spumanti","Champagne","Frizzanti","Liquori","Birre","Provati","Altro"]
TIPI_VINO      = ["Fermo","Mosso","Frizzante","Metodo Classico","Charmat","Passito"]
SCALA_ZUCCHERI = ["N.S.","Pas Dosé","Extra Brut","Brut","Extra Dry","Dry","Demi Sec","Dolce"]

PIANI = {"base": "🥈 Base", "pro": "🥇 Pro", "enterprise": "💎 Enterprise"}

SUPERADMIN_EMAIL = st.secrets.get("SUPERADMIN_EMAIL", "admin@cantina.pro")
APP_BASE_URL     = st.secrets.get("APP_BASE_URL", "https://cantina-cloud-gian.streamlit.app")

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "logged_in": False,
        "user": None,
        "ruolo": None,
        "page": "dashboard",
        "tenant_view": None,
        "id_modifica": None,
        "sezione_cantina": "VINI",
        "luogo_sel": "TUTTE LE SEDI",
        "cat_sel": "TUTTI",
        "login_attempts": 0,
        "login_blocked_until": None,
        "inv_pagina": 0,
        "inv_tipo_key": "",  # chiave per reset pagina al cambio filtri
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY (definite subito: servono nei handler pubblici senza login)
# ─────────────────────────────────────────────────────────────────────────────

def to_float(x):
    try: return float(str(x).replace(",", "."))
    except (ValueError, TypeError): return 0.0

def to_int(x):
    try: return int(str(x).split()[0])
    except (ValueError, TypeError, IndexError): return 0

def calcola_totali(data):
    bottiglie = sum(to_int(v.get("qta",0)) for v in data if v.get("tipo_cat") != "Provati")
    valore = sum(to_int(v.get("qta",0)) * to_float(v.get("prezzo",0)) for v in data if v.get("tipo_cat") != "Provati")
    return bottiglie, valore

# ─────────────────────────────────────────────────────────────────────────────
# PAGINE PUBBLICHE (accessibili senza login via query params)
# ─────────────────────────────────────────────────────────────────────────────

params = st.query_params
portale_slug = params.get("portale", "")
lista_slug   = params.get("lista", "")
lista_luogo  = params.get("luogo", "")
reset_token_param = params.get("reset", "")

# ─────────────────────────────────────────────────────────────────────────────
# RESET PASSWORD (route pubblica: ?reset=TOKEN)
# ─────────────────────────────────────────────────────────────────────────────

if reset_token_param:
    tenant_reset = db.verify_reset_token(reset_token_param)
    _, col_r, _ = st.columns([1, 1.2, 1])
    with col_r:
        st.markdown(f"""
        <div style="text-align:center;padding:40px 0 20px;">
            <div style="font-size:3em;margin-bottom:8px;">🔑</div>
            <div style="font-size:1.8em;font-weight:700;color:{TEXT_MAIN};">Reimposta Password</div>
            <div style="color:{TEXT_MUTED};font-size:0.9em;margin-top:4px;">CantinaPro</div>
        </div>
        """, unsafe_allow_html=True)
        if not tenant_reset:
            st.error("⛔ Il link di reset non è valido o è scaduto (validità 30 minuti).")
            st.markdown(f"[← Torna al login]({APP_BASE_URL})")
        else:
            st.markdown(f"<div style='text-align:center;color:{TEXT_MUTED};margin-bottom:20px;'>Stai reimpostando la password per <b>{tenant_reset['email']}</b></div>", unsafe_allow_html=True)
            with st.form("reset_pwd_form"):
                np1 = st.text_input("🔒 Nuova password", type="password", placeholder="Min. 8 caratteri")
                np2 = st.text_input("🔒 Conferma nuova password", type="password", placeholder="Ripeti la password")
                ok  = st.form_submit_button("✅ Salva nuova password", use_container_width=True, type="primary")
            if ok:
                if len(np1) < 8:
                    st.error("La password deve avere almeno 8 caratteri.")
                elif np1 != np2:
                    st.error("Le password non coincidono.")
                else:
                    if db.update_password_by_token(reset_token_param, np1):
                        st.success("✅ Password aggiornata! Ora puoi accedere con la nuova password.")
                        st.page_link(APP_BASE_URL, label="🔑 Vai al login", help="Torna alla pagina di login")
                    else:
                        st.error("Errore durante il reset. Riprova o richiedi un nuovo link.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# LISTA OSPITI PER LUOGO (accessibile via QR code senza login)
# ─────────────────────────────────────────────────────────────────────────────

if lista_slug:
    import urllib.parse
    tenant = db.get_tenant_by_slug_lista(lista_slug)
    if not tenant:
        st.error("Lista non trovata.")
        st.stop()

    tid = tenant["id"]
    tutti_vini = db.get_vini(tid)

    # Filtra per luogo se specificato
    if lista_luogo:
        vini_lista = [v for v in tutti_vini
                      if v.get("luogo","").lower() == lista_luogo.lower()
                      and to_int(v.get("qta",0)) > 0
                      and v.get("tipo_cat") != "Provati"]
        titolo_luogo = lista_luogo
    else:
        vini_lista = [v for v in tutti_vini
                      if to_int(v.get("qta",0)) > 0
                      and v.get("tipo_cat") != "Provati"]
        titolo_luogo = "Tutta la Cantina"

    # Raggruppa per categoria
    categorie = {}
    for v in vini_lista:
        cat = v.get("tipo_cat", "Altro")
        categorie.setdefault(cat, []).append(v)

    ord_cat = [c for c in CATEGORIE_BASE if c in categorie] + \
              [c for c in categorie if c not in CATEGORIE_BASE]

    # CSS premium mobile-first per lista ospiti
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, #1a0a0a 0%, #0d0d0d 100%) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding: 0 !important; max-width: 100% !important; }}
    .lista-hero {{
        background: linear-gradient(180deg, #2d0808 0%, #1a0505 60%, #0d0d0d 100%);
        padding: 48px 24px 36px;
        text-align: center;
        border-bottom: 1px solid #3a1a1a;
    }}
    .lista-cantina {{ font-family: 'Playfair Display', serif; font-size: 2em; color: #C9A84C; font-weight: 700; }}
    .lista-sede {{ font-size: 0.95em; color: rgba(255,255,255,0.5); margin-top: 6px; letter-spacing: 2px; text-transform: uppercase; }}
    .lista-count {{ font-size: 0.82em; color: #888; margin-top: 12px; }}
    .cat-header {{
        font-family: 'Playfair Display', serif;
        font-size: 1.3em; color: #C9A84C;
        border-bottom: 1px solid #3a1a1a;
        padding: 24px 20px 10px;
        margin: 0; letter-spacing: 1px;
    }}
    .wine-row {{
        display: flex; align-items: flex-start;
        padding: 14px 20px; border-bottom: 1px solid #1e1e1e;
        transition: background 0.15s;
    }}
    .wine-row:hover {{ background: #1a1005; }}
    .wine-num {{
        font-size: 0.75em; color: #555;
        min-width: 28px; padding-top: 3px;
    }}
    .wine-thumb {{
        width: 40px; height: 54px; object-fit: cover;
        border-radius: 4px; margin-right: 12px;
        border: 1px solid #2a2a2a; flex-shrink: 0;
    }}
    .wine-thumb-empty {{
        width: 40px; height: 54px; border-radius: 4px;
        margin-right: 12px; flex-shrink: 0;
        background: #1a1a1a; border: 1px solid #2a2a2a;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.2em; color: #333;
    }}
    .wine-info {{ flex: 1; }}
    .wine-nome {{ font-weight: 600; color: #F0EDE8; font-size: 0.98em; }}
    .wine-sub {{ color: #888; font-size: 0.78em; margin-top: 2px; }}
    .wine-fmt {{ color: #666; font-size: 0.72em; margin-top: 2px; }}
    .wine-qta {{
        font-size: 0.75em; text-align: right;
        min-width: 50px; padding-top: 3px;
    }}
    .wine-qta .num {{ font-size: 1.3em; font-weight: 700; color: #C9A84C; }}
    .wine-qta .lbl {{ color: #555; }}
    .footer-lista {{ text-align:center; padding: 32px 20px; color: #444; font-size:0.75em; }}
    p, span, div {{ color: #F0EDE8 !important; }}
    </style>
    """, unsafe_allow_html=True)

    # Hero — uso HTML compatto su una sola stringa (evita parsing markdown multiline)
    logo = tenant.get("logo_url", "")
    logo_tag = f'<img src="{logo}" style="height:64px;border-radius:50%;margin-bottom:12px;display:block;margin:0 auto 12px;"/>' if logo else ''
    n = len(vini_lista)
    hero_html = (f'<div class="lista-hero">{logo_tag}'
                 f'<div style="font-size:2.4em;margin-bottom:6px;">\U0001f377</div>'
                 f'<div class="lista-cantina">{tenant["nome"]}</div>'
                 f'<div class="lista-sede">\U0001f4cd\u00a0{titolo_luogo}</div>'
                 f'<div class="lista-count">{n} vin{"o" if n==1 else "i"} disponibil{"e" if n==1 else "i"}</div>'
                 f'</div>')
    st.markdown(hero_html, unsafe_allow_html=True)

    # Lista per categoria
    for cat in ord_cat:
        vini_cat = categorie[cat]
        st.markdown(f'<div class="cat-header">🍾 {cat} <span style="font-size:0.6em;color:#555;font-family:Inter;">({len(vini_cat)})</span></div>', unsafe_allow_html=True)
        for idx, v in enumerate(sorted(vini_cat, key=lambda x: x.get("nome","")), 1):
            az   = v.get("azienda","")
            ann  = v.get("annata","")
            vit  = v.get("vitigno","")
            fmt  = v.get("formato","0.75 L")
            q    = to_int(v.get("qta",0))
            sub  = " · ".join(filter(None, [az, ann, vit]))
            foto = v.get("foto_url", "")
            thumb_html = f'<img class="wine-thumb" src="{foto}" alt=""/>' if foto else '<div class="wine-thumb-empty">🍷</div>'
            st.markdown(f"""
            <div class="wine-row">
                <div class="wine-num">{idx}</div>
                {thumb_html}
                <div class="wine-info">
                    <div class="wine-nome">{v['nome']}</div>
                    {f'<div class="wine-sub">{sub}</div>' if sub else ''}
                    <div class="wine-fmt">🍾 {fmt}</div>
                </div>
                <div class="wine-qta">
                    <div class="num">{q}</div>
                    <div class="lbl">bott.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(
        '<div style="border-top:1px solid #2a1a1a;margin-top:24px;padding:32px 20px 20px;text-align:center;">'
        f'<div style="font-family:Playfair Display,serif;font-size:1em;color:#C9A84C;margin-bottom:6px;">'
        f'Desideri gestire la tua cantina digitale?</div>'
        f'<a href="{APP_BASE_URL}/" target="_blank" '
        f'style="display:inline-block;background:#8B1A1A;color:white;text-decoration:none;'
        f'padding:10px 28px;border-radius:8px;font-size:0.88em;font-weight:600;margin:8px 0;'
        f'letter-spacing:0.5px;">🍷 Scopri CantinaPro</a>'
        f'<div style="font-size:0.72em;color:#444;margin-top:16px;">'
        f'Lista aggiornata in tempo reale &nbsp;·&nbsp; '
        f'<span style="color:#8B1A1A;">CantinaPro</span></div>'
        '</div>',
        unsafe_allow_html=True
    )
    st.stop()


if portale_slug:
    tenant = db.get_tenant_by_slug(portale_slug)
    if not tenant:
        st.error("Portale non trovato o non attivo.")
        st.stop()

    vini = db.get_vini_portale(tenant["id"])

    # Hero
    logo = tenant.get("logo_url", "")
    st.markdown(f"""
    <div class="portale-hero">
        {'<img src="'+logo+'" style="height:80px;border-radius:50%;margin-bottom:16px;" />' if logo else '🍷'}
        <h1 style="color:white;font-size:2.4em;margin:0;">{tenant["nome"]}</h1>
        <p style="color:rgba(255,255,255,0.7);margin-top:8px;">Selezione vini pregiati — Catalogo aggiornato</p>
    </div>
    """, unsafe_allow_html=True)

    # Filtro categoria
    cats = sorted(list(set(v.get("tipo_cat","") for v in vini)))
    cat_scelta = st.selectbox("🍾 Categoria", ["Tutte"] + cats)
    cerca = st.text_input("🔍 Cerca vino...", "").lower()

    vini_filtrati = [v for v in vini
                     if (cat_scelta == "Tutte" or v.get("tipo_cat") == cat_scelta)
                     and (not cerca or cerca in v.get("nome","").lower() or cerca in v.get("azienda","").lower())]

    st.markdown(f"**{len(vini_filtrati)} vini disponibili**")
    cols = st.columns(3)
    for i, v in enumerate(vini_filtrati):
        with cols[i % 3]:
            with st.container():
                if v.get("foto_url"):
                    st.image(v["foto_url"], use_container_width=True)
                st.markdown(f"**{v['nome']}**")
                st.caption(f"{v.get('azienda','')} · {v.get('annata','')}")
                st.markdown(f"🍇 {v.get('vitigno','')} · {v.get('formato','0.75 L')}")
                st.markdown(f"💶 **€ {float(str(v.get('prezzo',0)).replace(',','.')):,.2f}** · Qta: {v['qta']}")
                st.markdown("---")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def _invia_email_notifica(nome: str, email: str, piano: str):
    """Invia email di notifica a direzione@serrastudio.it per ogni nuova registrazione."""
    try:
        smtp_host = st.secrets.get("SMTP_HOST", "")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        smtp_user = st.secrets.get("SMTP_USER", "")
        smtp_pass = st.secrets.get("SMTP_PASS", "")
        if not smtp_host or not smtp_user:
            return  # SMTP non configurato, skip silenzioso

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🍷 Nuova registrazione CantinaPro: {nome}"
        msg["From"]    = smtp_user
        msg["To"]      = "direzione@serrastudio.it"

        oggi = datetime.date.today()
        scadenza = oggi + datetime.timedelta(days=14)
        corpo = f"""\
<html><body style="font-family:Arial,sans-serif;color:#333;">
<h2 style="color:#8B1A1A;">🍷 Nuova registrazione CantinaPro</h2>
<table style="border-collapse:collapse;width:100%;">
  <tr><td style="padding:8px;font-weight:bold;">Nome cantina</td><td style="padding:8px;">{nome}</td></tr>
  <tr style="background:#f9f9f9;"><td style="padding:8px;font-weight:bold;">Email</td><td style="padding:8px;">{email}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Piano</td><td style="padding:8px;">{piano}</td></tr>
  <tr style="background:#f9f9f9;"><td style="padding:8px;font-weight:bold;">Data registrazione</td><td style="padding:8px;">{oggi.strftime('%d/%m/%Y')}</td></tr>
  <tr><td style="padding:8px;font-weight:bold;">Scadenza trial</td><td style="padding:8px;color:#8B1A1A;"><b>{scadenza.strftime('%d/%m/%Y')}</b></td></tr>
</table>
<p style="margin-top:20px;color:#666;font-size:0.9em;">Accedi al pannello superadmin per gestire questo cliente.</p>
</body></html>"""
        msg.attach(MIMEText(corpo, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, "direzione@serrastudio.it", msg.as_string())
    except Exception:
        pass  # Non bloccare la registrazione se email fallisce


def _invia_email_reset(email_dest: str, token: str):
    """Invia email con link di reset password all'utente."""
    try:
        smtp_host = st.secrets.get("SMTP_HOST", "")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        smtp_user = st.secrets.get("SMTP_USER", "")
        smtp_pass = st.secrets.get("SMTP_PASS", "")
        if not smtp_host or not smtp_user:
            return
        reset_url = f"{APP_BASE_URL}?reset={token}"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔑 Reimposta la tua password CantinaPro"
        msg["From"]    = smtp_user
        msg["To"]      = email_dest
        corpo = f"""\
<html><body style="font-family:Arial,sans-serif;color:#333;">
<h2 style="color:#8B1A1A;">🍷 CantinaPro — Reimposta password</h2>
<p>Hai richiesto il reset della password per il tuo account.</p>
<p style="margin:24px 0;">
  <a href="{reset_url}" style="background:#8B1A1A;color:white;text-decoration:none;
     padding:12px 28px;border-radius:8px;font-weight:bold;display:inline-block;">
    🔑 Reimposta la password
  </a>
</p>
<p style="color:#888;font-size:0.85em;">Il link è valido per 30 minuti.<br>
Se non hai richiesto il reset, ignora questa email.</p>
<p style="color:#888;font-size:0.8em;">Oppure copia questo indirizzo nel browser:<br>
<code style="color:#8B1A1A;">{reset_url}</code></p>
</body></html>"""
        msg.attach(MIMEText(corpo, "html"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email_dest, msg.as_string())
    except Exception as _smtp_err:
        import sys
        print(f"[SMTP RESET ERR] {_smtp_err}", file=sys.stderr)

def _banner_trial(user: dict):
    """Mostra banner se l'account è in periodo di trial."""
    if user.get("piano") != "trial":
        return
    note = user.get("note_admin", "")
    try:
        scad_str = next((p.split(":",1)[1] for p in note.split("|") if p.startswith("TRIAL_UNTIL")), None)
        if not scad_str:
            return
        scad = datetime.date.fromisoformat(scad_str.strip())
        rimasti = (scad - datetime.date.today()).days
        if rimasti < 0:
            st.error("⚠️ Il tuo periodo di prova è scaduto. Contatta direzione@serrastudio.it per attivare un piano.")
            st.stop()
        elif rimasti <= 3:
            st.warning(f"⏳ Il tuo periodo di prova scade tra **{rimasti} giorn{'o' if rimasti==1 else 'i'}**. Contattaci per continuare!")
        else:
            st.info(f"🌟 Stai usando CantinaPro in **prova gratuita** — scade il {scad.strftime('%d/%m/%Y')} ({rimasti} giorni rimasti).")
    except Exception:
        pass


def show_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(f"""
        <div style="text-align:center;padding:40px 0 20px;">
            <div style="font-size:3em;margin-bottom:8px;">🍷</div>
            <div style="font-size:1.8em;font-weight:700;color:{TEXT_MAIN};">CantinaPro</div>
            <div style="color:{TEXT_MUTED};font-size:0.9em;margin-top:4px;">Gestionale Cantine · Prova 14 giorni gratis</div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_reg = st.tabs(["  🔑 Accedi  ", "  ✨ Crea la tua cantina  "])

        # ── TAB LOGIN ──────────────────────────────────────────────────────────
        with tab_login:
            st.markdown(f"<div style='background:{CARD_BG};border:1px solid #222;border-radius:16px;padding:28px;margin-top:12px;'>", unsafe_allow_html=True)
            with st.form("login_form"):
                st.markdown("<div style='font-weight:600;font-size:1em;margin-bottom:16px;'>Accedi al tuo account</div>", unsafe_allow_html=True)
                email_l = st.text_input("Email", placeholder="nome@email.com", key="login_email")
                pwd_l   = st.text_input("Password", type="password", placeholder="••••••••", key="login_pwd")
                sub_l   = st.form_submit_button("🔓 ACCEDI", use_container_width=True, type="primary")
            if sub_l:
                _now = datetime.datetime.now()
                _blocked = st.session_state.login_blocked_until
                if _blocked and _now < _blocked:
                    _sec = int((_blocked - _now).total_seconds())
                    st.error(f"🔒 Troppi tentativi falliti. Riprova tra {_sec} secondi.")
                elif not email_l or not pwd_l:
                    st.error("Inserisci email e password.")
                else:
                    user = db.verify_login(email_l.strip().lower(), pwd_l)
                    if user:
                        st.session_state.login_attempts = 0
                        st.session_state.login_blocked_until = None
                        st.session_state.logged_in = True
                        st.session_state.user      = user
                        st.session_state.ruolo     = user.get("ruolo", "admin")
                        st.session_state.page      = "dashboard"
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        _att = st.session_state.login_attempts
                        if _att >= 5:
                            st.session_state.login_blocked_until = datetime.datetime.now() + datetime.timedelta(minutes=5)
                            st.session_state.login_attempts = 0
                            st.error("🔒 Troppi tentativi falliti. Accesso bloccato per 5 minuti.")
                        else:
                            st.error(f"❌ Credenziali non valide. ({_att}/5 tentativi)")
            st.markdown("</div>", unsafe_allow_html=True)

            # ── DIMENTICATO LA PASSWORD ────────────────────────────────────
            with st.expander("🔑 Hai dimenticato la password?"):
                with st.form("forgot_form"):
                    email_forgot = st.text_input("La tua email", placeholder="nome@email.com", key="forgot_email")
                    sub_forgot   = st.form_submit_button("📧 Invia link di reset", use_container_width=True)
                if sub_forgot:
                    if not email_forgot.strip():
                        st.error("Inserisci la tua email.")
                    else:
                        token_r = db.generate_reset_token(email_forgot.strip().lower())
                        # Sempre mostrare lo stesso messaggio (security: non rivela se email esiste)
                        if token_r:
                            _invia_email_reset(email_forgot.strip().lower(), token_r)
                        st.success("📬 Se l'email è registrata, riceverai un link entro pochi minuti. Controlla anche lo spam.")

        # ── TAB REGISTRAZIONE ──────────────────────────────────────────────────
        with tab_reg:
            st.markdown(f"""
            <div style='background:{CARD_BG};border:1px solid {PRIMARY};border-radius:16px;padding:28px;margin-top:12px;'>
            <div style='font-weight:600;font-size:1em;margin-bottom:4px;color:{ACCENT};'>✨ Inizia gratis — 14 giorni di prova</div>
            <div style='font-size:0.82em;color:{TEXT_MUTED};margin-bottom:16px;'>Nessuna carta di credito richiesta. Accesso immediato.</div>
            """, unsafe_allow_html=True)

            with st.form("reg_form"):
                nome_c = st.text_input("🍷 Nome della tua cantina", placeholder="Es. Cantina Rossi", key="reg_nome")
                email_r = st.text_input("📧 Email", placeholder="nome@email.com", key="reg_email")
                pwd_r   = st.text_input("🔒 Password", type="password", placeholder="Min. 8 caratteri", key="reg_pwd")
                pwd_r2  = st.text_input("🔒 Conferma password", type="password", placeholder="Ripeti password", key="reg_pwd2")
                terms   = st.checkbox("Accetto i termini di servizio e la privacy policy")
                sub_r   = st.form_submit_button("🚀 Crea la mia cantina", use_container_width=True, type="primary")

            if sub_r:
                # Validazioni
                err = []
                if not nome_c.strip():  err.append("Inserisci il nome della cantina.")
                if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email_r.strip()): err.append("Email non valida.")
                if len(pwd_r) < 8:      err.append("La password deve avere almeno 8 caratteri.")
                if pwd_r != pwd_r2:     err.append("Le password non coincidono.")
                if not terms:           err.append("Devi accettare i termini di servizio.")

                if err:
                    for e in err: st.error(e)
                elif db.email_exists(email_r.strip().lower()):
                    st.error("⚠️ Questa email è già registrata. Accedi con le tue credenziali.")
                else:
                    # Crea slug univoco
                    slug_base = re.sub(r'[^a-z0-9]', '-', nome_c.strip().lower())[:30]
                    slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"
                    scadenza = (datetime.date.today() + datetime.timedelta(days=14)).isoformat()

                    nuovo_tenant = db.create_tenant({
                        "nome": nome_c.strip(),
                        "email": email_r.strip().lower(),
                        "password": pwd_r,
                        "ruolo": "admin",
                        "piano": "trial",
                        "attivo": True,
                        "portale_slug": slug,
                        "portale_attivo": False,
                        "note_admin": f"TRIAL_UNTIL:{scadenza}|Registrazione autonoma",
                    })

                    if nuovo_tenant:
                        _invia_email_notifica(nome_c.strip(), email_r.strip(), "Trial 14 giorni")
                        st.success("✅ Cantina creata! Accedi ora con le tue credenziali.")
                        st.balloons()
                    else:
                        st.error("❌ Errore durante la registrazione. Riprova o contatta il supporto.")

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<div style='text-align:center;margin-top:20px;color:{TEXT_MUTED};font-size:0.78em;'>CantinaPro Platform · &copy; 2025 SerraStudio</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY (proseguo — to_float/to_int/calcola_totali già definite sopra)
# ─────────────────────────────────────────────────────────────────────────────

def calcola_formato(inp):
    mappa = {0.1875:"Piccolo",0.375:"Demi",0.75:"Standard",1.5:"Magnum",3.0:"Jeroboam",
             4.5:"Rehoboam",6.0:"Mathusalem",9.0:"Salmanazar",12.0:"Balthazar",15.0:"Nabuchodonosor"}
    try:
        val = float(str(inp).lower().replace("litri","").replace("l","").replace(",",".").strip())
        vis = int(val) if float(val).is_integer() else val
        nome = mappa.get(val, "")
        return f"{vis} L ({nome})" if nome else f"{vis} L"
    except: return inp or "0.75 L (Standard)"

def salva_img_cloud(uploaded_file, folder: str) -> str:
    try:
        img = Image.open(uploaded_file)
        try:
            from PIL import ExifTags
            for ori in ExifTags.TAGS.keys():
                if ExifTags.TAGS[ori] == "Orientation": break
            exif = img._getexif()
            if exif:
                if exif[ori] == 3: img = img.rotate(180, expand=True)
                elif exif[ori] == 6: img = img.rotate(270, expand=True)
                elif exif[ori] == 8: img = img.rotate(90, expand=True)
        except: pass
        img.thumbnail((900, 900))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=75, optimize=True)
        fname = f"img_{uuid.uuid4().hex[:12]}.jpg"
        return db.upload_image(buf.getvalue(), fname, folder)
    except Exception as e:
        st.error(f"Errore upload immagine: {e}")
        return ""

def pp(t):
    """Sanitizza testo per FPDF (latin-1): rimuove/sostituisce caratteri non supportati."""
    return (str(t)
            .replace("€", "E")
            .replace("—", "-")   # em dash
            .replace("–", "-")   # en dash
            .replace("…", "...")
            .replace("‘", "'")
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .encode("latin-1", "replace")
            .decode("latin-1"))

# ─────────────────────────────────────────────────────────────────────────────
# PDF  (funzioni cached per evitare rigenerazione ad ogni rerun)
# ─────────────────────────────────────────────────────────────────────────────



def genera_pdf_lista(lista, titolo):
    from collections import OrderedDict
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    # Titolo
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(139, 26, 26)
    pdf.cell(0, 10, pp(titolo), ln=True, align="C")
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 5, f"Stampato il {datetime.date.today().strftime('%d/%m/%Y')}  -  {len(lista)} etichette", ln=True, align="C")
    pdf.ln(3)
    hdrs = ["ID", "Nome Vino", "Azienda", "Sede", "Annata", "Formato", "Qta", "Prezzo"]
    wws  = [18, 65, 47, 35, 18, 28, 13, 28]
    W    = sum(wws)
    def stampa_header():
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(139, 26, 26)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(hdrs):
            pdf.cell(wws[i], 8, h, 1, 0, "C", True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln()
    # Raggruppa per categoria
    cat_map = OrderedDict()
    for v in lista:
        cat = v.get("tipo_cat", "Altro") or "Altro"
        cat_map.setdefault(cat, []).append(v)
    ord_cat = [c for c in CATEGORIE_BASE if c in cat_map] + \
              [c for c in cat_map if c not in CATEGORIE_BASE]
    for cat in ord_cat:
        vini_cat = sorted(cat_map[cat], key=lambda x: x.get("nome", ""))
        # Intestazione categoria
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(245, 236, 236)
        pdf.set_text_color(139, 26, 26)
        pdf.cell(W, 8, f"  {pp(cat)}  ({len(vini_cat)})", 1, 1, "L", True)
        pdf.set_text_color(0, 0, 0)
        stampa_header()
        pdf.set_font("Arial", "", 8)
        for i, v in enumerate(vini_cat):
            vid = str(v.get('id', ''))[:8]
            row = [
                vid,
                pp(v.get("nome", "")),
                pp(v.get("azienda", "")),
                pp(v.get("luogo", "")),
                pp(v.get("annata", "")),
                pp(v.get("formato", "")),
                str(to_int(v.get("qta", 0))),
                f"E {to_float(v.get('prezzo', 0)):.2f}",
            ]
            fill = i % 2 == 0
            pdf.set_fill_color(252, 248, 248) if fill else pdf.set_fill_color(255, 255, 255)
            for idx, txt in enumerate(row):
                pdf.cell(wws[idx], 6, txt, 1, 0, "L", fill)
            pdf.ln()
        pdf.ln(3)
    return bytes(pdf.output())


def genera_pdf_catalogo(lista, nome_cantina="Cantina"):
    """PDF catalogo completo: A4 verticale, schede dettagliate per categoria."""
    from collections import OrderedDict
    import datetime as _dt

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(True, margin=14)

    # Raggruppa e ordina
    cat_map = OrderedDict()
    for v in lista:
        cat = v.get("tipo_cat", "Altro") or "Altro"
        cat_map.setdefault(cat, []).append(v)
    ord_cat = [c for c in CATEGORIE_BASE if c in cat_map] + \
              [c for c in cat_map if c not in CATEGORIE_BASE]

    totale = sum(to_int(v.get("qta", 0)) for v in lista)
    valore = sum(to_float(v.get("prezzo", 0)) * to_int(v.get("qta", 0)) for v in lista)
    PAGE_W = 182  # 210 - 14*2

    def _hdr_pagina():
        """Header di ogni pagina."""
        pdf.set_font("Arial", "B", 7)
        pdf.set_text_color(180, 180, 180)
        pdf.cell(0, 5, f"CATALOGO VINI  {pp(nome_cantina).upper()}  |  {_dt.date.today().strftime('%d/%m/%Y')}",
                 ln=True, align="C")
        pdf.set_draw_color(200, 200, 200)
        pdf.line(14, pdf.get_y(), 196, pdf.get_y())
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0)

    # ── PAGINA DI COPERTINA ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(20)
    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(139, 26, 26)
    pdf.cell(0, 12, "CATALOGO VINI", ln=True, align="C")
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, pp(nome_cantina), ln=True, align="C")
    pdf.ln(6)

    pdf.set_draw_color(139, 26, 26)
    pdf.set_line_width(0.5)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(8)

    # Riepilogo numerico
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, f"Etichette: {len(lista)}   |   Bottiglie: {totale}   |   Valore: E {valore:,.2f}", ln=True, align="C")
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 6, f"Generato il {_dt.date.today().strftime('%d %B %Y')}", ln=True, align="C")
    pdf.ln(12)

    # Indice categorie
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(139, 26, 26)
    pdf.cell(0, 8, "CATEGORIE", ln=True, align="C")
    pdf.ln(2)
    for cat in ord_cat:
        n = len(cat_map[cat])
        q = sum(to_int(v.get("qta", 0)) for v in cat_map[cat])
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(90, 7, f"  {pp(cat)}", 0, 0, "L")
        pdf.cell(92, 7, f"{n} etichette  /  {q} bottiglie", 0, 1, "R")
        pdf.set_draw_color(220, 220, 220)
        pdf.line(14, pdf.get_y(), 196, pdf.get_y())

    # ── PAGINE PER CATEGORIA ────────────────────────────────────────────────
    COL_W  = [8, 62, 38, 18, 12, 26, 14, 4]   # N | Nome | Azienda | Annata | Gradi | Luogo/Pos | Prezzo | Qta + filler
    # Layout colonne dettaglio (larghezza totale = PAGE_W)
    C = [8, 56, 36, 18, 12, 24, 20, 8]        # N | Nome | Azienda | Annata | Gradi | Sede | Prezzo | Qta

    for cat in ord_cat:
        vini_cat = sorted(cat_map[cat], key=lambda x: x.get("nome", ""))

        pdf.add_page()
        _hdr_pagina()

        # Intestazione categoria
        pdf.set_fill_color(139, 26, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 12)
        ql = sum(to_int(v.get("qta", 0)) for v in vini_cat)
        pdf.cell(PAGE_W, 9,
                 f"  {pp(cat).upper()}  -  {len(vini_cat)} etichette  /  {ql} bottiglie",
                 1, 1, "L", True)
        pdf.ln(2)

        # Header tabella
        hdrs2 = ["ID", "Nome Vino", "Azienda/Produttore", "Annata", "Gradi", "Sede / Pos.", "Prezzo", "Qta"]
        pdf.set_fill_color(240, 235, 235)
        pdf.set_text_color(100, 30, 30)
        pdf.set_font("Arial", "B", 7)
        for i, h in enumerate(hdrs2):
            pdf.cell(C[i], 6, h, 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(0, 0, 0)

        for idx, v in enumerate(vini_cat):
            fill = idx % 2 == 0
            pdf.set_fill_color(252, 248, 248) if fill else pdf.set_fill_color(255, 255, 255)

            nome = pp(v.get("nome", ""))[:35]
            az   = pp(v.get("azienda", ""))[:28]
            sede = pp(v.get("luogo", ""))
            coll = pp(v.get("collocazione", ""))
            sede_txt = f"{sede} / {coll}" if coll else sede
            sede_txt = sede_txt[:22]

            vid = str(v.get('id', ''))[:8]
            row = [
                vid,
                nome,
                az,
                pp(v.get("annata", "")),
                pp(v.get("gradi", "")),
                sede_txt,
                f"E {to_float(v.get('prezzo', 0)):.2f}",
                str(to_int(v.get("qta", 0))),
            ]
            for i, txt in enumerate(row):
                pdf.cell(C[i], 6, txt, 1, 0, "C" if i in (0, 3, 4, 7) else "L", fill)
            pdf.ln()

            # Riga dettagli extra (vitigno, tipo, zucchero, formato, note)
            vitigno = pp(v.get("vitigno", ""))
            tipo    = pp(v.get("tipo_vino", ""))
            zuc     = pp(v.get("zucchero", ""))
            fmt     = pp(v.get("formato", ""))
            note    = pp(v.get("note", ""))[:60]
            dettagli = []
            if vitigno: dettagli.append(f"Vitigno: {vitigno}")
            if tipo:    dettagli.append(f"Tipo: {tipo}")
            if zuc:     dettagli.append(f"Zucchero: {zuc}")
            if fmt:     dettagli.append(f"Formato: {fmt}")
            if note:    dettagli.append(f"Note: {note}")
            if dettagli:
                pdf.set_font("Arial", "I", 6.5)
                pdf.set_text_color(100, 100, 100)
                pdf.set_fill_color(248, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(PAGE_W, 4.5, "    " + "   |   ".join(dettagli), 0, 1, "L", fill)
                pdf.set_font("Arial", "", 8)
                pdf.set_text_color(0, 0, 0)

        pdf.ln(4)

    return bytes(pdf.output())


def genera_pdf_etichette(lista, titolo="Etichette", num_offset=0):
    """Genera PDF con etichette stile originale: griglia 3×3 su A4 portrait.
    Ogni etichetta: cerchietto, #N grande, foto bottiglia, nome, azienda, annata, sede.
    num_offset: offset per la numerazione (es. se stampi da posizione 5, offset=4)."""
    import urllib.request, tempfile

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(8, 8, 8)
    pdf.set_auto_page_break(False)

    # Layout: 3 colonne × 3 righe su A4 portrait (210×297)
    E_W = 62     # larghezza etichetta
    E_H = 90     # altezza etichetta
    GAP_X = 3
    GAP_Y = 3
    COLS = 3
    ROWS = 3
    PAGE_W = 210 - 16  # 194mm utili
    MARGIN_X = (PAGE_W - COLS * E_W - (COLS - 1) * GAP_X) / 2

    for idx, v in enumerate(lista):
        col = idx % COLS
        row = (idx // COLS) % ROWS
        if col == 0 and row == 0:
            pdf.add_page()

        x = 8 + MARGIN_X + col * (E_W + GAP_X)
        y = 8 + row * (E_H + GAP_Y)

        # Bordo etichetta
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(x, y, E_W, E_H)

        # Cerchietto in alto al centro (segno per foro)
        cx = x + E_W / 2
        cy_circle = y + 4
        pdf.set_draw_color(180, 180, 180)
        pdf.ellipse(cx - 2.5, cy_circle - 2.5, 5, 5)

        # Numero grande
        num = idx + 1 + num_offset
        pdf.set_xy(x + 2, y + 7)
        pdf.set_font("Arial", "B", 22)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(E_W - 4, 10, f"#{num}", 0, 0, "L")

        # Foto bottiglia (se disponibile)
        foto_url = v.get("foto_url", "")
        img_y = y + 18
        img_h = 38
        if foto_url:
            try:
                req = urllib.request.Request(foto_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    img_data = resp.read()
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                tmp.write(img_data)
                tmp.close()
                # Centra l'immagine orizzontalmente
                pdf.image(tmp.name, x=x + E_W/2 - 12, y=img_y, h=img_h)
                import os
                os.unlink(tmp.name)
            except Exception:
                # Se fallisce, metti placeholder
                pdf.set_xy(x + 2, img_y + 10)
                pdf.set_font("Arial", "", 8)
                pdf.set_text_color(180, 180, 180)
                pdf.cell(E_W - 4, 5, "(no foto)", 0, 0, "C")
        else:
            pdf.set_xy(x + 2, img_y + 10)
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(180, 180, 180)
            pdf.cell(E_W - 4, 5, "(no foto)", 0, 0, "C")

        # Nome vino (sotto la foto)
        nome_y = img_y + img_h + 2
        pdf.set_xy(x + 2, nome_y)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(0, 0, 0)
        nome = pp(v.get("nome", ""))
        if len(nome) > 25:
            pdf.multi_cell(E_W - 4, 3.5, nome[:50], 0, "C")
        else:
            pdf.cell(E_W - 4, 4, nome[:25], 0, 0, "C")

        # Azienda (italico)
        pdf.set_xy(x + 2, nome_y + 5)
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(E_W - 4, 3.5, pp(v.get("azienda", ""))[:25], 0, 0, "C")

        # Annata
        annata = v.get("annata", "")
        if annata:
            pdf.set_xy(x + 2, nome_y + 9)
            pdf.set_font("Arial", "", 7)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(E_W - 4, 3.5, f"Annata: {annata}", 0, 0, "C")

        # Sede (in basso, italico piccolo)
        pdf.set_xy(x + 2, y + E_H - 7)
        pdf.set_font("Arial", "I", 6)
        pdf.set_text_color(120, 120, 120)
        sede = v.get("luogo", "")
        if sede:
            pdf.cell(E_W - 4, 3, f"SEDE: {pp(sede)}", 0, 0, "C")

    return bytes(pdf.output())




# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

def sidebar_superadmin():
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:20px 16px 10px;">
            <div style="font-size:1.5em;">🍷 <span style="font-weight:700;color:{ACCENT};">CantinaPro</span></div>
            <div style="font-size:0.72em;color:{TEXT_MUTED};margin-top:2px;">SUPERADMIN PANEL</div>
        </div>
        <hr style="margin:0 0 12px;">
        """, unsafe_allow_html=True)

        nav = [
            ("dashboard", "📊", "Dashboard"),
            ("clienti",   "👥", "Clienti"),
            ("cantina_view","🍷","Accedi Cantina"),
            ("impostazioni","⚙️","Impostazioni"),
        ]
        for page_id, icon, label in nav:
            active = "active" if st.session_state.page == page_id else ""
            if st.button(f"{icon}  {label}", key=f"nav_{page_id}", use_container_width=True,
                         type="secondary" if not active else "primary"):
                st.session_state.page = page_id
                st.session_state.id_modifica = None
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        user = st.session_state.user
        st.markdown(f"""
        <div style="padding:10px 14px;">
            <div style="font-size:0.8em;color:{TEXT_MUTED};">Connesso come</div>
            <div style="font-weight:600;font-size:0.9em;">{user.get('nome','Superadmin')}</div>
            <div style="font-size:0.75em;color:{TEXT_MUTED};">{user.get('email','')}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

def sidebar_admin(tenant):
    with st.sidebar:
        logo = tenant.get("logo_url","")
        st.markdown(f"""
        <div style="padding:20px 16px 10px;text-align:center;">
            {'<img src="'+logo+'" style="height:50px;border-radius:50%;margin-bottom:6px;" />' if logo else '<div style="font-size:2em;">🍷</div>'}
            <div style="font-weight:700;font-size:1.1em;color:{ACCENT};">{tenant.get('nome','La Mia Cantina')}</div>
            <div style="font-size:0.7em;color:{TEXT_MUTED};">{PIANI.get(tenant.get('piano','base'),'Base')}</div>
        </div>
        <hr style="margin:4px 0 12px;">
        """, unsafe_allow_html=True)

        nav = [
            ("dashboard",  "📊", "Dashboard"),
            ("vini",       "🍷", "I Miei Vini"),
            ("mignon",     "🥃", "Mignon"),
            ("portale",    "🌐", "Portale Vendita"),
            ("statistiche","📈", "Statistiche"),
            ("impostazioni","⚙️","Impostazioni"),
        ]
        for page_id, icon, label in nav:
            active = st.session_state.page == page_id
            if st.button(f"{icon}  {label}", key=f"nav_{page_id}", use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state.page = page_id
                st.session_state.id_modifica = None
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="padding:10px 14px;">
            <div style="font-size:0.75em;color:{TEXT_MUTED};">Connesso come</div>
            <div style="font-weight:600;font-size:0.85em;">{tenant.get('nome','')}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.ruolo == "superadmin":
            if st.button("↩ Torna Superadmin", use_container_width=True, type="secondary"):
                st.session_state.tenant_view = None
                st.session_state.page = "clienti"
                st.rerun()
        else:
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                for k in list(st.session_state.keys()): del st.session_state[k]
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGINE SUPERADMIN
# ─────────────────────────────────────────────────────────────────────────────

def page_superadmin_dashboard():
    st.markdown(f"<h2 style='color:{ACCENT};'>📊 Dashboard Globale</h2>", unsafe_allow_html=True)
    stats = db.get_stats_globali()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("👥 Clienti Attivi",    stats["n_clienti"])
    c2.metric("🍷 Bottiglie Totali",  f"{stats['n_bottiglie']:,}")
    c3.metric("💶 Valore Stimato",    f"€ {stats['valore_totale']:,.0f}")
    c4.metric("📋 Record Vini",       stats["n_vini_records"])

    st.markdown("---")
    st.markdown(f"<h3 style='color:{TEXT_MAIN};'>Ultimi Clienti</h3>", unsafe_allow_html=True)
    tenants = db.get_all_tenants()[:5]
    for t in tenants:
        with st.container():
            c1,c2,c3 = st.columns([3,1,1])
            badge = f'<span class="badge-attivo">Attivo</span>' if t.get("attivo") else f'<span class="badge-disattivo">Disattivo</span>'
            piano = f'<span class="badge-piano">{PIANI.get(t.get("piano","base"),"Base")}</span>'
            c1.markdown(f"**{t['nome']}** {badge} {piano}", unsafe_allow_html=True)
            c1.caption(t.get("email",""))
            if c2.button("Accedi", key=f"acc_{t['id']}", type="secondary"):
                st.session_state.tenant_view = t
                st.session_state.page = "dashboard"
                st.rerun()
            st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

def page_superadmin_clienti():
    st.markdown(f"<h2 style='color:{ACCENT};'>👥 Gestione Clienti</h2>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Lista Clienti", "➕ Nuovo Cliente"])

    with tab1:
        tenants = db.get_all_tenants()
        cerca = st.text_input("🔍 Cerca cliente...", "").lower()
        filtrati = [t for t in tenants if not cerca or cerca in t.get("nome","").lower() or cerca in t.get("email","").lower()]

        st.markdown(f"**{len(filtrati)} clienti**")
        st.markdown("---")

        for t in filtrati:
            with st.expander(f"{'🟢' if t.get('attivo') else '🔴'} {t['nome']} — {t.get('email','')}"):
                c1,c2,c3,c4 = st.columns([2,1,1,1])
                with c1:
                    st.markdown(f"**Email:** {t.get('email','')}")
                    st.markdown(f"**Piano:** {PIANI.get(t.get('piano','base'),'Base')}")
                    st.markdown(f"**Portale:** {'✅ Attivo — '+t.get('portale_slug','') if t.get('portale_attivo') else '❌ Disattivo'}")
                    if t.get("note_admin"): st.markdown(f"**Note:** {t['note_admin']}")
                    st.caption(f"Creato: {str(t.get('created_at',''))[:10]}")
                with c2:
                    if st.button("🔑 Accedi", key=f"acc_{t['id']}", use_container_width=True):
                        st.session_state.tenant_view = t
                        st.session_state.page = "dashboard"
                        st.rerun()
                with c3:
                    lbl = "🔴 Disattiva" if t.get("attivo") else "🟢 Attiva"
                    if st.button(lbl, key=f"tog_{t['id']}", use_container_width=True, type="secondary"):
                        db.toggle_tenant(t["id"], not t.get("attivo", True))
                        st.rerun()
                with c4:
                    st.markdown("")
                    st.caption(f"ID: {str(t['id'])[:8]}…")

    with tab2:
        with st.form("nuovo_cliente"):
            st.markdown("#### Dati Cliente")
            n_nome     = st.text_input("Nome / Ragione sociale *")
            n_email    = st.text_input("Email *")
            n_pass     = st.text_input("Password *", type="password")
            n_tel      = st.text_input("Telefono")
            n_piano    = st.selectbox("Piano", list(PIANI.keys()), format_func=lambda k: PIANI[k])
            n_slug     = st.text_input("Slug portale (es. cantina-rossi)", help="URL-friendly, senza spazi")
            n_portale  = st.checkbox("Portale vendita attivo")
            n_note     = st.text_area("Note interne")

            if st.form_submit_button("✅ CREA CLIENTE", type="primary"):
                if not n_nome or not n_email or not n_pass:
                    st.error("Nome, email e password sono obbligatori.")
                else:
                    payload = {
                        "nome": n_nome, "email": n_email.lower(), "password": n_pass,
                        "telefono": n_tel, "piano": n_piano,
                        "portale_slug": n_slug.strip().lower().replace(" ","-") or None,
                        "portale_attivo": n_portale, "note_admin": n_note, "attivo": True, "ruolo": "admin"
                    }
                    result = db.create_tenant(payload)
                    if result.get("id"):
                        st.success(f"✅ Cliente '{n_nome}' creato con successo!")
                        st.rerun()
                    else:
                        st.error("Errore nella creazione — email già in uso?")

def page_superadmin_settings():
    st.markdown(f"<h2 style='color:{ACCENT};'>⚙️ Impostazioni Superadmin</h2>", unsafe_allow_html=True)
    user = st.session_state.user
    st.info(f"**Account:** {user.get('nome')} · {user.get('email')} · Ruolo: superadmin")
    with st.form("upd_superadmin"):
        nn = st.text_input("Nome", user.get("nome",""))
        np = st.text_input("Nuova password", type="password", placeholder="lascia vuoto per non cambiare")
        if st.form_submit_button("Salva", type="primary"):
            data = {"nome": nn}
            if np: data["password"] = np
            db.update_tenant(user["id"], data)
            st.session_state.user["nome"] = nn
            st.success("Salvato!")

# ─────────────────────────────────────────────────────────────────────────────
# DIALOGO SCHEDA VINO
# ─────────────────────────────────────────────────────────────────────────────

@st.dialog("📖 Scheda Tecnica")
def dialog_scheda(v):
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if v.get("foto_url"):
            st.image(v["foto_url"], use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;padding:40px;color:#666;font-size:2em;'>📷</div>", unsafe_allow_html=True)
    with c2:
        def r(icon, label, val):
            if not val or val in ("N.D.", "", "0", "0.0", "0,00"): val = "—"
            return (f'<div style="margin-bottom:10px;line-height:1.4;">'
                    f'<span style="color:#C9A84C;font-weight:700;font-size:0.8em;letter-spacing:0.5px;text-transform:uppercase;">{icon} {label}</span>'
                    f'<br><span style="color:#F0EDE8;font-size:1em;">{val}</span></div>')

        precio = to_float(v.get("prezzo", 0))
        luogo = v.get("luogo", "—")
        colloc = f' · {v.get("collocazione")}' if v.get("collocazione") else ""
        prov = v.get("provenienza", "")

        vid_short = str(v.get('id',''))[:8]
        html = (
            f'<div style="font-size:0.72em;color:#888;font-family:monospace;margin-bottom:6px;">ID: {vid_short}</div>'
            f'<h3 style="color:#C9A84C;margin-bottom:16px;font-size:1.3em;border-bottom:1px solid #2A2A2A;padding-bottom:10px;">{v["nome"]}</h3>'
            + r("🏭", "Cantina", v.get("azienda", ""))
            + r("📅", "Annata", v.get("annata", ""))
            + r("📊", "Gradi", f'{v.get("gradi","")}%' if v.get("gradi") else "")
            + r("🍇", "Vitigno", v.get("vitigno", ""))
            + r("🍾", "Tipo", v.get("tipo_vino", ""))
            + r("🍬", "Zucchero", v.get("zucchero", ""))
            + r("📏", "Formato", v.get("formato", ""))
            + r("💶", "Prezzo", f"€ {precio:,.2f}")
            + r("📍", "Sede", f"{luogo}{colloc}")
            + (r("🎁", "Fonte", prov) if prov else "")
        )
        st.markdown(f'<div style="padding:4px 0;">{html}</div>', unsafe_allow_html=True)

    if v.get("note") or v.get("giudizio"):
        st.divider()
        if v.get("note"):
            st.markdown(f'<div><span style="color:#C9A84C;font-weight:700;font-size:0.8em;">📝 NOTE</span><br><span style="color:#F0EDE8;">{v["note"]}</span></div>', unsafe_allow_html=True)
        if v.get("giudizio"):
            st.markdown(f'<div style="margin-top:10px;"><span style="color:#C9A84C;font-weight:700;font-size:0.8em;">🍷 GIUDIZIO</span><br><span style="color:#F0EDE8;">{v["giudizio"]}</span></div>', unsafe_allow_html=True)


@st.dialog("🍷 Stappa e Giudica")
def dialog_stappa(v, tenant_id, tipo):
    st.markdown(f"### {v['nome']}")
    giudizio = st.text_area("Com'era questo vino?", placeholder="Profumo, sapore, persistenza...")
    st.markdown(f"**Quantità attuale:** {v['qta']} pz")
    if st.button("✅ Confermo lo stappo", type="primary"):
        if tipo == "vini":
            if int(v.get("qta",1)) > 1:
                db.update_vino(v["id"], tenant_id, {"qta": int(v["qta"])-1})
                copia = {k:val for k,val in v.items() if k not in ("id","created_at")}
                copia.update({"qta":0,"tipo_cat":"Provati","giudizio":giudizio,"cat_origine":v.get("tipo_cat","Rossi"),"tenant_id":tenant_id})
                db.insert_vino(tenant_id, copia)
            else:
                db.update_vino(v["id"], tenant_id, {"qta":0,"tipo_cat":"Provati","giudizio":giudizio,"cat_origine":v.get("tipo_cat","Rossi")})
        db.get_vini.clear()
        st.rerun()

@st.dialog("🗑️ Elimina vino")
def dialog_delete(v, tipo):
    st.markdown(f"Sei sicuro di voler eliminare **{v.get('nome','')}**?")
    if v.get("azienda"): st.caption(f"🏭 {v['azienda']}  ·  {v.get('annata','')}")
    st.warning("L'operazione è irreversibile. La foto verrà rimossa dallo storage cloud.")
    c1, c2 = st.columns(2)
    if c1.button("✖ Annulla", use_container_width=True, type="secondary"):
        st.rerun()
    if c2.button("🗑️ Elimina definitivamente", use_container_width=True, type="primary"):
        # Pulizia foto orfana dallo storage
        foto_url = v.get("foto_url", "")
        if foto_url:
            try:
                # Estrae il path relativo dall'URL pubblico
                bucket_marker = "/cantina-images/"
                if bucket_marker in foto_url:
                    path = foto_url.split(bucket_marker)[1].split("?")[0]
                    db.get_sb().storage.from_("cantina-images").remove([path])
            except Exception:
                pass
        if tipo == "vini":
            db.delete_vino(v["id"], v.get("tenant_id", ""))
        else:
            db.delete_mignon(v["id"], v.get("tenant_id", ""))
        db.get_vini.clear()
        db.get_mignon.clear()
        st.success(f"✅ '{v.get('nome','')}' eliminato.")
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MODULO FORM VINO (aggiunta / modifica)
# ─────────────────────────────────────────────────────────────────────────────

def form_vino(tenant_id, tipo="vini", vino_esistente=None):
    """Ritorna True se il form è stato inviato con successo."""
    v = vino_esistente or {}
    folder = tipo
    is_edit = v.get("id") is not None

    # Dati esistenti per categorie e luoghi
    tutti_vini = db.get_vini(tenant_id) if tipo == "vini" else db.get_mignon(tenant_id)
    luoghi_in_db = sorted(set(x.get("luogo","") for x in tutti_vini if x.get("luogo")))
    cats_in_db   = sorted(set(x.get("tipo_cat","") for x in tutti_vini if x.get("tipo_cat")))
    luoghi_full  = sorted(set(["Casa Principale","Casa al Mare","Casa in Montagna","Ufficio"] + luoghi_in_db))
    cats_full    = list(dict.fromkeys(CATEGORIE_BASE + [c for c in cats_in_db if c not in CATEGORIE_BASE]))

    with st.form(f"form_vino_{v.get('id','new')}_{tipo}"):
        co1,co2 = st.columns(2)
        with co1:
            nome   = st.text_input("🍷 Nome *", v.get("nome",""))
            azienda= st.text_input("🏭 Cantina / Produttore", v.get("azienda",""))
            annata = st.text_input("📅 Annata", v.get("annata",""))
            vitigno= st.text_input("🍇 Vitigno", v.get("vitigno",""))
            gradi  = st.text_input("% Gradi alcolici", v.get("gradi",""))
        with co2:
            prezzo = st.number_input("💶 Prezzo (€)", value=to_float(v.get("prezzo",0)), step=0.5)
            qta    = st.number_input("📦 Quantità", value=to_int(v.get("qta",1)), min_value=0)
            fmt_in = st.text_input("🍾 Formato (es: 0.75)", v.get("formato","0.75").split("(")[0].replace("L","").strip() or "0.75")
            prov   = st.text_input("🎁 Fonte / Regalo", v.get("provenienza",""))

        if tipo == "vini":
            co3,co4 = st.columns(2)
            with co3:
                sel_cat  = st.selectbox("Categoria", cats_full,
                                        index=cats_full.index(v.get("tipo_cat","⚠️ DA CATALOGARE")) if v.get("tipo_cat") in cats_full else 0)
                new_cat  = st.text_input("…o nuova categoria", "")
                tipo_vino= st.selectbox("Tipo vino", TIPI_VINO,
                                        index=TIPI_VINO.index(v.get("tipo_vino","Fermo")) if v.get("tipo_vino") in TIPI_VINO else 0)
                zucchero = st.selectbox("Zuccheri", SCALA_ZUCCHERI,
                                        index=SCALA_ZUCCHERI.index(v.get("zucchero","N.S.")) if v.get("zucchero") in SCALA_ZUCCHERI else 0)
            with co4:
                sel_luogo   = st.selectbox("📍 Sede / Stanza", luoghi_full,
                                           index=luoghi_full.index(v.get("luogo","Casa Principale")) if v.get("luogo") in luoghi_full else 0)
                new_luogo   = st.text_input("…o nuova sede", "")
                collocazione= st.text_input("📦 Posizione (es. Scaffale B)", v.get("collocazione",""))
        else:
            sel_cat="Mignon"; new_cat=""; tipo_vino="Fermo"; zucchero="N.S."
            sel_luogo="Casa Principale"; new_luogo=""; collocazione=""

        note = st.text_area("📝 Note", v.get("note",""), height=80)
        foto = st.file_uploader("📸 Foto etichetta", type=["jpg","jpeg","png"])
        if v.get("foto_url"):
            st.image(v["foto_url"], width=120, caption="Foto attuale")

        submitted = st.form_submit_button("💾 SALVA" if is_edit else "➕ INSERISCI",
                                          type="primary", use_container_width=True)

        if submitted:
            if not nome.strip():
                st.error("Il nome è obbligatorio.")
                return False
            foto_url = v.get("foto_url","")
            if foto: foto_url = salva_img_cloud(foto, folder)
            final_cat   = new_cat.strip().title() if new_cat.strip() else sel_cat
            final_luogo = new_luogo.strip().title() if new_luogo.strip() else sel_luogo
            payload = {
                "nome":nome, "azienda":azienda, "annata":annata, "vitigno":vitigno,
                "gradi":gradi, "prezzo":prezzo, "qta":qta,
                "formato":calcola_formato(fmt_in), "provenienza":prov,
                "luogo":final_luogo, "collocazione":collocazione,
                "note":note, "foto_url":foto_url,
                "tipo_cat":final_cat,
                "giudizio":v.get("giudizio",""), "cat_origine":v.get("cat_origine",""),
            }
            if tipo == "vini":
                payload.update({"tipo_vino":tipo_vino, "zucchero":zucchero})
            if is_edit:
                db.update_vino(v["id"], tenant_id, payload) if tipo=="vini" else db.update_mignon(v["id"], tenant_id, payload)
            else:
                db.insert_vino(tenant_id, payload) if tipo=="vini" else db.insert_mignon(tenant_id, payload)
            db.get_vini.clear()
            db.get_mignon.clear()
            return True
    return False

# ─────────────────────────────────────────────────────────────────────────────
# PAGINE ADMIN — CANTINA
# ─────────────────────────────────────────────────────────────────────────────

def page_admin_dashboard(tenant):
    tid = tenant["id"]
    st.markdown(f"<h2 style='color:{ACCENT};'>📊 La Mia Cantina</h2>", unsafe_allow_html=True)


    vini   = db.get_vini(tid)
    mignon = db.get_mignon(tid)
    tv, vv = calcola_totali(vini)
    tm, vm = calcola_totali(mignon)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🍷 Bottiglie", f"{tv:,}")
    c2.metric("💶 Valore Cantina", f"€ {vv:,.0f}")
    c3.metric("🥃 Mignon", f"{tm:,}")
    c4.metric("💶 Valore Mignon", f"€ {vm:,.0f}")

    st.markdown("---")

    # ── Sedi ──────────────────────────────────────────────────────────
    sedi = sorted(set(v.get("luogo","") for v in vini if v.get("luogo") and v.get("luogo") != "None"))


    if sedi:
        st.markdown("#### 🏠 Le Tue Sedi")
        cols = st.columns(min(len(sedi), 6))
        for i, sede in enumerate(sedi):
            vs = [v for v in vini if v.get("luogo")==sede
                  and v.get("tipo_cat")!="Provati"
                  and to_int(v.get("qta",0)) > 0]
            bt, val = calcola_totali(vs)
            with cols[i % 6]:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="val">{bt}</div>
                    <div class="lbl">📍 {sede}</div>
                    <div style="font-size:0.78em;color:{ACCENT};margin-top:4px;">€ {val:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Bottiglie Terminate ──────────────────────────────────────────
    terminate = [v for v in vini if to_int(v.get("qta",0)) == 0
                 and v.get("tipo_cat") != "Provati"
                 and v.get("nome","").strip()
                 and not v.get("nome","").startswith("[Sede:")]
    if terminate:
        with st.expander(f"🍾 Bottiglie Terminate ({len(terminate)})", expanded=False):
            for v in sorted(terminate, key=lambda x: x.get("nome","")):
                vid = str(v.get("id",""))[:8]
                sede_orig = v.get("luogo", "—")
                st.markdown(f"""<div style="padding:6px 10px;border-bottom:1px solid #1e1e1e;
                    font-size:0.88em;display:flex;justify-content:space-between;">
                    <span><code style="color:#888;">{vid}</code> &nbsp;
                    <b>{v.get('nome','')}</b>
                    <span style="color:{TEXT_MUTED};"> · {v.get('azienda','')}</span></span>
                    <span style="color:{TEXT_MUTED};font-size:0.85em;">ex: {sede_orig}</span>
                </div>""", unsafe_allow_html=True)


    st.markdown("---")

    # ── PDF Downloads ──
    giacenza = [v for v in vini if to_int(v.get("qta",0))>0 and v.get("tipo_cat")!="Provati"]
    nome_f   = tenant.get("nome","cantina").lower().replace(" ","_")

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        if giacenza:
            try:
                _b = genera_pdf_lista(giacenza, f"Giacenza - {tenant['nome']}")
                st.download_button("Scarica Lista PDF", data=_b,
                                   file_name="cantina.pdf", mime="application/pdf",
                                   use_container_width=True, key="dl_lista")
            except Exception as _e:
                st.warning(f"⚠️ PDF non disponibile: {_e}")
    with pc2:
        if sedi:
            sede_sel = st.selectbox("Sede", sedi, key="sede_divisa_sel",
                                    label_visibility="collapsed")
            vini_sede = [v for v in vini if v.get("luogo")==sede_sel
                         and v.get("tipo_cat")!="Provati"
                         and to_int(v.get("qta",0))>0]
            if vini_sede:
                try:
                    _b2 = genera_pdf_lista(vini_sede, f"Lista - {sede_sel} ({tenant['nome']})")
                    st.download_button(f"Divisa {sede_sel}", data=_b2,
                                       file_name=f"divisa_{sede_sel.lower().replace(' ','_')}.pdf",
                                       mime="application/pdf",
                                       use_container_width=True, key="dl_divisa")
                except Exception as _e:
                    st.warning(f"⚠️ PDF non disponibile: {_e}")
    with pc3:
        if giacenza:
            try:
                _b3 = genera_pdf_catalogo(giacenza, tenant.get("nome","Cantina"))
                st.download_button("Catalogo PDF", data=_b3,
                                   file_name=f"catalogo_{nome_f}.pdf",
                                   mime="application/pdf",
                                   use_container_width=True, type="primary",
                                   key="dl_cat")
            except Exception as _e:
                st.warning(f"⚠️ PDF non disponibile: {_e}")
    st.markdown("---")

    # ── STAMPA ETICHETTE CON INTERVALLO ───────────────────────────────
    if giacenza:
        st.markdown(f"""<div style='font-size:1em;font-weight:600;color:{ACCENT};margin-bottom:8px;'>
            🏷️ Stampa Etichette
            <div style='font-size:0.75em;font-weight:400;color:#888;margin-top:4px;'>
            Seleziona l'intervallo di vini da stampare (per non ristampare etichette gi&agrave; fatte).
            </div></div>""", unsafe_allow_html=True)

        # Numera i vini in giacenza per dare un indice leggibile
        et1, et2, et3 = st.columns([1, 1, 1])
        with et1:
            id_da = st.number_input("Da posizione", min_value=1, max_value=len(giacenza),
                                     value=1, step=1, key="et_da")
        with et2:
            id_a = st.number_input("A posizione", min_value=1, max_value=len(giacenza),
                                    value=len(giacenza), step=1, key="et_a")
        with et3:
            st.markdown(f"<div style='padding-top:28px;font-size:0.85em;color:{TEXT_MUTED};'>"
                        f"Totale: <b style='color:{ACCENT};'>{max(0, id_a - id_da + 1)}</b> etichette"
                        f"</div>", unsafe_allow_html=True)

        if id_da <= id_a:
            selezione = giacenza[id_da - 1 : id_a]
            if selezione:
                try:
                    _b_et = genera_pdf_etichette(selezione,
                                f"Etichette {tenant.get('nome','Cantina')} ({id_da}-{id_a})",
                                num_offset=id_da - 1)
                    st.download_button(f"Stampa {len(selezione)} etichette (pos. {id_da}–{id_a})",
                                       data=_b_et,
                                       file_name=f"etichette_{id_da}_{id_a}.pdf",
                                       mime="application/pdf",
                                       use_container_width=True, key="dl_etichette")
                except Exception as e:
                    st.error(f"Errore PDF etichette: {e}")

    st.markdown("---")

    # ── QR CODE PER SEDE ─────────────────────────────────────────────
    slug = tenant.get("portale_slug", "")
    if sedi and slug:
        st.markdown(f"""<div style='font-size:1em;font-weight:600;color:{ACCENT};margin-bottom:12px;'>
            Lista Ospiti — QR Code per Sede
            <div style='font-size:0.75em;font-weight:400;color:#888;margin-top:4px;'>
            Stampa il QR e consegnalo agli ospiti: scannerizzano e vedono la lista vini.
            </div></div>""", unsafe_allow_html=True)

        import qrcode, urllib.parse
        qr_cols = st.columns(min(len(sedi), 4))
        for i, sede in enumerate(sedi):
            url_lista = f"{APP_BASE_URL}?lista={slug}&luogo={urllib.parse.quote(sede)}"
            n_vini = len([v for v in vini if v.get("luogo")==sede and v.get("tipo_cat")!="Provati" and to_int(v.get("qta",0))>0])

            qr = qrcode.QRCode(version=1, box_size=8, border=2,
                               error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(url_lista)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="#8B1A1A", back_color="white").convert("RGB")
            qr_w, qr_h = img_qr.size

            card_w = qr_w + 60
            card_h = qr_h + 200
            card = Image.new("RGB", (card_w, card_h), color="#FFFFFF")
            from PIL import ImageDraw
            draw = ImageDraw.Draw(card)
            draw.rectangle([0, 0, card_w, 60], fill="#8B1A1A")
            draw.rectangle([0, 60, card_w, 120], fill="#F9F4F4")
            draw.text((card_w//2, 90), tenant.get("nome","Cantina")[:30], fill="#8B1A1A", anchor="mm")
            draw.text((card_w//2, 120), f"Sede: {sede}", fill="#555555", anchor="mm")
            card.paste(img_qr, (30, 145))
            y_txt = 145 + qr_h + 12
            draw.rectangle([0, y_txt-4, card_w, card_h], fill="#F9F4F4")
            draw.text((card_w//2, y_txt+10), "Scansiona per vedere la lista vini", fill="#8B1A1A", anchor="mm")
            draw.text((card_w//2, y_txt+28), f"{n_vini} etichette disponibili", fill="#999999", anchor="mm")
            draw.rectangle([0, 0, card_w-1, card_h-1], outline="#CCCCCC", width=2)

            buf_card = BytesIO()
            card.save(buf_card, format="PNG", dpi=(300,300))
            card_bytes = buf_card.getvalue()

            buf_preview = BytesIO()
            card.thumbnail((200,300))
            card.save(buf_preview, format="PNG")
            buf_preview.seek(0)
            prev_b64 = base64.b64encode(buf_preview.read()).decode()

            with qr_cols[i % 4]:
                st.markdown(f'<img src="data:image/png;base64,{prev_b64}" style="width:100%;border-radius:8px;margin-bottom:8px;border:1px solid #2A2A2A;"/>', unsafe_allow_html=True)
                st.download_button(
                    label=f"Scarica QR - {sede}",
                    data=card_bytes,
                    file_name=f"lista_qr_{sede.lower().replace(' ','_')}.png",
                    mime="image/png",
                    use_container_width=True,
                    key=f"qr_dl_{i}"
                )
                wa_msg = urllib.parse.quote(f"Lista vini {tenant.get('nome',sede)} - {sede}: {url_lista}")
                st.markdown(
                    f'<a href="https://wa.me/?text={wa_msg}" target="_blank" '
                    f'style="display:block;text-align:center;font-size:0.82em;'
                    f'color:#25D366;margin-top:6px;text-decoration:none;font-weight:600;">WhatsApp</a>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div style="background:#1a1a1a;border:1px solid #333;border-radius:6px;'
                    f'padding:6px 8px;margin-top:2px;font-size:0.65em;color:#aaa;word-break:break-all;text-align:center;">'
                    f'<a href="{url_lista}" target="_blank" style="color:#C9A84C;text-decoration:none;">{url_lista}</a></div>',
                    unsafe_allow_html=True
                )


def grid_vini(tenant, tipo="vini"):
    tid = tenant["id"]
    data_fn = db.get_vini if tipo=="vini" else db.get_mignon
    data = data_fn(tid)

    # Filtri
    with st.expander("🔍 Filtri e ricerca", expanded=False):
        fc1,fc2 = st.columns(2)
        txt = fc1.text_input("Cerca", "").lower()
        luoghi = sorted(set(v.get("luogo","") for v in data if v.get("luogo")))
        luogo_f = fc2.selectbox("Sede", ["TUTTE"] + luoghi)
        fc3,fc4 = st.columns(2)
        cats = list(dict.fromkeys(CATEGORIE_BASE + [v.get("tipo_cat","") for v in data if v.get("tipo_cat") not in CATEGORIE_BASE]))
        cat_f = fc3.selectbox("Categoria", ["TUTTI"] + cats)
        formati = sorted(set(v.get("formato","") for v in data if v.get("formato")))
        fmt_f = fc4.selectbox("🍾 Formato", ["TUTTI"] + formati)

    # Aggiungi nuovo
    with st.expander("➕ Aggiungi nuovo vino", expanded=False):
        if form_vino(tid, tipo):
            st.success("✅ Inserito!")
            st.rerun()

    st.markdown("---")

    # Modifica in pagina
    if st.session_state.id_modifica:
        vino_m = next((v for v in data if v["id"] == st.session_state.id_modifica), None)
        if vino_m:
            st.markdown(f"""
            <div style="background:#1E1E1E;border:1px solid {PRIMARY};border-radius:12px;
                        padding:20px;margin-bottom:20px;">
                <div style="font-size:1em;font-weight:600;color:{ACCENT};margin-bottom:12px;"
                >✏️ Modifica: {vino_m['nome']}</div>
            """, unsafe_allow_html=True)
            if form_vino(tid, tipo, vino_m):
                st.session_state.id_modifica = None
                st.success("✅ Salvato!")
                st.rerun()
            col_ann, _ = st.columns([1,3])
            if col_ann.button("✖ Chiudi", use_container_width=True, type="secondary"):
                st.session_state.id_modifica = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Lista filtrata
    vini_f = []
    for v in reversed(data):
        if txt and not any(txt in str(val).lower() for val in v.values()): continue
        if luogo_f != "TUTTE" and v.get("luogo") != luogo_f: continue
        if fmt_f != "TUTTI" and v.get("formato","") != fmt_f: continue
        q = to_int(v.get("qta",0))
        if cat_f == "TUTTI":
            if q <= 0: continue
        elif cat_f == "Provati":
            if v.get("tipo_cat") != "Provati" and q > 0: continue
        else:
            if v.get("tipo_cat") != cat_f or q <= 0: continue
        vini_f.append(v)

    st.markdown(f"**{len(vini_f)} bottiglie trovate**")

    # ── PAGINAZIONE ──────────────────────────────────────────────────────────
    PER_PAG = 50
    n_tot   = len(vini_f)
    n_pag   = max(1, (n_tot + PER_PAG - 1) // PER_PAG)

    # Reset pagina se cambiano i filtri (chiave = combinazione filtri attivi)
    _filtro_key = f"{tipo}|{txt}|{luogo_f}|{cat_f}|{fmt_f}"
    if st.session_state.get("inv_tipo_key") != _filtro_key:
        st.session_state.inv_pagina  = 0
        st.session_state.inv_tipo_key = _filtro_key

    pg = st.session_state.inv_pagina
    pg = max(0, min(pg, n_pag - 1))  # clamp sicuro
    st.session_state.inv_pagina = pg

    inizio = pg * PER_PAG
    fine   = min(inizio + PER_PAG, n_tot)
    vini_pag = vini_f[inizio:fine]

    if n_pag > 1:
        pa1, pa2, pa3 = st.columns([1, 3, 1])
        if pa1.button("← Prec.", disabled=(pg == 0), key=f"pag_prec_{tipo}", use_container_width=True):
            st.session_state.inv_pagina = pg - 1; st.rerun()
        pa2.markdown(
            f"<div style='text-align:center;color:{TEXT_MUTED};font-size:0.85em;padding-top:6px;'>"
            f"Pagina <b>{pg+1}</b> di <b>{n_pag}</b> · {inizio+1}–{fine} di {n_tot}"
            f"</div>", unsafe_allow_html=True)
        if pa3.button("Succ. →", disabled=(pg >= n_pag-1), key=f"pag_next_{tipo}", use_container_width=True):
            st.session_state.inv_pagina = pg + 1; st.rerun()

    cols = st.columns(3)
    for j, v in enumerate(vini_pag):
        with cols[j % 3]:
            q = to_int(v.get("qta",0))
            cat = v.get("tipo_cat","")
            loc = v.get("luogo","")
            coll= v.get("collocazione","")

            # XSS guard: escape tutti i dati utente prima di inserirli in HTML
            _nome = _html.escape(str(v.get('nome', '')))
            _cat  = _html.escape(str(cat))
            _az   = _html.escape(str(v.get('azienda', '')))
            _ann  = _html.escape(str(v.get('annata', '')))
            _loc  = _html.escape(str(loc))
            _cll  = _html.escape(str(coll))
            _fmt  = _html.escape(str(v.get('formato', '0.75 L')))
            _giud = _html.escape(str(v.get('giudizio', '')[:50]))

            st.markdown(f"""
            <div class="wine-card">
                <div class="wine-card-header">
                    {_nome}
                    <span class="wine-badge">{_cat}</span>
                </div>
            """, unsafe_allow_html=True)

            if v.get("foto_url"): st.image(v["foto_url"], use_container_width=True)

            vid_short = str(v.get('id',''))[:8]
            _prezzo = to_float(v.get('prezzo', 0))
            _qta_color = '#C9A84C' if q > 3 else ('#f59e0b' if q > 0 else '#ef4444')
            _loc_html = (f'<div style="font-size:0.78em;color:{TEXT_MUTED};">&#128205; {_loc}'
                         + (f' &middot; {_cll}' if _cll else '') + '</div>') if _loc else ''
            _giud_html = (f'<div style="font-size:0.78em;color:#d97706;margin-top:4px;font-style:italic;">🍷 {_giud}…</div>'
                          if v.get("giudizio") else '')
            st.markdown(f"""
            <div style="padding:10px 12px;">
                <div style="font-size:0.7em;color:#888;font-family:monospace;margin-bottom:4px;">ID: {vid_short}</div>
                <div style="font-size:1.2em;font-weight:700;color:{ACCENT};">&#8364; {_prezzo:,.2f}</div>
                <div style="color:{TEXT_MUTED};font-size:0.8em;">{_az} &middot; {_ann}</div>
                <div style="margin-top:6px;font-size:0.82em;">
                    🍾 {_fmt} &nbsp;|&nbsp;
                    📦 Qta: <b style="color:{_qta_color};">{q}</b>
                </div>
                {_loc_html}
                {_giud_html}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Azioni
            a1,a2,a3,a4,a5,a6 = st.columns(6)
            if a1.button("−", key=f"m_{tipo}_{v['id']}", help="Decrementa"):
                if tipo == "vini":
                    db.update_vino(v["id"], tid, {"qta": max(0, q-1)})
                else:
                    db.update_mignon(v["id"], tid, {"qta": max(0, q-1)})
                db.get_vini.clear(); db.get_mignon.clear(); st.rerun()
            if a2.button("+", key=f"p_{tipo}_{v['id']}", help="Incrementa"):
                if tipo == "vini":
                    db.update_vino(v["id"], tid, {"qta": q+1})
                else:
                    db.update_mignon(v["id"], tid, {"qta": q+1})
                db.get_vini.clear(); db.get_mignon.clear(); st.rerun()
            if a3.button("✏️", key=f"e_{tipo}_{v['id']}", help="Modifica"):
                st.session_state.id_modifica = v["id"]; st.rerun()
            if a4.button("📖", key=f"s_{tipo}_{v['id']}", help="Scheda"):
                dialog_scheda(v)
            if a5.button("🍷", key=f"sta_{tipo}_{v['id']}", help="Stappa") and tipo=="vini":
                dialog_stappa(v, tid, tipo)
            if a6.button("🗑️", key=f"del_{tipo}_{v['id']}", help="Elimina"):
                dialog_delete(v, tipo)

def page_admin_portale(tenant):
    tid = tenant["id"]
    st.markdown(f"<h2 style='color:{ACCENT};'>🌐 Portale di Vendita</h2>", unsafe_allow_html=True)

    attivo = tenant.get("portale_attivo", False)
    slug   = tenant.get("portale_slug","")

    if attivo and slug:
        url_pub = f"{APP_BASE_URL}?portale={slug}"
        st.success(f"✅ Portale attivo!")
        st.code(url_pub, language=None)
        st.markdown(f"[🔗 Apri il portale]({url_pub})")
        import urllib.parse as _up
        wa_msg = _up.quote(f"Visita il mio catalogo vini: {url_pub}")
        st.markdown(f'<a href="https://wa.me/?text={wa_msg}" target="_blank" style="font-size:0.85em;color:#25D366;font-weight:600;">📲 Condividi su WhatsApp</a>', unsafe_allow_html=True)
    else:
        st.warning("Il portale di vendita non è ancora attivo. Contatta l'amministratore per abilitarlo.")

    st.markdown("---")
    st.markdown("#### Anteprima catalogo pubblico")

    vini_pub = db.get_vini_portale(tid)
    st.markdown(f"**{len(vini_pub)} vini nel catalogo pubblico** (qta > 0, non Provati)")

    if vini_pub:
        cols = st.columns(4)
        for i, v in enumerate(vini_pub[:8]):
            with cols[i%4]:
                if v.get("foto_url"): st.image(v["foto_url"], use_container_width=True)
                st.caption(f"{v['nome']} · € {to_float(v.get('prezzo',0)):.2f}")

def page_admin_statistiche(tenant):
    tid = tenant["id"]
    st.markdown(f"<h2 style='color:{ACCENT};'>📈 Statistiche</h2>", unsafe_allow_html=True)

    vini = db.get_vini(tid)
    attivi = [v for v in vini if to_int(v.get("qta",0))>0 and v.get("tipo_cat")!="Provati"]

    # Per categoria
    cat_data = {}
    for v in attivi:
        c = v.get("tipo_cat","Altro")
        cat_data[c] = cat_data.get(c, {"n":0,"val":0})
        cat_data[c]["n"]   += to_int(v.get("qta",0))
        cat_data[c]["val"] += to_int(v.get("qta",0)) * to_float(v.get("prezzo",0))

    st.markdown("#### Per Categoria")
    if cat_data:
        for cat, d in sorted(cat_data.items(), key=lambda x: -x[1]["n"]):
            pct = int(d["n"] / sum(x["n"] for x in cat_data.values()) * 100)
            st.markdown(f"""
            <div style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:0.85em;">
                    <span>{cat}</span><span style="color:{ACCENT};">{d['n']} pz · € {d['val']:,.0f}</span>
                </div>
                <div style="background:#1E1E1E;border-radius:4px;height:6px;margin-top:4px;">
                    <div style="background:{PRIMARY};width:{pct}%;height:100%;border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nessun dato disponibile.")

    st.markdown("---")

    # Per sede
    sede_data = {}
    for v in attivi:
        s = v.get("luogo","N.D.")
        sede_data[s] = sede_data.get(s,{"n":0,"val":0})
        sede_data[s]["n"]   += to_int(v.get("qta",0))
        sede_data[s]["val"] += to_int(v.get("qta",0)) * to_float(v.get("prezzo",0))

    st.markdown("#### Per Sede")
    cols = st.columns(len(sede_data) if sede_data else 1)
    for i, (sede, d) in enumerate(sede_data.items()):
        cols[i].metric(f"📍 {sede}", f"{d['n']} pz", f"€ {d['val']:,.0f}")

def page_admin_settings(tenant):
    tid = tenant["id"]
    st.markdown(f"<h2 style='color:{ACCENT};'>⚙️ Impostazioni Cantina</h2>", unsafe_allow_html=True)

    with st.form("settings_tenant"):
        st.markdown("#### Dati Azienda")
        nn = st.text_input("Nome cantina", tenant.get("nome",""))
        nt = st.text_input("Telefono", tenant.get("telefono",""))
        nl = st.text_input("Logo URL", tenant.get("logo_url",""))
        st.markdown("#### Password")
        np = st.text_input("Nuova password", type="password", placeholder="lascia vuoto per non cambiare")

        if st.form_submit_button("💾 Salva impostazioni", type="primary"):
            # A-3: validazione URL logo
            def _url_sicuro(u):
                if not u: return True
                import urllib.parse
                p = urllib.parse.urlparse(u)
                return p.scheme in ("https", "http") and bool(p.netloc)
            if nl and not _url_sicuro(nl):
                st.error("❌ URL logo non valido. Usa un indirizzo https:// valido.")
            else:
                data = {"nome":nn, "telefono":nt, "logo_url":nl}
                if np: data["password"] = np
                db.update_tenant(tid, data)
                st.session_state.user = db.get_tenant(tid)
                if st.session_state.tenant_view: st.session_state.tenant_view = db.get_tenant(tid)
                st.success("✅ Impostazioni salvate!")
                st.rerun()

    st.markdown("---")

    # ── GESTIONE SEDI ─────────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{ACCENT};'>📍 Gestione Sedi</h3>", unsafe_allow_html=True)

    vini = db.get_vini(tid)
    mignon = db.get_mignon(tid)
    tutti = vini + mignon

    # Raccogli tutte le sedi
    sedi_set = sorted(set(
        v.get("luogo", "") for v in tutti
        if v.get("luogo") and v.get("luogo") != "None"
    ))

    if sedi_set:
        for sede in sedi_set:
            n_vini = len([v for v in tutti if v.get("luogo") == sede])
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            with sc1:
                st.markdown(f"""<div style="padding:8px 12px;background:#1a1a1a;border:1px solid #2a2a2a;
                    border-radius:8px;margin-bottom:4px;">
                    <span style="font-weight:600;color:#F0EDE8;">📍 {sede}</span>
                    <span style="color:{TEXT_MUTED};font-size:0.8em;margin-left:8px;">
                    ({n_vini} bottigli{"a" if n_vini==1 else "e"})</span>
                </div>""", unsafe_allow_html=True)
            with sc2:
                if st.button("✏️ Rinomina", key=f"ren_{sede}", use_container_width=True):
                    st.session_state.sede_rinomina = sede
            with sc3:
                if n_vini == 0:
                    if st.button("🗑️ Elimina", key=f"del_{sede}", use_container_width=True):
                        # Nessun vino — elimina (non serve azione DB, la sede esiste solo come valore)
                        st.success(f"Sede '{sede}' rimossa (era già vuota).")
                        st.rerun()
                else:
                    st.button("🗑️ Elimina", key=f"del_{sede}", use_container_width=True,
                              disabled=True, help=f"Non puoi eliminare: {n_vini} bottiglie assegnate")

        # Dialog rinomina
        if st.session_state.get("sede_rinomina"):
            old_name = st.session_state.sede_rinomina
            st.markdown(f"**Rinomina sede:** `{old_name}`")
            with st.form("form_rinomina_sede"):
                new_name = st.text_input("Nuovo nome sede", value=old_name)
                if st.form_submit_button("💾 Salva nuovo nome", type="primary"):
                    if new_name and new_name.strip() and new_name.strip() != old_name:
                        new_name = new_name.strip()
                        count = 0
                        for v in vini:
                            if v.get("luogo") == old_name:
                                db.update_vino(v["id"], tid, {"luogo": new_name})
                                count += 1
                        for v in mignon:
                            if v.get("luogo") == old_name:
                                db.update_mignon(v["id"], tid, {"luogo": new_name})
                                count += 1
                        st.session_state.sede_rinomina = None
                        st.success(f"✅ Sede rinominata: '{old_name}' → '{new_name}' ({count} bottiglie aggiornate)")
                        st.rerun()
                    else:
                        st.warning("Inserisci un nome diverso.")
            if st.button("Annulla"):
                st.session_state.sede_rinomina = None
                st.rerun()
    else:
        st.info("Nessuna sede configurata. Aggiungi la prima!")

    # Aggiungi nuova sede
    st.markdown("---")
    with st.form("form_nuova_sede"):
        st.markdown("**➕ Aggiungi nuova sede**")
        nuova_sede = st.text_input("Nome nuova sede", placeholder="es. Cantina, Frigo, Soggiorno...")
        if st.form_submit_button("Aggiungi sede"):
            if nuova_sede and nuova_sede.strip():
                nuova_sede = nuova_sede.strip()
                if nuova_sede in sedi_set:
                    st.warning(f"La sede '{nuova_sede}' esiste già.")
                else:
                    # Crea un vino "segnaposto" con qta=0 per registrare la sede
                    db.insert_vino(tid, {
                        "nome": f"[Sede: {nuova_sede}]",
                        "luogo": nuova_sede,
                        "qta": 0,
                        "tipo_cat": "Altro",
                        "prezzo": 0
                    })
                    st.success(f"✅ Sede '{nuova_sede}' creata! Puoi assegnarle i vini.")
                    st.rerun()
            else:
                st.warning("Inserisci un nome per la sede.")

# ─────────────────────────────────────────────────────────────────────────────
# ROUTER PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state.logged_in:
    show_login()
    st.stop()

user  = st.session_state.user
ruolo = st.session_state.ruolo

# Superadmin che sta visualizzando la cantina di un cliente
if ruolo == "superadmin" and st.session_state.tenant_view:
    tenant = st.session_state.tenant_view
    sidebar_admin(tenant)
    page = st.session_state.page
    if page == "dashboard":     page_admin_dashboard(tenant)
    elif page == "vini":        grid_vini(tenant, "vini")
    elif page == "mignon":      grid_vini(tenant, "mignon")
    elif page == "portale":     page_admin_portale(tenant)
    elif page == "statistiche": page_admin_statistiche(tenant)
    elif page == "impostazioni":page_admin_settings(tenant)

elif ruolo == "superadmin":
    sidebar_superadmin()
    page = st.session_state.page
    if page == "dashboard":    page_superadmin_dashboard()
    elif page == "clienti":    page_superadmin_clienti()
    elif page == "impostazioni": page_superadmin_settings()
    else: page_superadmin_dashboard()

else:
    # Admin normale — verifica trial
    _banner_trial(user)
    sidebar_admin(user)
    page = st.session_state.page
    if page == "dashboard":     page_admin_dashboard(user)
    elif page == "vini":        grid_vini(user, "vini")
    elif page == "mignon":      grid_vini(user, "mignon")
    elif page == "portale":     page_admin_portale(user)
    elif page == "statistiche": page_admin_statistiche(user)
    elif page == "impostazioni":page_admin_settings(user)
    else: page_admin_dashboard(user)
