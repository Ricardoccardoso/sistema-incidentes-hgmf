import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Gestão de Incidentes - HGMF", layout="wide")

# Blindagem total para o usuário não ver absolutamente nada do painel
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stAppDeployButton"] {display: none !important;}
    [data-testid="stHeader"] {display: none !important; visibility: hidden !important;}
    header {display: none !important; visibility: hidden !important;}
    [data-testid="stDecoration"] {display: none !important;}
    footer {display: none !important;}
    </style>
""", unsafe_allow_html=True)

CONFIG_FILE = "config_tabelas.csv"

# =====================================================================
GOOGLE_SHEET_URL = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA_DO_GOOGLE"
# =====================================================================

def load_data():
    DATA_FILE = "dados_backup_nuvem.csv"
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "Data_Registro", "Data_Incidente", "Turno", "Setor", "Cama_Leito", 
            "Tipo_Geral", "Categoria_Incidente", "Medicamento_Envolvido", 
            "Gravidade", "Fatores_Causadores", "Descricao", "Relator", "Funcao_Relator"
        ])
        try:
            csv_url = GOOGLE_SHEET_URL.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
            df_sheets = pd.read_csv(csv_url)
            if not df_sheets.empty:
                df_sheets.to_csv(DATA_FILE, index=False)
                return df_sheets
        except:
            pass
        df.to_csv(DATA_FILE, index=False)
        return df
    return pd.read_csv(DATA_FILE)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        opcoes_padrao = [
            {"Tabela": "Turno", "Opcao": "Manhã", "Ativo": True},
            {"Tabela": "Turno", "Opcao": "Tarde", "Ativo": True},
            {"Tabela": "Turno", "Opcao": "Noite", "Ativo": True},
            {"Tabela": "Tipo Geral", "Opcao": "Assistencial", "Ativo": True},
            {"Tabela": "Tipo Geral", "Opcao": "Administrativa", "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Emergência (REA)", "Ativo": True},
            {"Tabela": "Setor", "Opcao": "UTI", "Ativo": True},
            {"Tabela": "Setor", "Opcao": "Enfermaria Clínica", "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Lesão por Pressão (LPP)", "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Queda do Paciente", "Ativo": True},
            {"Tabela": "Categoria", "Opcao": "Falha na Segurança Medicamentosa", "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Sem Dano", "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Dano Leve", "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Óbito", "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Déficit de pessoal / Sobrecarga", "Ativo": True},
        ]
        df_conf = pd.DataFrame(opcoes_padrao)
        df_conf.to_csv(CONFIG_FILE, index=False)
        return df_conf
    return pd.read_csv(CONFIG_FILE)

def get_opcoes_ativas(df_conf, nome_tabela):
    opcoes = df_conf[(df_conf["Tabela"] == nome_tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return opcoes if opcoes else ["Nenhuma opção ativa"]

df_config = load_config()
df_dados = load_data()

st.title("🏥 Hospital Geral Menandro de Faria")
st.header("Notificação de Incidente Assistencial / Administrativo")
st.info("Garantimos o sigilo absoluto do seu relato. Ajude-nos a melhorar a segurança do nosso hospital.")

with st.form("form_publico", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        data_incidente = st.date_input("Data do Incidente")
        turno = st.selectbox("Turno", get_opcoes_ativas(df_config, "Turno"))
        setor = st.selectbox("Setor Ocorrência", get_opcoes_ativas(df_config, "Setor"))
        cama = st.text_input("Leito / Cama")
        tipo_geral = st.radio("Tipo", get_opcoes_ativas(df_config, "Tipo Geral"))
    with col2:
        categoria = st.selectbox("Categoria", get_opcoes_ativas(df_config, "Categoria"))
        medicamento = ""
        if categoria == "Falha na Segurança Medicamentosa":
            medicamento = st.text_input("Medicamento Envolvido (Opcional)")
        gravidade = st.select_slider("Gravidade do Dano", options=get_opcoes_ativas(df_config, "Gravidade"))
        fatores = st.multiselect("Fatores Causadores", get_opcoes_ativas(df_config, "Fator Causador"))
        
    descricao = st.text_area("Descrição do Incidente")
    st.markdown("---")
    st.subheader("Identificação (Opcional)")
    c3, c4 = st.columns(2)
    with c3:
        relator = st.text_input("Seu Nome")
    with c4:
        funcao = st.text_input("Sua Função")
        
    submit = st.form_submit_button("📤 Enviar Notificação para o Núcleo", use_container_width=True)
    if submit:
        novo_registro = {
            "Data_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Data_Incidente": str(data_incidente),
            "Turno": turno,
            "Setor": setor,
            "Cama_Leito": cama,
            "Tipo_Geral": tipo_geral,
            "Categoria_Incidente": categoria,
            "Medicamento_Envolvido": medicamento,
            "Gravidade": gravidade,
            "Fatores_Causadores": ", ".join(fatores),
            "Descricao": descricao,
            "Relator": relator,
            "Funcao_Relator": funcao
        }
        DATA_FILE = "dados_backup_nuvem.csv"
        df_dados = pd.concat([df_dados, pd.DataFrame([novo_registro])], ignore_index=True)
        df_dados.to_csv(DATA_FILE, index=False)
        st.success("✅ Notificação enviada com sucesso ao Núcleo de Segurança do Paciente!")
        st.balloons()
