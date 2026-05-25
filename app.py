import streamlit as st
import pandas as pd
from datetime import datetime, date
import db  # camada de acesso ao Supabase

st.set_page_config(
    page_title="Notificação de Incidente - HGMF",
    page_icon="🏥",
    layout="centered"
)

# ─── CSS: oculta controles do Streamlit e aplica identidade visual ───────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

[data-testid="stSidebar"]          {display:none !important;}
[data-testid="stAppDeployButton"]  {display:none !important;}
[data-testid="stHeader"]           {display:none !important; visibility:hidden !important;}
header                             {display:none !important; visibility:hidden !important;}
[data-testid="stDecoration"]       {display:none !important;}
footer                             {display:none !important;}
[data-testid="stSidebarNav"]       {display:none !important;}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.block-container { padding-top: 1.5rem !important; max-width: 780px; }

.cabecalho {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%);
    border-radius: 16px;
    padding: 28px 32px 22px 32px;
    margin-bottom: 24px;
    box-shadow: 0 4px 24px rgba(13,71,161,0.18);
    text-align: center;
}
.cabecalho h1 { color: #fff; font-size: 1.45rem; font-weight: 700; margin:0 0 4px 0; letter-spacing:-0.3px; }
.cabecalho p  { color: #bbdefb; font-size: 0.88rem; margin:0; }

.aviso-sigilo {
    background: #e3f2fd;
    border-left: 4px solid #1976d2;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 20px;
    color: #0d47a1;
    font-size: 0.88rem;
    font-weight: 500;
}

.secao-titulo {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #1565c0;
    margin: 22px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 2px solid #e3f2fd;
}

div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #0d47a1, #1976d2) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 14px !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 4px 14px rgba(13,71,161,0.3) !important;
    transition: all 0.2s !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(13,71,161,0.4) !important;
}

div[data-testid="stRadio"] > label          { font-size: 0.9rem; }
div[data-testid="stSelectbox"] > label      { font-size: 0.9rem; font-weight:500; }
div[data-testid="stTextInput"] > label      { font-size: 0.9rem; font-weight:500; }
div[data-testid="stTextArea"] > label       { font-size: 0.9rem; font-weight:500; }
div[data-testid="stMultiSelect"] > label    { font-size: 0.9rem; font-weight:500; }
div[data-testid="stDateInput"] > label      { font-size: 0.9rem; font-weight:500; }
div[data-testid="stSelectSlider"] > label   { font-size: 0.9rem; font-weight:500; }
div[data-testid="stCheckbox"] > label       { font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)

# ─── Funções delegadas ao módulo db ──────────────────────────────────────────
load_data   = db.load_data
load_config = db.load_config

def get_opcoes(df_conf, tabela):
    return db.get_opcoes(df_conf, tabela)

# ─── (bloco removido — opções padrão agora vivem em db.py) ───────────────────

# ─── Cabeçalho ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cabecalho">
  <h1>🏥 Hospital Geral Menandro de Faria</h1>
  <p>Núcleo de Segurança do Paciente — Notificação de Incidente</p>
</div>
<div class="aviso-sigilo">
  🔒 <strong>Sigilo garantido.</strong> Sua identidade é opcional e nunca será divulgada. 
  Este relato ajuda a proteger pacientes e profissionais. Notifique sem medo.
</div>
""", unsafe_allow_html=True)

df_config = load_config()
df_dados  = load_data()

with st.form("form_notificacao", clear_on_submit=True):

    # ── BLOCO 1: Dados do Evento ──────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">📅 Dados do Evento</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        data_incidente = st.date_input("Data do Incidente", value=date.today(), max_value=date.today())
    with c2:
        hora_aprox = st.selectbox("Hora Aproximada", [
            "Não sei informar", "00h–02h", "02h–04h", "04h–06h", "06h–08h",
            "08h–10h", "10h–12h", "12h–14h", "14h–16h", "16h–18h",
            "18h–20h", "20h–22h", "22h–00h"
        ])
    with c3:
        turno = st.selectbox("Turno", get_opcoes(df_config, "Turno"))

    c4, c5 = st.columns([3, 1])
    with c4:
        setor = st.selectbox("Setor / Unidade de Ocorrência", get_opcoes(df_config, "Setor"))
    with c5:
        cama = st.text_input("Leito / Cama", placeholder="Ex: 12A")

    # ── BLOCO 2: Tipo do Incidente ────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">📋 Tipo do Incidente</div>', unsafe_allow_html=True)
    tipo_geral = st.radio(
        "Natureza do incidente",
        get_opcoes(df_config, "Tipo Geral"),
        horizontal=True
    )

    categoria = st.selectbox("Categoria do Incidente", get_opcoes(df_config, "Categoria"))

    # Subcategorias dinâmicas conforme categoria
    subcategoria = ""
    medicamento  = ""

    if categoria == "Lesão por Pressão (LPP)":
        subcategoria = st.selectbox("Estágio da LPP", get_opcoes(df_config, "Subcategoria_LPP"))
        local_lpp = st.text_input("Região anatômica afetada", placeholder="Ex: sacral, calcâneo direito")
        subcategoria = subcategoria + (f" — {local_lpp}" if local_lpp else "")

    elif categoria == "Queda do Paciente":
        subcategoria = st.selectbox("Tipo de Queda", get_opcoes(df_config, "Subcategoria_Queda"))
        st.info("💡 Lembre-se de preencher o Boletim de Queda físico no setor, se aplicável.")

    elif categoria == "Falha na Segurança Medicamentosa":
        subcategoria = st.selectbox("Tipo de Falha Medicamentosa", get_opcoes(df_config, "Subcategoria_Med"))
        medicamento  = st.text_input("Medicamento(s) envolvido(s)", placeholder="Ex: Heparina 5000 UI")

    # ── BLOCO 3: Gravidade e Dano ─────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">⚠️ Gravidade e Dano</div>', unsafe_allow_html=True)
    gravidade_ops = get_opcoes(df_config, "Gravidade")
    gravidade = st.select_slider("Nível de Gravidade / Classificação do Dano", options=gravidade_ops)

    dano_desc = st.text_input(
        "Descrição sucinta do dano observado (se houver)",
        placeholder="Ex: escoriação no joelho direito, sem sangramento ativo"
    )

    c6, c7, c8 = st.columns(3)
    with c6:
        pac_comunicado = st.checkbox("Paciente foi comunicado?")
    with c7:
        fam_comunicado = st.checkbox("Familiar foi comunicado?")
    with c8:
        med_comunicado = st.checkbox("Médico responsável foi comunicado?")

    # ── BLOCO 4: Fatores e Descrição ──────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🔍 Fatores Causadores e Descrição</div>', unsafe_allow_html=True)
    fatores = st.multiselect(
        "Fatores que contribuíram para o incidente (selecione todos que se aplicam)",
        get_opcoes(df_config, "Fator Causador")
    )

    descricao = st.text_area(
        "Descreva o que aconteceu (O quê? Como? Onde? Sequência dos fatos)",
        height=130,
        placeholder="Relate os fatos de forma objetiva, sem identificar pacientes. Ex: Paciente em pós-op imediato foi encontrado no chão ao lado do leito às 14h30..."
    )

    acoes_imediatas = st.text_area(
        "Ações imediatas realizadas (o que foi feito logo após o incidente?)",
        height=80,
        placeholder="Ex: Chamado médico, curativo aplicado, grade do leito levantada..."
    )

    sugestao = st.text_area(
        "Sugestão para evitar que isso ocorra novamente (opcional)",
        height=70,
        placeholder="Ex: Revisar protocolo de contenção de pacientes agitados..."
    )

    # ── BLOCO 5: Identificação Opcional ──────────────────────────────────────
    st.markdown('<div class="secao-titulo">👤 Sua Identificação (totalmente opcional)</div>', unsafe_allow_html=True)
    st.caption("Sua identidade nunca será vinculada ao relato de forma pública. É opcional e serve apenas para contato em caso de dúvida pelo Núcleo.")
    c9, c10 = st.columns(2)
    with c9:
        relator = st.text_input("Seu Nome", placeholder="Opcional")
    with c10:
        funcao  = st.text_input("Sua Função / Cargo", placeholder="Ex: Técnico de Enfermagem")

    st.markdown("---")
    enviar = st.form_submit_button("📤 Enviar Notificação ao Núcleo de Segurança", use_container_width=True)

    if enviar:
        if not descricao.strip():
            st.warning("⚠️ Por favor, descreva o incidente antes de enviar.")
        else:
            novo = {
                "Data_Registro":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Data_Incidente":           str(data_incidente),
                "Hora_Aproximada":          hora_aprox,
                "Turno":                    turno,
                "Setor":                    setor,
                "Cama_Leito":               cama,
                "Tipo_Geral":               tipo_geral,
                "Categoria_Incidente":      categoria,
                "Subcategoria":             subcategoria,
                "Medicamento_Envolvido":    medicamento,
                "Gravidade":                gravidade,
                "Dano_Paciente":            dano_desc,
                "Paciente_Foi_Comunicado":  "Sim" if pac_comunicado else "Não",
                "Familiar_Foi_Comunicado":  "Sim" if fam_comunicado else "Não",
                "Medico_Foi_Comunicado":    "Sim" if med_comunicado else "Não",
                "Fatores_Causadores":       ", ".join(fatores),
                "Descricao":               descricao,
                "Acoes_Imediatas":          acoes_imediatas,
                "Sugestao_Melhoria":        sugestao,
                "Relator":                  relator,
                "Funcao_Relator":           funcao,
                "Status":                   "Novo"
            }
            db.save_incidente(novo)
            st.success("✅ Notificação enviada com sucesso! Obrigado por contribuir com a segurança do nosso hospital.")
            st.balloons()
