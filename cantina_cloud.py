import streamlit as st
import os
import random
import base64
import socket
import qrcode
import urllib.parse
import datetime
from io import BytesIO
from fpdf import FPDF
from PIL import Image

# --- SUPABASE ---
from supabase_client import (
    init_supabase, get_all, insert_record, update_record,
    upload_image, get_public_url, BUCKET
)

# --- OCR (opzionale) ---
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ==============================================================================
# PROTOCOLLO GIAN CARLO — VERSIONE CLOUD (SUPABASE)
# ==============================================================================

SFONDO_FILE = "sfondo.jpg"

st.set_page_config(page_title="Le Cantine di Gian Carlo", layout="wide")

bg_base64 = ""
if os.path.exists(SFONDO_FILE):
    with open(SFONDO_FILE, "rb") as f: bg_base64 = base64.b64encode(f.read()).decode()

# --- CSS STILE ---
st.markdown(f"""
<style>
    .stApp {{ background-image: url('data:image/jpg;base64,{bg_base64}'); background-size: cover; background-attachment: fixed; }}
    
    div.stButton > button {{
        background-color: #000000 !important; color: #ffffff !important;
        border: 1px solid #555 !important; border-radius: 5px !important; font-weight: bold !important;
    }}
    div.stButton > button:hover {{
        border-color: #f0e68c !important; color: #f0e68c !important;
    }}

    .card {{ background: rgba(0, 0, 0, 0.85) !important; border-radius: 15px; border: 1px solid #f0e68c44; color: white; margin-bottom: 25px; overflow: hidden; box-shadow: 5px 5px 15px rgba(0,0,0,0.9); }}
    .card-header {{ background: #000000; padding: 12px; text-align: center; border-bottom: 1px solid #f0e68c; font-weight: bold; font-size: 1.3em; color: #f0e68c; text-transform: uppercase; }}
    .card-body {{ padding: 15px; text-align: center; }}
    .data-box {{ background-color: rgba(30, 30, 30, 0.9); padding: 10px; border-radius: 8px; margin-top: 10px; color: #ffffff !important; text-shadow: 1px 1px 2px #000000; border: 1px solid #555; font-size: 1.1em; }}
    .giudizio-box {{ background: rgba(240, 230, 140, 0.1); border-left: 4px solid #f0e68c; padding: 8px; margin-top: 10px; font-style: italic; color: #fff; text-align: left; }}
    
    h1, h2, h3, h4 {{ background-color: rgba(0,0,0,0.7); padding: 10px; border-radius: 10px; color: white !important; text-shadow: 2px 2px 4px #000000; }}
</style>
""", unsafe_allow_html=True)

# --- LISTE BASE ---
LISTA_CATEGORIE_BASE = ["⚠️ DA CATALOGARE", "Rossi", "Bianchi", "Spumanti", "Champagne", "Frizzanti", "Liquori", "Birre", "Provati", "Altro"]
TIPI_VINO = ["Fermo", "Mosso", "Frizzante", "Metodo Classico", "Charmat", "Passito"]
SCALA_ZUCCHERI = ["N.S.", "Pas Dosé", "Extra Brut", "Brut", "Extra Dry", "Dry", "Demi Sec", "Dolce"]
LISTA_LUOGHI_BASE = ["Casa Principale", "Casa al Mare", "Casa in Montagna", "Ufficio"]

# ── LETTURA DATI DA SUPABASE ──────────────────────────────────────────────────

def get_data(tipo: str) -> list[dict]:
    """Legge i dati dalla tabella corrispondente."""
    table = "vini" if tipo == "CANTINA" else "mignon"
    return get_all(table)

def save_field(tipo: str, record_id: int, field: str, value):
    """Aggiorna un singolo campo di un record."""
    table = "vini" if tipo == "CANTINA" else "mignon"
    update_record(table, record_id, {field: value})

def save_record(tipo: str, record_id: int, data: dict):
    """Aggiorna più campi di un record."""
    table = "vini" if tipo == "CANTINA" else "mignon"
    update_record(table, record_id, data)

def add_record(tipo: str, data: dict) -> dict:
    """Inserisce un nuovo record."""
    table = "vini" if tipo == "CANTINA" else "mignon"
    return insert_record(table, data)

# ── COMPRESSIONE IMMAGINI + UPLOAD ────────────────────────────────────────────

def salva_immagine_cloud(uploaded_file, folder: str) -> str:
    """Comprime e carica un'immagine su Supabase Storage. Ritorna l'URL."""
    try:
        img = Image.open(uploaded_file)
        # Fix orientamento EXIF
        try:
            from PIL import ExifTags
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation': break
            exif = img._getexif()
            if exif is not None:
                if exif[orientation] == 3: img = img.rotate(180, expand=True)
                elif exif[orientation] == 6: img = img.rotate(270, expand=True)
                elif exif[orientation] == 8: img = img.rotate(90, expand=True)
        except: pass
        img.thumbnail((800, 800))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=70, optimize=True)
        filename = f"img_{random.randint(10000, 99999)}.jpg"
        return upload_image(buf.getvalue(), filename, folder)
    except Exception as e:
        st.error(f"Errore salvataggio immagine: {e}")
        return ""

def ruota_immagine_cloud(foto_url: str, gradi: int, folder: str) -> str:
    """Scarica immagine da URL, la ruota e la ricarica."""
    try:
        import urllib.request, tempfile
        tmp = os.path.join(tempfile.gettempdir(), "rotate_tmp.jpg")
        urllib.request.urlretrieve(foto_url, tmp)
        img = Image.open(tmp)
        img = img.rotate(gradi, expand=True)
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
        # Estrai filename dall'URL
        filename = foto_url.split("/")[-1].split("?")[0]
        return upload_image(buf.getvalue(), filename, folder)
    except Exception as e:
        st.error(f"Errore rotazione: {e}")
        return foto_url

# ── CERVELLO FORMATI ──────────────────────────────────────────────────────────

def calcola_nome_formato(input_utente):
    mappa = {0.1875:"Piccolo", 0.375:"Demi", 0.75:"Standard", 1.5:"Magnum", 3.0:"Jéroboam", 4.5:"Réhoboam", 6.0:"Mathusalem", 9.0:"Salmanazar", 12.0:"Balthazar", 15.0:"Nabuchodonosor"}
    try:
        txt = str(input_utente).lower().replace("litri", "").replace("l", "").replace(",", ".").strip()
        valore = float(txt)
        val_vis = int(valore) if valore.is_integer() else valore
        nome = mappa.get(valore, "")
        return f"{val_vis} L ({nome})" if nome else f"{val_vis} L"
    except: return input_utente if input_utente else "0.75 L (Standard)"

# ── UTILS ─────────────────────────────────────────────────────────────────────

def calcola_totali(data):
    def to_float(x):
        try: return float(str(x).replace(",", "."))
        except: return 0.0
    def to_int(x):
        try: return int(str(x).split()[0])
        except: return 0
    bottiglie = sum(to_int(v.get('qta', 0)) for v in data if v.get('tipo_cat') != "Provati")
    valore = sum(to_int(v.get('qta', 0)) * to_float(v.get('prezzo', 0.0)) for v in data if v.get('tipo_cat') != "Provati")
    return bottiglie, valore

def trova_ip():
    try: s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

# ── PDF ───────────────────────────────────────────────────────────────────────

def pulisci_per_pdf(testo): return str(testo).replace("€", "E").encode('latin-1', 'replace').decode('latin-1')

def genera_pdf_completo(lista, titolo):
    pdf = FPDF(orientation='L', unit='mm', format='A4'); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, pulisci_per_pdf(titolo), ln=True, align='C'); pdf.ln(5)
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 230, 140)
    h, w = (["ID", "Nome", "Cantina", "Pos./Scaf.", "Qta", "Prezzo"], [15, 75, 50, 35, 15, 30])
    for i, txt in enumerate(h): pdf.cell(w[i], 10, txt, 1, 0, 'C', True)
    pdf.ln(); pdf.set_font("Arial", '', 10)
    for i, v in enumerate(lista):
        loc_str = pulisci_per_pdf(v.get('luogo',''))
        col_str = pulisci_per_pdf(v.get('collocazione',''))
        full_loc = f"{loc_str} ({col_str})" if col_str else loc_str
        row = [f"#{v.get('id', i+1)}", pulisci_per_pdf(v['nome']), pulisci_per_pdf(v.get('azienda','')), full_loc, str(v['qta']), f"E {v.get('prezzo',0)}"]
        for idx, text in enumerate(row): pdf.cell(w[idx], 8, text, 1)
        pdf.ln()
    return bytes(pdf.output(dest='S'))

def _scarica_immagine_temp(url):
    """Scarica un'immagine da URL in un file temporaneo per fpdf."""
    try:
        import urllib.request, tempfile
        ext = ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        urllib.request.urlretrieve(url, tmp.name)
        return tmp.name
    except:
        return None

def genera_etichette_collo_range(data_completa, id_start, id_end):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.set_auto_page_break(auto=False, margin=0)
    
    vini_da_stampare = []
    for v in data_completa:
        rid = v['id']
        if id_start <= rid <= id_end: vini_da_stampare.append(v)
            
    if not vini_da_stampare: return None

    margin_x = 10; start_y = 15; w_card = 63; h_card = 84
    
    for i, v in enumerate(vini_da_stampare):
        index_in_page = i % 9
        if index_in_page == 0: pdf.add_page()
        
        col = index_in_page % 3; row = index_in_page // 3
        x = margin_x + (col * w_card); y = start_y + (row * h_card)
        
        pdf.set_draw_color(150, 150, 150); pdf.rect(x, y, w_card, h_card)
        pdf.set_draw_color(0, 0, 0); center_x = x + (w_card / 2); pdf.circle(center_x, y + 6, 2) 
        
        pdf.set_xy(x, y + 10)
        pdf.set_font("Arial", 'B', 24)
        pdf.cell(w_card, 10, f"#{v['id']}", ln=True, align='C')
        
        img_y_start = y + 22
        if v.get('foto_url'):
            tmp_path = _scarica_immagine_temp(v['foto_url'])
            if tmp_path:
                try: pdf.image(tmp_path, x + 16, img_y_start, w=30, h=35)
                except: pass
                try: os.unlink(tmp_path)
                except: pass
        else:
            pdf.set_xy(x, img_y_start + 10); pdf.set_font("Arial", 'I', 8); pdf.cell(w_card, 5, "(No Foto)", align='C')

        text_y = img_y_start + 36
        pdf.set_xy(x, text_y)
        
        pdf.set_font("Arial", 'B', 10)
        nome = pulisci_per_pdf(v['nome'])
        pdf.set_x(x); pdf.multi_cell(w_card, 4.5, nome, align='C')
        
        pdf.set_x(x); pdf.set_font("Arial", '', 9)
        azienda = pulisci_per_pdf(v.get('azienda',''))
        if azienda: pdf.multi_cell(w_card, 4, azienda, align='C')
        
        pdf.set_x(x); pdf.set_font("Arial", 'B', 9)
        annata = str(v.get('annata', ''))
        if annata: pdf.cell(w_card, 5, f"Annata: {annata}", ln=True, align='C')
        else: pdf.ln(2)
        
        pdf.set_x(x); pdf.set_font("Arial", 'I', 7)
        loc = pulisci_per_pdf(v.get('collocazione',''))
        macro = pulisci_per_pdf(v.get('luogo',''))
        if loc: pos_txt = f"POS: {loc}"
        elif macro: pos_txt = f"SEDE: {macro}"
        else: pos_txt = ""
        if pos_txt: pdf.cell(w_card, 4, pos_txt[:35], ln=True, align='C')

    return bytes(pdf.output(dest='S'))

def genera_catalogo_visuale(full_data):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.set_auto_page_break(auto=False, margin=0)
    categorie_presenti = sorted(list(set(v.get('tipo_cat', 'Altro').strip() for v in full_data if int(str(v.get('qta',0)).split()[0]) > 0)))
    buckets = {cat: [] for cat in categorie_presenti}
    count = 0
    for v in full_data:
        try: qta = int(str(v.get('qta', 0)).split()[0])
        except: qta = 0
        if qta > 0:
            c = str(v.get('tipo_cat', 'Altro')).strip()
            if c in buckets: buckets[c].append(v); count += 1

    pdf.add_page(); pdf.set_font("Arial", 'B', 24); pdf.cell(0, 20, "", ln=True); pdf.cell(0, 20, "CATALOGO CANTINA", ln=True, align='C')
    pdf.cell(0, 20, "GIAN CARLO", ln=True, align='C'); pdf.set_font("Arial", 'I', 12); pdf.cell(0, 10, f"Aggiornato: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", '', 12); pdf.cell(0, 10, f"Totale Vini: {count}", ln=True, align='C')

    priorita = [c for c in LISTA_CATEGORIE_BASE if c in categorie_presenti]
    altri = [c for c in categorie_presenti if c not in priorita]
    ordine_stampa = priorita + altri

    for cat in ordine_stampa:
        vini = buckets.get(cat, [])
        if not vini: continue
        pdf.add_page(); pdf.set_fill_color(0, 0, 0); pdf.set_text_color(240, 230, 140)
        pdf.set_font("Arial", 'B', 16); pdf.cell(0, 12, f"  {cat.upper()}", 0, 1, 'L', True)
        pdf.set_text_color(0, 0, 0); pdf.ln(5)
        
        mx=10; sy=35; wc=63; hc=84
        for i, v in enumerate(vini):
            pg_idx = i % 9
            if i > 0 and pg_idx == 0:
                pdf.add_page(); pdf.set_font("Arial", 'I', 10); pdf.cell(0, 10, f"{cat} (continua...)", ln=True, align='R'); sy=20
            
            c_col = pg_idx % 3; r = pg_idx // 3
            x = mx + (c_col * wc); y = sy + (r * hc)
            pdf.rect(x, y, wc-2, hc-2)
            
            if v.get('foto_url'):
                tmp_path = _scarica_immagine_temp(v['foto_url'])
                if tmp_path:
                    try: pdf.image(tmp_path, x+11, y+2, w=40, h=45)
                    except: pass
                    try: os.unlink(tmp_path)
                    except: pass
            
            pdf.set_xy(x, y+50); pdf.set_font("Arial", 'B', 9)
            pdf.cell(wc-2, 5, pulisci_per_pdf(v['nome'])[:28], ln=True, align='C')
            
            pdf.set_xy(x, pdf.get_y()); pdf.set_font("Arial", '', 8)
            det = f"{pulisci_per_pdf(v.get('azienda',''))}"
            if v.get('provenienza'): det += f" - {pulisci_per_pdf(v.get('provenienza',''))[:10]}"
            elif v.get('collocazione'): det += f" [{pulisci_per_pdf(v.get('collocazione',''))[:10]}]"
            elif v.get('luogo'): det += f" [{pulisci_per_pdf(v.get('luogo',''))[:10]}]"
            pdf.cell(wc-2, 4, det[:35], ln=True, align='C')
            
            if v.get('vitigno'):
                pdf.set_xy(x, pdf.get_y()); pdf.set_font("Arial", 'I', 7)
                pdf.cell(wc-2, 4, pulisci_per_pdf(v.get('vitigno',''))[:30], ln=True, align='C')
            
            pdf.set_xy(x, pdf.get_y())
            pdf.set_font("Arial", '', 7)
            t_tipo = pulisci_per_pdf(v.get('tipo_vino', '')); t_zuc = pulisci_per_pdf(v.get('zucchero', '')); t_grad = pulisci_per_pdf(v.get('gradi', ''))
            parts = []
            if t_tipo and t_tipo != "N.D.": parts.append(t_tipo)
            if t_zuc and t_zuc != "N.S.": parts.append(t_zuc)
            if t_grad: parts.append(f"{t_grad}%")
            full_specs = " - ".join(parts)
            if full_specs: pdf.cell(wc-2, 4, full_specs[:38], ln=True, align='C')
            else: pdf.ln(4)

            pdf.set_xy(x, pdf.get_y()); pdf.set_font("Arial", 'B', 8)
            fmt_clean = v.get('formato','0.75').split('(')[0]
            pdf.cell(wc-2, 4, f"{fmt_clean}L - E {v.get('prezzo',0)}", ln=True, align='C')
            
            pdf.set_fill_color(230, 230, 230); pdf.set_xy(x+1, y+hc-8); pdf.set_font("Arial", '', 8)
            pdf.cell(wc-4, 5, f"Qta: {v['qta']}", 1, 0, 'C', True)
            
    return bytes(pdf.output(dest='S'))

# ── DIALOGHI ──────────────────────────────────────────────────────────────────

@st.dialog("Liste Rapide")
def mostra_liste_rapide(lista_vini, titolo_lista):
    st.subheader(titolo_lista)
    if not lista_vini: st.write("Nessun vino trovato.")
    else:
        for v in lista_vini: st.write(f"**#{v['id']} - {v['nome']}** ({v.get('azienda','')}) - Qta: {v['qta']}")
        pdf_data = genera_pdf_completo(lista_vini, titolo_lista)
        st.download_button("📥 SCARICA PDF", data=pdf_data, file_name="lista.pdf")

@st.dialog("Scheda Tecnica")
def mostra_scheda(v, tipo):
    folder = "vini" if tipo == "CANTINA" else "mignon"
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if v.get('foto_url'):
            st.image(v['foto_url'], use_container_width=True)
            cr1, cr2 = st.columns(2)
            if cr1.button("🔄 SX", key=f"rsx_{v['id']}"):
                new_url = ruota_immagine_cloud(v['foto_url'], 90, folder)
                save_field(tipo, v['id'], 'foto_url', new_url)
                st.rerun()
            if cr2.button("🔄 DX", key=f"rdx_{v['id']}"):
                new_url = ruota_immagine_cloud(v['foto_url'], -90, folder)
                save_field(tipo, v['id'], 'foto_url', new_url)
                st.rerun()
    with c2:
        st.subheader(f"{v['nome']}")
        st.write(f"**Cantina:** {v.get('azienda', 'N.D.')}")
        if v.get('provenienza'): st.write(f"🎁 **Fonte:** {v.get('provenienza')}")
        st.write(f"**Formato:** {v.get('formato', '0.75 L')}")
        st.write(f"**Annata:** {v.get('annata', 'N.D.')} | **Gradi:** {v.get('gradi', 'N.D.')}%")
        st.write(f"**Vitigno:** {v.get('vitigno', 'N.D.')}")
        st.write(f"**Tipo:** {v.get('tipo_vino', 'N.D.')} | **Zucchero:** {v.get('zucchero', 'N.S.')}")
        st.write(f"**Prezzo:** € {float(str(v.get('prezzo', 0)).replace(',','.')):,.2f}")
        loc_completa = f"📍 {v.get('luogo', 'Casa Principale')}"
        if v.get('collocazione'): loc_completa += f" — 📦 {v.get('collocazione')}"
        st.info(loc_completa)
    st.divider()
    ca, cb = st.columns(2)
    with ca: st.markdown("📝 **Note:**"); st.info(v.get('note', 'Nessuna'))
    with cb: st.markdown("🍷 **Giudizio:**"); st.warning(v.get('giudizio', 'Nessuno'))

@st.dialog("Stappa e Giudica")
def dialog_stappa(v, tipo):
    st.subheader(f"🍷 Assaggio: {v['nome']}")
    nuovo_giudizio = st.text_area("Com'era questo vino?")
    if st.button("Conferma Stappo"):
        qta = int(v.get('qta', 1))
        if qta > 1:
            # Decrementa quantità del record originale
            save_field(tipo, v['id'], 'qta', qta - 1)
            # Crea copia in "Provati"
            nuovo = {k: v2 for k, v2 in v.items() if k != 'id'}
            nuovo['qta'] = 0
            nuovo['tipo_cat'] = "Provati"
            nuovo['giudizio'] = nuovo_giudizio
            nuovo['cat_origine'] = v.get('tipo_cat', 'Rossi')
            add_record(tipo, nuovo)
        else:
            save_record(tipo, v['id'], {
                'qta': 0, 'tipo_cat': "Provati",
                'giudizio': nuovo_giudizio,
                'cat_origine': v.get('tipo_cat', 'Rossi')
            })
        st.rerun()

# ── OCR ───────────────────────────────────────────────────────────────────────

def estrai_dati_da_foto(image_bytes):
    if not OCR_AVAILABLE: return None, None, None, None
    try:
        import re
        reader = easyocr.Reader(['it', 'en'], gpu=False)
        res = reader.readtext(image_bytes, detail=0)
        txt = " ".join(res)
        anno = re.search(r'\b(19|20)\d{2}\b', txt); anno = anno.group(0) if anno else ""
        gradi = re.search(r'(\d{1,2}[.,]\d{0,1})\s?%', txt); gradi = gradi.group(1) if gradi else ""
        nome = res[0] if len(res)>0 else ""; cantina = res[1] if len(res)>1 else ""
        return nome, cantina, anno, gradi
    except: return "", "", "", ""

# ══════════════════════════════════════════════════════════════════════════════
# INTERFACCIA
# ══════════════════════════════════════════════════════════════════════════════

if 'sezione' not in st.session_state: st.session_state.sezione = "HOME"
if 'id_modifica' not in st.session_state: st.session_state.id_modifica = None
if 'cantina_selezionata' not in st.session_state: st.session_state.cantina_selezionata = "TUTTE LE SEDI"

for key in ['new_nome', 'new_az', 'new_ann', 'new_gr']:
    if key not in st.session_state: st.session_state[key] = ""

# Carica dati da Supabase
data_vini = get_data("CANTINA")
data_mignon = get_data("MIGNON")

# -- CALCOLO DINAMICO LISTE --
luoghi_presenti = sorted(list(set(v.get('luogo', '').strip() for v in data_vini if v.get('luogo'))))
LISTA_LUOGHI_COMPLETA = sorted(list(set(LISTA_LUOGHI_BASE + luoghi_presenti)))

categorie_presenti = sorted(list(set(v.get('tipo_cat', '').strip() for v in data_vini if v.get('tipo_cat'))))
LISTA_CATEGORIE_COMPLETA = []
for c in LISTA_CATEGORIE_BASE: LISTA_CATEGORIE_COMPLETA.append(c)
for c in categorie_presenti:
    if c not in LISTA_CATEGORIE_COMPLETA and c: LISTA_CATEGORIE_COMPLETA.append(c)

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.sezione == "HOME":
    st.markdown("<br><br><h1 style='text-align:center; color:white; font-size:55px; text-shadow: 4px 4px 10px black;'>LE CANTINE DI GIAN CARLO</h1>", unsafe_allow_html=True)
    st.success("☁️ Connesso a Supabase Cloud!")

    tv, vv = calcola_totali(data_vini); tm, vm = calcola_totali(data_mignon)
    st.markdown(f'<div style="display:flex; justify-content:center; gap:20px; margin-bottom:30px;"><div style="background: rgba(240, 230, 140, 0.2); border: 1px solid #f0e68c; padding: 15px; border-radius: 10px; text-align: center; color: white;"><b>TOTALE VINI (Tutte le Sedi)</b><br>{tv} pz - € {vv:,.2f}</div><div style="background: rgba(240, 230, 140, 0.2); border: 1px solid #f0e68c; padding: 15px; border-radius: 10px; text-align: center; color: white;"><b>TOTALE MIGNON</b><br>{tm} pz - € {vm:,.2f}</div></div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("<h3 style='text-align:center; color:#f0e68c;'>📍 SCEGLI IN QUALE CANTINA ENTRARE</h3>", unsafe_allow_html=True)
    col_sel1, col_sel2, col_sel3 = st.columns([1, 2, 1])
    with col_sel2:
        scelta = st.selectbox("", ["TUTTE LE SEDI"] + LISTA_LUOGHI_COMPLETA, index=0)
        if st.button("ENTRA NELLA CANTINA SELEZIONATA", use_container_width=True, type="primary"):
            st.session_state.cantina_selezionata = scelta
            st.session_state.sezione = "CANTINA"; st.rerun()
    c2 = st.columns(3)[1]
    if c2.button("🥃 ENTRA IN MIGNON", use_container_width=True): st.session_state.sezione = "MIGNON"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SEZIONE CANTINA / MIGNON
# ══════════════════════════════════════════════════════════════════════════════

else:
    tipo = st.session_state.sezione
    data = data_vini if tipo == "CANTINA" else data_mignon
    folder = "vini" if tipo == "CANTINA" else "mignon"
    luogo_corrente = st.session_state.get('cantina_selezionata', 'TUTTE LE SEDI')
    
    with st.sidebar:
        if st.button("🔄 AGGIORNA PAGINA"): st.rerun()
        st.divider()
        if st.button("🏠 TORNA HOME"): st.session_state.sezione = "HOME"; st.session_state.id_modifica = None; st.rerun()
        st.divider(); st.markdown(f"📍 **Sei in:**\n## {luogo_corrente}"); st.divider()
        
        ip = trova_ip(); qr = qrcode.make(f"http://{ip}:8502"); buf = BytesIO(); qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption=f"IP: {ip}")
        st.divider()

        vini_filtrati = data
        if luogo_corrente != "TUTTE LE SEDI" and tipo == "CANTINA":
            vini_filtrati = [v for v in data if v.get('luogo') == luogo_corrente]

        if st.button("📜 LISTA RAPIDA"): mostra_liste_rapide([v for v in vini_filtrati if int(v.get('qta',0))>0], f"GIACENZA: {luogo_corrente}")
        if st.button("🖨️ CATALOGO FOTO"):
             if not vini_filtrati: st.error("Nessun vino qui!")
             else:
                 with st.spinner("Creo PDF..."):
                     pdf_vis = genera_catalogo_visuale(vini_filtrati)
                     st.download_button("📥 SCARICA PDF", data=pdf_vis, file_name=f"catalogo.pdf", mime="application/pdf", type="primary")
        
        # Etichette
        with st.expander("🏷️ STAMPA ETICHETTE"):
            tot_vini = len(data)
            if tot_vini > 0:
                ids = [v['id'] for v in data]
                min_id, max_id = min(ids), max(ids)
                col_min, col_max = st.columns(2)
                id_start = col_min.number_input("Da ID", min_value=min_id, max_value=max_id, value=min_id)
                id_end = col_max.number_input("A ID", min_value=min_id, max_value=max_id, value=max_id)
                if st.button("🖨️ GENERA PDF"):
                    pdf = genera_etichette_collo_range(data, id_start, id_end)
                    if pdf: st.download_button("📥 SCARICA", data=pdf, file_name=f"etichette_{id_start}_{id_end}.pdf")
            else:
                st.warning("Nessuna bottiglia presente.")

        st.divider()
        
        # Filtri
        if tipo == "CANTINA":
            formati = sorted(list(set(v.get('formato', '0.75 L (Standard)') for v in vini_filtrati)))
            formati.insert(0, "TUTTI I FORMATI")
            filtro_fmt = st.selectbox("🍾 FORMATO", formati)
        else: filtro_fmt = "TUTTI I FORMATI"
        filtro_txt = st.text_input("🔍 CERCA", "").lower()
        st.divider()

        # ── MODIFICA ──────────────────────────────────────────────────────
        if st.session_state.id_modifica is not None:
            v_mod = next((v for v in data if v['id'] == st.session_state.id_modifica), None)
            if v_mod is None:
                st.session_state.id_modifica = None
                st.rerun()
            else:
                v = v_mod
                st.subheader(f"✏️ Modifica ID #{v['id']}")
                if v.get('foto_url'):
                    st.image(v['foto_url'], use_container_width=True)
                    r1, r2 = st.columns(2)
                    if r1.button("🔄 SX"):
                        new_url = ruota_immagine_cloud(v['foto_url'], 90, folder)
                        save_field(tipo, v['id'], 'foto_url', new_url)
                        st.rerun()
                    if r2.button("🔄 DX"):
                        new_url = ruota_immagine_cloud(v['foto_url'], -90, folder)
                        save_field(tipo, v['id'], 'foto_url', new_url)
                        st.rerun()
                
                with st.form("edit_form"):
                    n_nome = st.text_input("Nome", v['nome'])
                    n_az = st.text_input("Cantina", v.get('azienda',''))
                    if tipo == "CANTINA":
                        curr_cat = v.get('tipo_cat', 'Rossi')
                        cats_combo = sorted(list(set(LISTA_CATEGORIE_COMPLETA + [curr_cat])))
                        idx_cat = cats_combo.index(curr_cat) if curr_cat in cats_combo else 0
                        sel_cat = st.selectbox("Categoria esistente...", cats_combo, index=idx_cat)
                        n_new_cat = st.text_input("...oppure scrivi una NUOVA Categoria", "")

                        curr_l = v.get('luogo', 'Casa Principale')
                        locs_combo = sorted(list(set(LISTA_LUOGHI_COMPLETA + [curr_l])))
                        idx_l = locs_combo.index(curr_l) if curr_l in locs_combo else 0
                        sel_luogo = st.selectbox("Sede esistente...", locs_combo, index=idx_l)
                        n_new_luogo = st.text_input("...oppure scrivi una NUOVA Sede", "")
                        n_collocazione = st.text_input("Posizione Specifica (es. Scaffale A)", v.get('collocazione', ''))
                    else: 
                        sel_cat="Mignon"; n_new_cat=""; sel_luogo="Casa Principale"; n_new_luogo=""; n_collocazione=""

                    n_prov = st.text_input("Fonte/Regalo", v.get('provenienza', ''))
                    n_fmt = st.text_input("Formato", v.get('formato', '0.75 L (Standard)'))
                    n_an = st.text_input("Annata", v.get('annata','')); n_gr = st.text_input("Gradi", v.get('gradi',''))
                    n_vit = st.text_input("Vitigno", v.get('vitigno',''))
                    n_tip = st.selectbox("Tipo", TIPI_VINO, index=TIPI_VINO.index(v.get('tipo_vino','Fermo')) if v.get('tipo_vino') in TIPI_VINO else 0)
                    n_zuc = st.selectbox("Zucchero", SCALA_ZUCCHERI, index=SCALA_ZUCCHERI.index(v.get('zucchero','N.S.')) if v.get('zucchero') in SCALA_ZUCCHERI else 0)
                    n_pr = st.number_input("Prezzo", value=float(str(v.get('prezzo', 0)).replace(',','.'))); n_qta = st.number_input("Pezzi", value=int(v.get('qta',0)))
                    n_not = st.text_area("Note", v.get('note','')); n_giu = st.text_area("Giudizio", v.get('giudizio',''))
                    st.markdown("---")
                    n_foto = st.file_uploader("📸 Foto", key="edit_upload")
                    
                    if st.form_submit_button("SALVA"):
                        foto_url_new = v.get('foto_url', '')
                        if n_foto: foto_url_new = salva_immagine_cloud(n_foto, folder)
                        fmt_cal = calcola_nome_formato(n_fmt)
                        
                        final_cat = n_new_cat.strip().title() if n_new_cat.strip() else sel_cat
                        final_luogo = n_new_luogo.strip().title() if n_new_luogo.strip() else sel_luogo
                        
                        nuovo_rec = {"nome":n_nome, "azienda":n_az, "provenienza":n_prov, "luogo":final_luogo, "collocazione":n_collocazione, "annata":n_an, "gradi":n_gr, "formato":fmt_cal, "vitigno":n_vit, "tipo_vino":n_tip, "zucchero":n_zuc, "prezzo":n_pr, "qta":n_qta, "note":n_not, "giudizio":n_giu, "foto_url": foto_url_new}
                        if tipo == "CANTINA": nuovo_rec["tipo_cat"] = final_cat
                        save_record(tipo, v['id'], nuovo_rec)
                        st.session_state.id_modifica = None; st.rerun()
                if st.button("Annulla"): st.session_state.id_modifica = None; st.rerun()
        else:
            # ── AGGIUNGI NUOVO ────────────────────────────────────────────
            with st.expander("➕ AGGIUNGI NUOVO", expanded=False):
                a_foto = st.file_uploader("1. Foto", key="add_foto_uploader")
                if a_foto and st.button("✨ SCAN OCR", use_container_width=True):
                    if OCR_AVAILABLE:
                         with st.spinner("Reading..."):
                             n_ia, c_ia, a_ia, g_ia = estrai_dati_da_foto(a_foto.getvalue())
                             st.session_state.new_nome = n_ia; st.session_state.new_az = c_ia; st.session_state.new_ann = a_ia; st.session_state.new_gr = g_ia; st.rerun()
                    else: st.error("No OCR.")
                
                a_n = st.text_input("2. Nome", value=st.session_state.new_nome)
                a_az = st.text_input("3. Cantina", value=st.session_state.new_az)
                if tipo == "CANTINA":
                    def_cat_idx = 0
                    if "⚠️ DA CATALOGARE" in LISTA_CATEGORIE_COMPLETA:
                        def_cat_idx = LISTA_CATEGORIE_COMPLETA.index("⚠️ DA CATALOGARE")
                    
                    sel_cat_add = st.selectbox("4. Categoria esistente...", LISTA_CATEGORIE_COMPLETA, index=def_cat_idx)
                    new_cat_add = st.text_input("...oppure scrivi una NUOVA Categoria", "")

                    def_idx = 0
                    if luogo_corrente in LISTA_LUOGHI_COMPLETA: def_idx = LISTA_LUOGHI_COMPLETA.index(luogo_corrente)
                    sel_la = st.selectbox("5. Sede esistente...", LISTA_LUOGHI_COMPLETA, index=def_idx)
                    new_la = st.text_input("...oppure scrivi una NUOVA Sede", "")
                    
                    new_coll_add = st.text_input("6. Posizione Specifica (es. Scaffale A)", "")
                else: sel_cat_add="Mignon"; new_cat_add=""; sel_la="Casa Principale"; new_la=""; new_coll_add=""

                a_prov = st.text_input("7. Fonte/Regalo", "")
                a_fmt = st.text_input("8. Formato", value="0.75")
                a_an = st.text_input("9. Annata", value=st.session_state.new_ann)
                
                with st.form("add_form"):
                    a_gr = st.text_input("Gradi", value=st.session_state.new_gr); a_pr = st.number_input("Prezzo", value=0.0)
                    if tipo == "CANTINA": a_vit = st.text_input("Vitigno"); a_tip = st.selectbox("Tipo", TIPI_VINO); a_zuc = st.selectbox("Zucchero", SCALA_ZUCCHERI)
                    a_qta = st.number_input("Qta", value=1); a_not = st.text_area("Note")
                    
                    if st.form_submit_button("INSERISCI"):
                        foto_url_new = ""
                        if a_foto: foto_url_new = salva_immagine_cloud(a_foto, folder)
                        fmt_cal = calcola_nome_formato(a_fmt)
                        
                        final_cat = new_cat_add.strip().title() if new_cat_add.strip() else sel_cat_add
                        final_luogo = new_la.strip().title() if new_la.strip() else sel_la
                        
                        nuovo = {"nome": a_n, "azienda": a_az, "provenienza": a_prov, "luogo": final_luogo, "collocazione": new_coll_add, "annata": a_an, "gradi": a_gr, "formato": fmt_cal, "prezzo": a_pr, "qta": a_qta, "foto_url": foto_url_new, "note": a_not, "giudizio": "", "tipo_cat": final_cat if tipo=="CANTINA" else "Mignon"}
                        if tipo == "CANTINA": nuovo.update({"vitigno": a_vit, "tipo_vino": a_tip, "zucchero": a_zuc})
                        add_record(tipo, nuovo)
                        st.session_state.new_nome=""; st.session_state.new_az=""; st.session_state.new_ann=""; st.session_state.new_gr=""; st.rerun()

    st.title(f"{tipo} - {luogo_corrente}")
    
    # ── FILTRO CATEGORIE ──────────────────────────────────────────────────
    st.markdown("### 📂 SELEZIONA CATEGORIA")
    cats_for_filter = [c for c in LISTA_CATEGORIE_COMPLETA if c != "Provati"]
    opzioni_vista = ["TUTTI"] + cats_for_filter + ["Provati"]
    
    def_view_idx = 0
    if "⚠️ DA CATALOGARE" in opzioni_vista:
        def_view_idx = opzioni_vista.index("⚠️ DA CATALOGARE")
    
    categoria_selezionata = st.selectbox("Filtra per:", opzioni_vista, index=def_view_idx)
    
    vini_filtrati_finali = []
    
    # LOOP INVERSO PER MOSTRARE PRIMA GLI ULTIMI INSERITI
    for v in reversed(data):
        m_l = True
        if luogo_corrente != "TUTTE LE SEDI" and tipo == "CANTINA":
            if v.get('luogo', 'Casa Principale') != luogo_corrente: m_l = False
        
        q = int(v.get('qta', 0))
        m_c = False
        if categoria_selezionata == "TUTTI": m_c = (q > 0)
        elif categoria_selezionata == "Provati": m_c = (v.get('tipo_cat') == "Provati" or (q == 0 and tipo=="CANTINA"))
        else: m_c = (v.get('tipo_cat') == categoria_selezionata and q > 0)
        
        m_s = True
        if filtro_txt: m_s = any(filtro_txt in str(val).lower() for val in v.values())
        m_fmt = True
        if filtro_fmt != "TUTTI I FORMATI": m_fmt = (v.get('formato') == filtro_fmt)

        if m_l and m_c and m_s and m_fmt: vini_filtrati_finali.append(v)

    if not vini_filtrati_finali:
        st.info(f"Nessuna bottiglia trovata in: {categoria_selezionata} / {luogo_corrente}")
    else:
        cols = st.columns(3)
        for j, v in enumerate(vini_filtrati_finali):
            with cols[j % 3]:
                vit_d = f"<br>🍇 <i>{v.get('vitigno','')}</i>" if v.get('vitigno') else ""
                pr_d = f"<br>🎁 {v.get('provenienza', '')}" if v.get('provenienza') else ""
                
                pos_spec = v.get('collocazione', '')
                loc_base = v.get('luogo', 'Casa Principale')
                loc_label = ""
                if luogo_corrente == "TUTTE LE SEDI":
                    loc_label = f"<br>📍 <b>{loc_base}</b>"
                    if pos_spec: loc_label += f" <br>📦 {pos_spec}"
                else:
                    if pos_spec: loc_label = f"<br>📦 {pos_spec}"

                st.markdown(f'<div class="card"><div class="card-header">{v["nome"]}</div><div class="card-body">', unsafe_allow_html=True)
                if v.get('foto_url'): st.image(v['foto_url'], use_container_width=True)
                st.markdown(f'<div class="data-box"><b>ID: #{v["id"]}</b> | € {float(str(v.get("prezzo",0)).replace(",", ".")):,.2f} | Qta: <b>{v["qta"]}</b><br>{v.get("formato", "0.75 L (Standard)")}{vit_d}{pr_d}{loc_label}<br><span style="font-size:0.8em">{v.get("azienda", "Sconosciuto")}</span></div>', unsafe_allow_html=True)
                if v.get('giudizio'): st.markdown(f'<div class="giudizio-box"><b>Assaggio:</b> {v["giudizio"][:60]}...</div>', unsafe_allow_html=True)
                st.write("---")
                c1, c2, c3 = st.columns(3)
                if c1.button(" [-] ", key=f"m_{v['id']}"):
                    save_field(tipo, v['id'], 'qta', int(v['qta']) - 1); st.rerun()
                if c2.button(" ✏️ ", key=f"e_{v['id']}"):
                    st.session_state.id_modifica = v['id']; st.rerun()
                if c3.button(" [+] ", key=f"p_{v['id']}"):
                    save_field(tipo, v['id'], 'qta', int(v['qta']) + 1); st.rerun()
                b1, b2 = st.columns(2)
                if b1.button("📖 SCHEDA", key=f"sh_{v['id']}", use_container_width=True):
                    mostra_scheda(v, tipo)
                if categoria_selezionata == "Provati" or int(v.get('qta',0)) == 0:
                    if b2.button("🛒 RE-BUY", key=f"re_{v['id']}", use_container_width=True):
                        save_record(tipo, v['id'], {'qta': 1, 'tipo_cat': v.get('cat_origine', 'Rossi')})
                        st.rerun()
                else:
                    if b2.button("🍷 STAPPA", key=f"s_{v['id']}", use_container_width=True):
                        dialog_stappa(v, tipo)
                st.markdown("</div></div>", unsafe_allow_html=True)
