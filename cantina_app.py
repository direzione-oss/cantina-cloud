# -*- coding: utf-8 -*-
"""
cantina_app.py — CantinaPro SaaS Platform
Piattaforma multi-tenant per la gestione di cantine vino.
Ruoli: superadmin | admin (cliente) | portale pubblico
"""
import streamlit as st
import os, random, base64, datetime, hashlib, re, smtplib
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

/* ── DIALOG / MODAL: tema scuro come l'app ── */
[data-testid="stDialog"] > div {{
    background-color: #1A1A1A !important;
    border: 1px solid #2A2A2A !important;
    border-radius: 16px !important;
}}
[data-testid="stDialog"] p,
[data-testid="stDialog"] span,
[data-testid="stDialog"] h1,
[data-testid="stDialog"] h2,
[data-testid="stDialog"] h3,
[data-testid="stDialog"] h4,
[data-testid="stDialog"] div,
[data-testid="stDialog"] label {{
    color: {TEXT_MAIN} !important;
}}
[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p,
[data-testid="stDialog"] [data-testid="stMarkdownContainer"] span {{
    color: {TEXT_MAIN} !important;
}}
/* Titolo dialog */
[data-testid="stDialog"] [data-testid="stDialogTitle"] p {{
    color: {ACCENT} !important; font-weight: 700 !important;
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

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "logged_in": False,
        "user": None,          # dict tenant
        "ruolo": None,
        "page": "dashboard",
        "tenant_view": None,   # superadmin accede come cliente
        "id_modifica": None,
        "sezione_cantina": "VINI",
        "luogo_sel": "TUTTE LE SEDI",
        "cat_sel": "TUTTI",
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
    except: return 0.0

def to_int(x):
    try: return int(str(x).split()[0])
    except: return 0

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
            st.markdown(f"""
            <div class="wine-row">
                <div class="wine-num">{idx}</div>
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
        f'<a href="https://cantina-cloud-gian.streamlit.app/" target="_blank" '
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
                if not email_l or not pwd_l:
                    st.error("Inserisci email e password.")
                else:
                    user = db.verify_login(email_l.strip().lower(), pwd_l)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user      = user
                        st.session_state.ruolo     = user.get("ruolo", "admin")
                        st.session_state.page      = "dashboard"
                        st.rerun()
                    else:
                        st.error("Credenziali non valide o account disattivato.")
            st.markdown("</div>", unsafe_allow_html=True)

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
                    slug = f"{slug_base}-{random.randint(1000,9999)}"
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
        fname = f"img_{random.randint(100000,999999)}.jpg"
        return db.upload_image(buf.getvalue(), fname, folder)
    except Exception as e:
        st.error(f"Errore upload immagine: {e}")
        return ""

def pp(t): return str(t).replace("€","E").encode("latin-1","replace").decode("latin-1")

# ─────────────────────────────────────────────────────────────────────────────
# PDF
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
    hdrs = ["N.", "Nome Vino", "Azienda", "Sede", "Annata", "Formato", "Qta", "Prezzo"]
    wws  = [10, 70, 50, 35, 18, 30, 13, 28]
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
            row = [
                str(i + 1),
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

        html = (
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
                db.update_vino(v["id"], {"qta": int(v["qta"])-1})
                copia = {k:val for k,val in v.items() if k not in ("id","created_at")}
                copia.update({"qta":0,"tipo_cat":"Provati","giudizio":giudizio,"cat_origine":v.get("tipo_cat","Rossi"),"tenant_id":tenant_id})
                db.insert_vino(tenant_id, copia)
            else:
                db.update_vino(v["id"], {"qta":0,"tipo_cat":"Provati","giudizio":giudizio,"cat_origine":v.get("tipo_cat","Rossi")})
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
                db.update_vino(v["id"], payload) if tipo=="vini" else db.update_mignon(v["id"], payload)
            else:
                db.insert_vino(tenant_id, payload) if tipo=="vini" else db.insert_mignon(tenant_id, payload)
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

    # Sedi
    sedi = sorted(set(v.get("luogo","") for v in vini if v.get("luogo")))
    if sedi:
        st.markdown("#### 🏠 Le Tue Sedi")
        cols = st.columns(len(sedi))
        for i, sede in enumerate(sedi):
            vini_sede = [v for v in vini if v.get("luogo") == sede and v.get("tipo_cat") != "Provati"]
            bt, val = calcola_totali(vini_sede)
            with cols[i]:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="val">{bt}</div>
                    <div class="lbl">📍 {sede}</div>
                    <div style="font-size:0.78em;color:{ACCENT};margin-top:4px;">€ {val:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ── QR CODE PER SEDE ─────────────────────────────────────────────
    slug = tenant.get("portale_slug", "")
    if sedi and slug:
        st.markdown(f"""<div style='font-size:1em;font-weight:600;color:{ACCENT};margin-bottom:12px;'>
            📱 Lista Ospiti — QR Code per Sede
            <div style='font-size:0.75em;font-weight:400;color:#888;margin-top:4px;'>
            Stampa il QR e consegnalo agli ospiti: scannerizzano e vedono la lista vini in tempo reale.
            </div></div>""", unsafe_allow_html=True)

        qr_cols = st.columns(min(len(sedi), 4))
        for i, sede in enumerate(sedi):
            import qrcode, urllib.parse
            url_lista = f"https://cantina-cloud-gian.streamlit.app?lista={slug}&luogo={urllib.parse.quote(sede)}"
            n_vini = len([v for v in vini if v.get("luogo")==sede and v.get("tipo_cat")!="Provati" and to_int(v.get("qta",0))>0])

            # ── Genera QR ──────────────────────────────────────────────
            qr = qrcode.QRCode(version=1, box_size=8, border=2,
                               error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(url_lista)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="#8B1A1A", back_color="white").convert("RGB")
            qr_w, qr_h = img_qr.size

            # ── Componi immagine stampabile con PIL ────────────────────
            card_w = qr_w + 60
            card_h = qr_h + 200
            card = Image.new("RGB", (card_w, card_h), color="#FFFFFF")
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(card)

            # Striscia bordeaux in alto
            draw.rectangle([0, 0, card_w, 60], fill="#8B1A1A")
            # Emoji vino (come testo)
            draw.text((card_w//2, 30), "🍷", fill="white", anchor="mm")

            # Nome cantina
            nome_cantina = tenant.get("nome", "Cantina")
            draw.rectangle([0, 60, card_w, 120], fill="#F9F4F4")
            draw.text((card_w//2, 90), nome_cantina[:30], fill="#8B1A1A", anchor="mm")

            # Sede
            draw.text((card_w//2, 120), f"📍  {sede}", fill="#555555", anchor="mm")

            # QR al centro
            card.paste(img_qr, (30, 145))

            # Testo istruzione sotto
            y_txt = 145 + qr_h + 12
            draw.rectangle([0, y_txt - 4, card_w, card_h], fill="#F9F4F4")
            draw.text((card_w//2, y_txt + 10), "Scansiona per vedere la lista vini", fill="#8B1A1A", anchor="mm")
            draw.text((card_w//2, y_txt + 28), f"{n_vini} etichette disponibili", fill="#999999", anchor="mm")

            # Bordo arrotondato (effetto)
            draw.rectangle([0, 0, card_w-1, card_h-1], outline="#CCCCCC", width=2)

            # ── Salva immagine card ────────────────────────────────────
            buf_card = BytesIO()
            card.save(buf_card, format="PNG", dpi=(300, 300))
            buf_card.seek(0)
            card_b64 = base64.b64encode(buf_card.read()).decode()

            # Anteprima nel dashboard (piccola)
            buf_preview = BytesIO()
            card.thumbnail((200, 300))
            card.save(buf_preview, format="PNG")
            buf_preview.seek(0)
            prev_b64 = base64.b64encode(buf_preview.read()).decode()

            with qr_cols[i % 4]:
                st.markdown(f'<img src="data:image/png;base64,{prev_b64}" style="width:100%;border-radius:8px;margin-bottom:8px;border:1px solid #2A2A2A;"/>', unsafe_allow_html=True)
                buf_card.seek(0)
                st.download_button(
                    label=f"🖨️ Scarica card {sede}",
                    data=buf_card,
                    file_name=f"lista_qr_{sede.lower().replace(' ','_')}.png",
                    mime="image/png",
                    use_container_width=True,
                    key=f"qr_dl_{i}"
                )
                # Link condivisibile
                nome_cantina = tenant.get("nome", sede)
                wa_msg = urllib.parse.quote(f"Lista vini {nome_cantina} — {sede}: {url_lista}")
                st.markdown(
                    f'<a href="https://wa.me/?text={wa_msg}" target="_blank" '
                    f'style="display:block;text-align:center;font-size:0.82em;'
                    f'color:#25D366;margin-top:6px;margin-bottom:4px;text-decoration:none;'
                    f'font-weight:600;">📤 Invia via WhatsApp</a>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div style="background:#1a1a1a;border:1px solid #333;border-radius:6px;'
                    f'padding:8px 10px;margin-top:2px;font-size:0.68em;color:#aaa;'
                    f'word-break:break-all;text-align:center;">'
                    f'<a href="{url_lista}" target="_blank" style="color:#C9A84C;text-decoration:none;">'
                    f'🔗 {url_lista}</a></div>',
                    unsafe_allow_html=True
                )


    st.markdown("---")

    # ── PDF ────────────────────────────────────────────────
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("📄 Lista PDF completa", use_container_width=True, type="secondary"):
            giacenza = [v for v in vini if to_int(v.get("qta",0))>0 and v.get("tipo_cat")!="Provati"]
            pdf = genera_pdf_lista(giacenza, f"Giacenza Cantina — {tenant['nome']}")
            st.download_button("📥 Scarica", data=pdf, file_name="cantina.pdf", mime="application/pdf")
    with col2:
        if sedi:
            sede_sel = st.selectbox("📍 Sede per divisa", sedi, key="sede_divisa_sel", label_visibility="collapsed")
            if st.button(f"📝 Divisa {sede_sel}", use_container_width=True, type="secondary"):
                vini_sede = [v for v in vini if v.get("luogo")==sede_sel
                             and v.get("tipo_cat")!="Provati"
                             and to_int(v.get("qta",0))>0]
                pdf = genera_pdf_lista(vini_sede, f"Lista Vini — {sede_sel}  ({tenant['nome']})")
                st.download_button("📥 Scarica Divisa", data=pdf,
                                   file_name=f"divisa_{sede_sel.lower().replace(' ','_')}.pdf",
                                   mime="application/pdf")

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

    cols = st.columns(3)
    for j, v in enumerate(vini_f):
        with cols[j % 3]:
            q = to_int(v.get("qta",0))
            cat = v.get("tipo_cat","")
            loc = v.get("luogo","")
            coll= v.get("collocazione","")

            st.markdown(f"""
            <div class="wine-card">
                <div class="wine-card-header">
                    {v['nome']}
                    <span class="wine-badge">{cat}</span>
                </div>
            """, unsafe_allow_html=True)

            if v.get("foto_url"): st.image(v["foto_url"], use_container_width=True)

            st.markdown(f"""
            <div style="padding:10px 12px;">
                <div style="font-size:1.2em;font-weight:700;color:{ACCENT};">€ {to_float(v.get('prezzo',0)):,.2f}</div>
                <div style="color:{TEXT_MUTED};font-size:0.8em;">{v.get('azienda','')} · {v.get('annata','')}</div>
                <div style="margin-top:6px;font-size:0.82em;">
                    🍾 {v.get('formato','0.75 L')} &nbsp;|&nbsp;
                    📦 Qta: <b style="color:{ACCENT if q>3 else '#f59e0b' if q>0 else '#ef4444'};">{q}</b>
                </div>
                {'<div style="font-size:0.78em;color:'+TEXT_MUTED+';">📍 '+loc+(' · '+coll if coll else '')+'</div>' if loc else ''}
                {'<div style="font-size:0.78em;color:#d97706;margin-top:4px;font-style:italic;">🍷 '+v["giudizio"][:50]+'…</div>' if v.get("giudizio") else ''}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Azioni
            a1,a2,a3,a4,a5 = st.columns(5)
            if a1.button("−", key=f"m_{tipo}_{v['id']}", help="Decrementa"):
                upd = db.update_vino if tipo=="vini" else db.update_mignon
                upd(v["id"], {"qta": max(0, q-1)}); st.rerun()
            if a2.button("+", key=f"p_{tipo}_{v['id']}", help="Incrementa"):
                upd = db.update_vino if tipo=="vini" else db.update_mignon
                upd(v["id"], {"qta": q+1}); st.rerun()
            if a3.button("✏️", key=f"e_{tipo}_{v['id']}", help="Modifica"):
                st.session_state.id_modifica = v["id"]; st.rerun()
            if a4.button("📖", key=f"s_{tipo}_{v['id']}", help="Scheda"):
                dialog_scheda(v)
            if a5.button("🍷", key=f"sta_{tipo}_{v['id']}", help="Stappa") and tipo=="vini":
                dialog_stappa(v, tid, tipo)

def page_admin_portale(tenant):
    tid = tenant["id"]
    st.markdown(f"<h2 style='color:{ACCENT};'>🌐 Portale di Vendita</h2>", unsafe_allow_html=True)

    attivo = tenant.get("portale_attivo", False)
    slug   = tenant.get("portale_slug","")

    if attivo and slug:
        url = f"?portale={slug}"
        st.success(f"✅ Portale attivo! Link pubblico: `{url}`")
        st.markdown(f"[🔗 Apri il portale]({url})", unsafe_allow_html=True)
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
            data = {"nome":nn, "telefono":nt, "logo_url":nl}
            if np: data["password"] = np
            db.update_tenant(tid, data)
            st.session_state.user = db.get_tenant(tid)
            if st.session_state.tenant_view: st.session_state.tenant_view = db.get_tenant(tid)
            st.success("✅ Impostazioni salvate!")
            st.rerun()

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
