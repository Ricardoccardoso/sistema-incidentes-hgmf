import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

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
[data-testid="stHeaderActionElements"] {display:none !important;} /* Esconde apenas os botões da direita */
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

# ─── Caminhos de dados ────────────────────────────────────────────────────────
DATA_FILE   = "dados_incidentes.csv"
CONFIG_FILE = "config_tabelas.csv"
COLUNAS = [
    "Data_Registro", "Data_Incidente", "Hora_Aproximada", "Turno", "Setor",
    "Cama_Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade", "Dano_Paciente", "Paciente_Foi_Comunicado",
    "Familiar_Foi_Comunicado", "Medico_Foi_Comunicado", "Fatores_Causadores",
    "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Relator", "Funcao_Relator", "Status"
]

# ─── Funções de carga ─────────────────────────────────────────────────────────
def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=COLUNAS)
        df.to_csv(DATA_FILE, index=False)
        return df
    return pd.read_csv(DATA_FILE)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        opcoes_padrao = [
            # Turno
            {"Tabela": "Turno", "Opcao": "Manhã (07h–13h)",   "Ativo": True},
            {"Tabela": "Turno", "Opcao": "Tarde (13h–19h)",   "Ativo": True},
            {"Tabela": "Turno", "Opcao": "Noite (19h–07h)",   "Ativo": True},
            # Tipo Geral
            {"Tabela": "Tipo Geral", "Opcao": "Assistencial",   "Ativo": True},
            {"Tabela": "Tipo Geral", "Opcao": "Administrativa", "Ativo": True},
            {"Tabela": "Tipo Geral", "Opcao": "Infraestrutura", "Ativo": True},
            # Setores
            {"Tabela": "Setor", "Opcao": "Emergência (REA)",       "Ativo": True},
            {"Tabela": "Setor", "Opcao": "UTI Adulto",             "Ativo": True},
            {"Tabela": "Setor", "Opcao": "UTI Neonatal",           "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Enfermaria Clínica",     "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Enfermaria Cirúrgica",   "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Centro Cirúrgico",       "Ativo": True},
            {"Tabela": "Setor", "Opcao": "CME",                    "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Farmácia",               "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Laboratório",            "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Radiologia/Imagem",      "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Ambulatório",            "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Recepção/Admissão",      "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Outro",                  "Ativo": True},
            # Categorias
            {"Tabela": "Categoria", "Opcao": "Lesão por Pressão (LPP)",              "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Queda do Paciente",                    "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Falha na Segurança Medicamentosa",     "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Falha de Identificação do Paciente",   "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Infecção Relacionada à Assistência",   "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Falha em Procedimento/Cirurgia",       "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Falha em Equipamento/Dispositivo",     "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Reação Transfusional",                 "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Evento de Comunicação/Informação",     "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Violência / Agressão",                 "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Extubação não Planejada",              "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Saída não Autorizada do Paciente",     "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Outro Incidente Assistencial",         "Ativo": True},
            # Subcategorias de LPP
            {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio I",    "Ativo": True},
            {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio II",   "Ativo": True},
            {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio III",  "Ativo": True},
            {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio IV",   "Ativo": True},
            {"Tabela": "Subcategoria_LPP", "Opcao": "Não Classificável", "Ativo": True},
            {"Tabela": "Subcategoria_LPP", "Opcao": "Tecido Mucoso", "Ativo": True},
            # Subcategorias de Queda
            {"Tabela": "Subcategoria_Queda", "Opcao": "Queda da própria altura",     "Ativo": True},
            {"Tabela": "Subcategoria_Queda", "Opcao": "Queda do leito",              "Ativo": True},
            {"Tabela": "Subcategoria_Queda", "Opcao": "Queda durante transferência", "Ativo": True},
            {"Tabela": "Subcategoria_Queda", "Opcao": "Queda no banheiro",           "Ativo": True},
            {"Tabela": "Subcategoria_Queda", "Opcao": "Outro",                       "Ativo": True},
            # Subcategorias Medicamento
            {"Tabela": "Subcategoria_Med", "Opcao": "Dose errada",         "Ativo": True},
            {"Tabela": "Subcategoria_Med", "Opcao": "Medicamento errado",  "Ativo": True},
            {"Tabela": "Subcategoria_Med", "Opcao": "Via errada",          "Ativo": True},
            {"Tabela": "Subcategoria_Med", "Opcao": "Horário errado",      "Ativo": True},
            {"Tabela": "Subcategoria_Med", "Opcao": "Omissão de dose",     "Ativo": True},
            {"Tabela": "Subcategoria_Med", "Opcao": "Paciente errado",     "Ativo": True},
            {"Tabela": "Subcategoria_Med", "Opcao": "Reação adversa",      "Ativo": True},
            # Gravidade (escala OMS)
            {"Tabela": "Gravidade", "Opcao": "Near Miss (Quase Evento - não atingiu o paciente)", "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Sem Dano (atingiu, sem lesão)",                     "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Dano Leve (lesão leve/temporária)",                 "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Dano Moderado (lesão moderada/temporária)",         "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Dano Grave (lesão grave/permanente)",               "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Óbito",                                             "Ativo": True},
            # Fatores Causadores
            {"Tabela": "Fator Causador", "Opcao": "Déficit de pessoal / Sobrecarga",        "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha na comunicação entre equipes",     "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha na comunicação escrita/verbal",    "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falta de treinamento / capacitação",     "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Equipamento com defeito",                "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falta de material / insumo",             "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Ambiente inadequado / risco físico",     "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha no processo/protocolo",            "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Distração / interrupção",                "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Erro humano (sem negligência)",          "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha no sistema de medicação",         "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Causa ainda não identificada",          "Ativo": True},
        ]
        df_conf = pd.DataFrame(opcoes_padrao)
        df_conf.to_csv(CONFIG_FILE, index=False)
        return df_conf
    return pd.read_csv(CONFIG_FILE)

def get_opcoes(df_conf, tabela):
    ops = df_conf[(df_conf["Tabela"] == tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return ops if ops else ["Sem opções configuradas"]

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
            df_dados = pd.concat([df_dados, pd.DataFrame([novo])], ignore_index=True)
            df_dados.to_csv(DATA_FILE, index=False)
            st.success("✅ Notificação enviada com sucesso! Obrigado por contribuir com a segurança do nosso hospital.")
            st.balloons()
