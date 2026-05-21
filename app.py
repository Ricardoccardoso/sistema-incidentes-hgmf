import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página - Barra lateral oculta por padrão
st.set_page_config(page_title="HGMF - Notificação de Incidentes", layout="wide", initial_sidebar_state="collapsed")

# BLINDAGEM TOTAL - CSS para ocultar menus de desenvolvedor
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stAppDeployButton"] {display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    header {display: none !important;}
    footer {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# Link do Google Sheets (Configure depois)
GOOGLE_SHEET_URL = "SUA_PLANILHA_AQUI"

# Funções de carregar dados (Mantendo local por enquanto, pronto para Sheets)
def load_config():
    if not os.path.exists("config_tabelas.csv"):
        df = pd.DataFrame([{"Tabela": "Setor", "Opcao": "Emergência", "Ativo": True}])
        df.to_csv("config_tabelas.csv", index=False)
    return pd.read_csv("config_tabelas.csv")

def save_incidente(dados):
    df = pd.read_csv("dados.csv") if os.path.exists("dados.csv") else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
    df.to_csv("dados.csv", index=False)

# --- INTERFACE PÚBLICA ---
st.title("🏥 Notificação de Incidentes - HGMF")
st.info("Relato sigiloso para o Núcleo de Segurança do Paciente.")

with st.form("form_publico", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data da Ocorrência")
        setor = st.selectbox("Setor", ["Emergência", "UTI", "Clínica Médica", "Centro Cirúrgico"])
        tipo = st.radio("Tipo de Incidente", ["Assistencial", "Administrativo"])
    with col2:
        categoria = st.selectbox("Categoria", ["Queda", "Medicação", "LPP", "Identificação", "Outros"])
        gravidade = st.select_slider("Gravidade Percebida", options=["Sem Dano", "Leve", "Moderado", "Grave"])
    
    descricao = st.text_area("Descrição do ocorrido")
    
    if st.form_submit_button("Enviar Notificação", use_container_width=True):
        registro = {
            "Data_Registro": datetime.now(),
            "Data_Incidente": str(data),
            "Setor": setor,
            "Tipo": tipo,
            "Categoria": categoria,
            "Gravidade": gravidade,
            "Descricao": descricao
        }
        save_incidente(registro)
        st.success("Notificação enviada com sucesso!")
        st.balloons()
