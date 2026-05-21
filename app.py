import streamlit as st
import pandas as pd
import os
from datetime import datetime
import altair as alt

# Configuração da página (deve ser a primeira coisa no código)
st.set_page_config(page_title="Gestão de Incidentes - HGMF", layout="wide", initial_sidebar_state="collapsed")

# Nomes dos arquivos
CONFIG_FILE = "config_tabelas.csv"

# =====================================================================
# ⚠️ ADICIONE O LINK DA SUA PLANILHA GOOGLE DISPONÍVEL PARA EDIÇÃO AQUI
# =====================================================================
GOOGLE_SHEET_URL = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA_DO_GOOGLE"

# ---------------------------------------------------------
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# SISTEMA DE ROTAS (LINK DA GESTÃO)
# ---------------------------------------------------------
parametros_url = st.query_params
modo_gestao = parametros_url.get("painel") == "gestao"

# --- ESCONDER ELEMENTOS DO STREAMLIT E BARRA LATERAL PARA O PÚBLICO ---
if not modo_gestao:
    esconder_elementos = """
        <style>
        [data-testid="stSidebar"] {display: none;} /* Oculta a barra lateral */
        #MainMenu {visibility: hidden;} /* Oculta ferramentas de desenvolvedor */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """
    st.markdown(esconder_elementos, unsafe_allow_html=True)

# ---------------------------------------------------------
# MÓDULO 1: VISÃO PÚBLICA (APENAS FORMULÁRIO DO QR CODE)
# ---------------------------------------------------------
if not modo_gestao:
    st.title("🏥 Sistema de Gestão da Qualidade e Segurança do Paciente")
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
                
            gravidade = st.select_slider("Grau de Dano (Gravidade)", options=get_opcoes_ativas(df_config, "Gravidade"))
            fatores = st.multiselect("Fatores Causadores", get_opcoes_ativas(df_config, "Fator Causador"))
            
        descricao = st.text_area("Descrição Breve do Incidente")
        st.markdown("---")
        st.subheader("Dados do Relator (Opcional)")
        col3, col4 = st.columns(2)
        with col3:
            relator = st.text_input("Nome de quem está reportando")
        with col4:
            funcao = st.text_input("Função (ex: Enfermeiro, Médico)")
        
        submit = st.form_submit_button("📤 Enviar Notificação")
        
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
            st.success("✅ Incidente registrado com sucesso! Agradecemos sua colaboração.")
            st.balloons()

# ---------------------------------------------------------
# MÓDULO 2: VISÃO DA GESTÃO (COM AUTENTICAÇÃO DUPLA)
# ---------------------------------------------------------
if modo_gestao:
    # Remove menus nativos para manter a estética corporativa
    st.markdown("""<style>#MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)
    
    st.sidebar.title("🔐 Login de Gestão")
    usuario_digitado = st.sidebar.text_input("👤 Usuário")
    senha_digitada = st.sidebar.text_input("🔑 Senha", type="password")
    
    # Validação de credenciais organizadas
    if usuario_digitado != "admin" or senha_digitada != "admin123":
        st.title("🔒 Área Restrita - Núcleo de Segurança")
        st.warning("Insira suas credenciais de administrador na barra lateral esquerda para visualizar os relatórios.")
        st.stop()
        
    # Se passar pelo login, o restante da barra lateral de navegação é liberado
    st.sidebar.markdown("---")
    menu_gestao = st.sidebar.radio("Navegação:", ["📊 Painel de Indicadores", "⚙️ Configurações"])
    
    if menu_gestao == "📊 Painel de Indicadores":
        st.title("📊 Dashboard de Segurança do Paciente")
        st.markdown(f"[🔗 Abrir Planilha Base de Dados Completa no Google Sheets]({GOOGLE_SHEET_URL})")
        
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

    elif menu_gestao == "⚙️ Configurações":
        st.title("⚙️ Configuração de Tabelas")
        tabelas_disponiveis = df_config["Tabela"].unique()
        tabela_selecionada = st.selectbox("Selecione o Menu que deseja configurar:", tabelas_disponiveis)
        
        df_filtro = df_config[df_config["Tabela"] == tabela_selecionada].copy()
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"Gerenciar opções de: {tabela_selecionada}")
            df_editado = st.data_editor(
                df_filtro,
                column_config={"Ativo": st.column_config.CheckboxColumn("Ativo (Mostrar)?", default=True), "Tabela": None},
                disabled=["Opcao"], hide_index=True, use_container_width=True
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
