import streamlit as st
import pandas as pd
import os
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
load_field_flags = getattr(db, "load_field_flags", lambda: pd.DataFrame())

def get_opcoes(df_conf, tabela):
    return db.get_opcoes(df_conf, tabela)

GRAVIDADE_ORDEM = [
    "Near Miss (Quase Evento - não atingiu o paciente)",
    "Sem Dano (atingiu, sem lesão)",
    "Dano Leve (lesão leve/temporária)",
    "Dano Moderado (lesão moderada/temporária)",
    "Dano Grave (lesão grave/permanente)",
    "Óbito",
]

def ordenar_gravidade(opcoes):
    ordem = {valor: indice for indice, valor in enumerate(GRAVIDADE_ORDEM)}
    return sorted(opcoes, key=lambda x: ordem.get(x, len(opcoes)))

# ─── Cabeçalho ────────────────────────────────────────────────────────────────
if os.path.exists("logo.png"):
        st.image("logo.png", width=140)
        st.markdown('<div style="text-align:center; margin-bottom:8px;">'
                                '<h1 style="margin:6px 0 0; font-size:1.25rem">Hospital Geral Menandro de Faria</h1>'
                                '<p style="margin:0; color:#546e7a">Núcleo de Segurança do Paciente — Notificação de Incidente</p></div>', unsafe_allow_html=True)
else:
        st.markdown("""
        <div class="cabecalho">
            <h1>🏥 Hospital Geral Menandro de Faria</h1>
            <p>Núcleo de Segurança do Paciente — Notificação de Incidente</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown(f"""
<div class="aviso-sigilo">
    🔒 <strong>Notificação sigilosa, a identificação do notificador é opcional.</strong>
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
        turno = st.selectbox("Hora/Turno do Incidente", get_opcoes(df_config, "Turno"))
    with c3:
        pass

    c4, c5 = st.columns([3, 1])
    with c4:
        setor = st.selectbox("Setor / Unidade de Ocorrência", get_opcoes(df_config, "Setor"))
    with c5:
        cama = st.text_input("Leito", placeholder="Ex: 12A")

    # Novos campos: data/hora do relato e dados do paciente
    try:
        fflags = load_field_flags()
    except Exception:
        fflags = pd.DataFrame()
    def label(campo, texto):
        try:
            req = bool(fflags[fflags["Campo"] == campo]["Obrigatorio"].iloc[0])
        except Exception:
            req = False
        return texto + (" *" if req else "")

    st.markdown('<div class="secao-titulo">📝 Dados do Relato / Paciente</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1.5, 1.5, 4])
    with r1:
        data_relato = st.date_input(label("Data_Relato", "Data do Relato"), value=date.today())
    with r2:
        hora_relato = st.time_input(label("Hora_Relato", "Hora do Relato"))
    with r3:
        nome_paciente = st.text_input(label("Nome_Paciente", "Nome do Paciente"), placeholder="Ex: João da Silva")

    s1, s2 = st.columns([1.1, 0.4])
    with s1:
        data_nasc = st.date_input(label("Data_Nascimento", "Data de Nascimento do Paciente"), value=date(2000,1,1))
    with s2:
        pass

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
    gravidade_ops = ordenar_gravidade(get_opcoes(df_config, "Gravidade"))
    gravidade = st.select_slider("Nível de Gravidade / Classificação do Dano", options=gravidade_ops)

    # Observação: campo de dano e caixas de comunicação removidos conforme solicitado

    # ── BLOCO 4: Fatores e Descrição ──────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🔍 Fatores Causadores e Descrição</div>', unsafe_allow_html=True)
    fatores = st.multiselect(
        "Fatores que contribuíram para o incidente (selecione todos os itens aplicáveis)",
        get_opcoes(df_config, "Fator Causador")
    )

    descricao = st.text_area(
        "Descreva o que aconteceu (O quê? Como? Onde? Sequência dos fatos)",
        height=130,
        placeholder="Relate os fatos de forma objetiva. Ex: Paciente em pós-op imediato foi encontrado no chão ao lado do leito às 14h30..."
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
        # validação de obrigatoriedade baseada nas flags de campos
        missing = []
        try:
            reqs = {row['Campo']: bool(row['Obrigatorio']) for _, row in fflags.iterrows()}
        except Exception:
            reqs = {}
        if reqs.get('Nome_Paciente', False) and not nome_paciente.strip():
            missing.append('Nome do Paciente')
        if reqs.get('Data_Relato', False) and not data_relato:
            missing.append('Data do Relato')
        if reqs.get('Hora_Relato', False) and not hora_relato:
            missing.append('Hora do Relato')
        if reqs.get('Data_Nascimento', False) and not data_nasc:
            missing.append('Data de Nascimento')

        if missing:
            st.warning(f"⚠️ Preencha os campos obrigatórios: {', '.join(missing)}")
        elif not descricao.strip():
            st.warning("⚠️ Por favor, descreva o incidente antes de enviar.")
        else:
            novo = {
                "Data_Registro":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Data_Incidente":           str(data_incidente),
                "Turno":                    turno,
                "Setor":                    setor,
                "Leito":                    cama,
                "Tipo_Geral":               tipo_geral,
                "Categoria_Incidente":      categoria,
                "Subcategoria":             subcategoria,
                "Medicamento_Envolvido":    medicamento,
                "Gravidade":                gravidade,
                "Data_Relato":              str(data_relato),
                "Hora_Relato":              str(hora_relato),
                "Nome_Paciente":            nome_paciente,
                "Data_Nascimento":          str(data_nasc),
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
