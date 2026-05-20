import streamlit as st
import pandas as pd
import os
from datetime import datetime
import altair as alt

# Nomes dos arquivos de banco de dados
DATA_FILE = "dados_incidentes_v3.csv"
CONFIG_FILE = "config_tabelas.csv"

# ---------------------------------------------------------
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ---------------------------------------------------------
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

def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "Data_Registro", "Data_Incidente", "Turno", "Setor", "Cama_Leito", 
            "Tipo_Geral", "Categoria_Incidente", "Medicamento_Envolvido", 
            "Gravidade", "Fatores_Causadores", "Descricao", "Relator", "Funcao_Relator"
        ])
        df.to_csv(DATA_FILE, index=False)
        return df
    return pd.read_csv(DATA_FILE)

def get_opcoes_ativas(df_conf, nome_tabela):
    opcoes = df_conf[(df_conf["Tabela"] == nome_tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return opcoes if opcoes else ["Nenhuma opção ativa"]

# ---------------------------------------------------------
# CONFIGURAÇÃO DA INTERFACE E MENU
# ---------------------------------------------------------
st.set_page_config(page_title="Gestão de Incidentes - HGMF", layout="wide", initial_sidebar_state="expanded")
st.title("🏥 Sistema de Gestão da Qualidade e Segurança do Paciente")

df_config = load_config()
df_dados = load_data()

# Menu lateral
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Selecione a página:", [
    "📝 Registrar Incidente", 
    "📊 Painel de Indicadores", 
    "⚙️ Configurações"
])

# SISTEMA DE SEGURANÇA PARA AS ABAS DE GESTÃO
if menu in ["📊 Painel de Indicadores", "⚙️ Configurações"]:
    st.sidebar.markdown("---")
    senha_digitada = st.sidebar.text_input("🔑 Senha de Acesso (Gestão)", type="password")
    
    # A senha provisória é admin123
    if senha_digitada != "admin123":
        st.warning("⚠️ Área restrita à Coordenação de Qualidade e Segurança do Paciente. Insira a senha no menu lateral para acessar.")
        st.stop() # Para a execução do código aqui, impedindo que os gráficos apareçam

# ---------------------------------------------------------
# ECRÃ 1: FORMULÁRIO DE REGISTRO (PÚBLICO PARA A EQUIPE)
# ---------------------------------------------------------
if menu == "📝 Registrar Incidente":
    st.header("Novo Registro de Incidente")
    st.info("Preencha os dados abaixo. As informações serão enviadas de forma sigilosa ao Núcleo de Segurança do Paciente.")
    
    with st.form("form_incidente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data_incidente = st.date_input("Data do Incidente")
            turno = st.selectbox("Turno da Ocorrência", get_opcoes_ativas(df_config, "Turno"))
            setor = st.selectbox("Setor da Ocorrência", get_opcoes_ativas(df_config, "Setor"))
            cama = st.text_input("Cama / Leito do Paciente")
            tipo_geral = st.radio("Tipo de Ocorrência", get_opcoes_ativas(df_config, "Tipo Geral"))
            
        with col2:
            categoria = st.selectbox("Categoria do Incidente", get_opcoes_ativas(df_config, "Categoria"))
            
            medicamento = ""
            if categoria == "Falha na Segurança Medicamentosa":
                medicamento = st.text_input("⚠️ Nome do Medicamento Envolvido (Opcional)")
                
            gravidade = st.select_slider(
                "Grau de Dano (Gravidade)", 
                options=get_opcoes_ativas(df_config, "Gravidade")
            )
            
            fatores = st.multiselect(
                "Fatores Causadores (Pode escolher vários)", 
                get_opcoes_ativas(df_config, "Fator Causador")
            )
            
        descricao = st.text_area("Descrição Breve do Incidente")
        
        st.markdown("---")
        st.subheader("Dados do Relator (Opcional - Garantimos o Anonimato)")
        col3, col4 = st.columns(2)
        with col3:
            relator = st.text_input("Nome de quem está reportando")
        with col4:
            funcao = st.text_input("Função (ex: Enfermeiro, Médico)")
        
        submit = st.form_submit_button("📤 Enviar Notificação")
        
        if submit:
            novo_registro = {
                "Data_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Data_Incidente": data_incidente,
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
            df_dados = pd.concat([df_dados, pd.DataFrame([novo_registro])], ignore_index=True)
            df_dados.to_csv(DATA_FILE, index=False)
            st.success("✅ Incidente registrado com sucesso! Agradecemos sua colaboração para a segurança dos pacientes.")

# ---------------------------------------------------------
# ECRÃ 2: PAINEL DE INDICADORES (RESTRITO)
# ---------------------------------------------------------
elif menu == "📊 Painel de Indicadores":
    st.header("Dashboard de Segurança do Paciente")
    
    if df_dados.empty:
        st.info("Ainda não existem dados na base. Registre um incidente primeiro.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Notificações", len(df_dados))
        col2.metric("Incidentes Sem Dano", len(df_dados[df_dados["Gravidade"] == "Sem Dano"]))
        col3.metric("Total de LPP", len(df_dados[df_dados["Categoria_Incidente"] == "Lesão por Pressão (LPP)"]))
        col4.metric("Total de Quedas", len(df_dados[df_dados["Categoria_Incidente"] == "Queda do Paciente"]))
        
        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Proporção por Gravidade")
            df_gravidade = df_dados["Gravidade"].value_counts().reset_index()
            df_gravidade.columns = ["Gravidade", "Quantidade"]
            grafico_pizza = alt.Chart(df_gravidade).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Quantidade", type="quantitative"),
                color=alt.Color(field="Gravidade", type="nominal", scale=alt.Scale(scheme="category10")),
                tooltip=["Gravidade", "Quantidade"]
            ).properties(height=350)
            st.altair_chart(grafico_pizza, use_container_width=True)
            
        with col_chart2:
            st.subheader("Incidentes por Categoria")
            st.bar_chart(df_dados["Categoria_Incidente"].value_counts())

# ---------------------------------------------------------
# ECRÃ 3: CONFIGURAÇÕES (RESTRITO)
# ---------------------------------------------------------
elif menu == "⚙️ Configurações":
    st.header("⚙️ Configuração de Tabelas")
    
    tabelas_disponiveis = df_config["Tabela"].unique()
    tabela_selecionada = st.selectbox("Selecione o Menu que deseja configurar:", tabelas_disponiveis)
    
    df_filtro = df_config[df_config["Tabela"] == tabela_selecionada].copy()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Gerenciar opções de: {tabela_selecionada}")
        df_editado = st.data_editor(
            df_filtro,
            column_config={
                "Ativo": st.column_config.CheckboxColumn("Ativo (Mostrar)?", default=True),
                "Tabela": None
            },
            disabled=["Opcao"],
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("💾 Salvar Status"):
            for idx, row in df_editado.iterrows():
                mask = (df_config["Tabela"] == tabela_selecionada) & (df_config["Opcao"] == row["Opcao"])
                df_config.loc[mask, "Ativo"] = row["Ativo"]
            
            df_config.to_csv(CONFIG_FILE, index=False)
            st.success("✅ Configurações atualizadas!")
            st.rerun()
            
    with col2:
        st.subheader("➕ Adicionar Novo Item")
        nova_opcao = st.text_input("Escreva o nome da nova opção:")
        
        if st.button("Adicionar"):
            if nova_opcao.strip() != "":
                existe = ((df_config["Tabela"] == tabela_selecionada) & (df_config["Opcao"].str.lower() == nova_opcao.lower())).any()
                if not existe:
                    novo_reg = {"Tabela": tabela_selecionada, "Opcao": nova_opcao.strip(), "Ativo": True}
                    df_config = pd.concat([df_config, pd.DataFrame([novo_reg])], ignore_index=True)
                    df_config.to_csv(CONFIG_FILE, index=False)
                    st.success("✅ Adicionado com sucesso!")
                    st.rerun()