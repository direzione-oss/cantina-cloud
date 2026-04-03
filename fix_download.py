
with open(r'C:\Progetti\CANTINADEF\cantina_app.py', 'r', encoding='utf-8') as f:
    src = f.read()

src_lf = src.replace('\r\n', '\n')

# Restore PDF section to use st.download_button (simpler, now that magic is off)
old_pdf_start = "    # \u2500\u2500 PDF Downloads (via HTML component \u2014 st.download_button e' rotto) \u2500\u2500"
old_pdf_end = "\n    st.markdown(\"---\")\n\n    # \u2500\u2500 QR CODE"

idx_s = src_lf.find(old_pdf_start)
idx_e = src_lf.find(old_pdf_end, idx_s)

if idx_s < 0 or idx_e < 0:
    print(f"NOT FOUND: start={idx_s}, end={idx_e}")
else:
    new_pdf = """    # \u2500\u2500 PDF Downloads \u2500\u2500
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
            except Exception:
                pass
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
                except Exception:
                    pass
    with pc3:
        if giacenza:
            try:
                _b3 = genera_pdf_catalogo(giacenza, tenant.get("nome","Cantina"))
                st.download_button("Catalogo PDF", data=_b3,
                                   file_name=f"catalogo_{nome_f}.pdf",
                                   mime="application/pdf",
                                   use_container_width=True, type="primary",
                                   key="dl_cat")
            except Exception:
                pass"""

    result = src_lf[:idx_s] + new_pdf + src_lf[idx_e:]

    # Also restore QR download button
    old_qr = """                _qr_b64 = base64.b64encode(card_bytes).decode()
                _qr_fn = f"lista_qr_{sede.lower().replace(' ','_')}.png"
                components.html(f\'\'\'<a href="data:image/png;base64,{_qr_b64}" download="{_qr_fn}"
                    style="display:flex;align-items:center;justify-content:center;width:100%;
                    padding:8px;background:#252525;color:#C9A84C;border:1px solid #555;
                    border-radius:8px;text-decoration:none;font-weight:600;
                    font-family:Inter,sans-serif;font-size:0.82em;box-sizing:border-box;
                    cursor:pointer;">Scarica QR - {sede}</a>\'\'\', height=44)"""

    new_qr = """                st.download_button(
                    label=f"Scarica QR - {sede}",
                    data=card_bytes,
                    file_name=f"lista_qr_{sede.lower().replace(' ','_')}.png",
                    mime="image/png",
                    use_container_width=True,
                    key=f"qr_dl_{i}"
                )"""

    if old_qr in result:
        result = result.replace(old_qr, new_qr, 1)
        print("QR section restored")
    else:
        print("QR section not found (will try without)")

    # Remove components import if no longer needed
    result = result.replace("\n    import streamlit.components.v1 as components\n", "\n", 1)

    with open(r'C:\Progetti\CANTINADEF\cantina_app.py', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(result)
    print("OK - PDF section restored with st.download_button")
