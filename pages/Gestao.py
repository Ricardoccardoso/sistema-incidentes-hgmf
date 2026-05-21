import streamlit as st
import pandas as pd
import os
import altair as alt

st.set_page_config(page_title="Painel de Gestão - HGMF", layout="wide", initial_sidebar_state="expanded")

# Esconde opções do desenvolvedor e o menu lateral do Streamlit
st.markdown("""
    <style>
    [data-testid="stAppDeployButton"] {display: none !important;}
    [data-testid="stHeader"] {display: none !important; visibility: hidden !important;}
    header {display: none !important; visibility: hidden !important;}
    [data-testid="stDecoration"] {display: none !important;}
    footer {display: none !important;}
    [data-testid="stSidebarNav"] {display: none !important;} 
    </style>
""", unsafe_allow_html=True)

CONFIG_FILE = "config_tabelas.csv"
USERS_FILE = "config_usuarios.csv"

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
        opcoes_padrao = [{"Tabela": "Gravidade", "Opcao": "Sem Dano", "Ativo": True}] # Resumido para segurança
        df_conf = pd.DataFrame(opcoes_padrao)
        df_conf.to_csv(CONFIG_FILE, index=False)
        return df_conf
    return pd.read_csv(CONFIG_FILE)

def load_users():
    if not os.path.exists(USERS_FILE):
        df_usr = pd.DataFrame([{"Usuario": "admin", "Senha": "admin123", "Permissao": "Acesso Total"}])
        df_usr.to_csv(USERS_FILE, index=False)
        return df_usr
    return pd.read_csv(USERS_FILE)

df_config = load_config()
df_dados = load_data()
df_usuarios = load_users()

if "admin_logado" not in st.session_state:
    st.session_state["admin_logado"] = False

if not st.session_state["admin_logado"]:
    st.title("🔒 Núcleo de Segurança - Painel de Controle")
    st.subheader("Autenticação Administrativa")
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("login_admin"):
            input_user = st.text_input("👤 Usuário")
            input_senha = st.text_input("🔑 Senha", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_login:
                validacao = df_usuarios[(df_usuarios["Usuario"] == input_user) & (df_usuarios["Senha"] == input_senha)]
                if not validacao.empty:
                    st.session_state["admin_logado"] = True
                    st.session_state["user_nome"] = input_user
                    st.session_state["user_permissao"] = validacao.iloc[0]["Permissao"]
                    st.success("Acesso liberado!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou Senha incorretos.")
else:
    st.sidebar.title(f"👤 {st.session_state['user_nome']}")
    st.sidebar.markdown(f"Nível: `{st.session_state['user_permissao']}`")
    st.sidebar.markdown("---")
    
    abas_disponiveis = []
    if st.session_state["user_permissao"] in ["Acesso Total", "Apenas Relatórios"]:
        abas_disponiveis.append("📊 Painel de Indicadores")
    if st.session_state["user_permissao"] in ["Acesso Total", "Apenas Configurar Tabelas"]:
        abas_disponiveis.append("⚙️ Configuração de Tabelas")
        abas_disponiveis.append("👥 Gerenciar Usuários")
        
    menu_gestao = st.sidebar.radio("Navegação do Sistema", abas_disponiveis)
    
    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
        st.session_state["admin_logado"] = False
        st.rerun()

    # --- ABA 1: DASHBOARD ---
    if menu_gestao == "📊 Painel de Indicadores":
        st.title("📊 Painel Gerencial de Incidentes")
        st.markdown(f"[🔗 Abrir Planilha Base de Dados Completa no Google Sheets]({GOOGLE_SHEET_URL})")
        
        if df_dados.empty:
            st.info("Nenhum dado registrado.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Notificações", len(df_dados))
            c2.metric("Incidentes Sem Dano", len(df_dados[df_dados["Gravidade"] == "Sem Dano"]))
            c3.metric("Total de LPP", len(df_dados[df_dados["Categoria_Incidente"] == "Lesão por Pressão (LPP)"]))
            c4.metric("Total de Quedas", len(df_dados[df_dados["Categoria_Incidente"] == "Queda do Paciente"]))
            
            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Gravidade dos Danos")
                df_g = df_dados["Gravidade"].value_counts().reset_index()
                df_g.columns = ["Gravidade", "Qtd"]
                pizza = alt.Chart(df_g).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="Qtd", type="quantitative"),
                    color=alt.Color(field="Gravidade", type="nominal"),
                    tooltip=["Gravidade", "Qtd"]
                ).properties(height=300)
                st.altair_chart(pizza, use_container_width=True)
            with g2:
                st.subheader("Incidentes por Categoria")
                st.bar_chart(df_dados["Categoria_Incidente"].value_counts())

    # --- ABA 2: CONFIGURAÇÕES ---
    elif menu_gestao == "⚙️ Configuração de Tabelas":
        st.title("⚙️ Gerenciar Opções dos Menus")
        lista_tabelas = df_config["Tabela"].unique()
        tab_sel = st.selectbox("Escolha o menu para editar:", lista_tabelas)
        
        df_f = df_config[df_config["Tabela"] == tab_sel].copy()
        col_t1, col_t2 = st.columns([2, 1])
        
        with col_t1:
            df_ed = st.data_editor(df_f, column_config={"Ativo": st.column_config.CheckboxColumn("Ativo?"), "Tabela": None}, disabled=["Opcao"], hide_index=True, use_container_width=True)
            if st.button("💾 Gravar Alterações"):
                for _, r in df_ed.iterrows():
                    mask = (df_config["Tabela"] == tab_sel) & (df_config["Opcao"] == r["Opcao"])
                    df_config.loc[mask, "Ativo"] = r["Ativo"]
                df_config.to_csv(CONFIG_FILE, index=False)
                st.success("Atualizado!")
                st.rerun()
        with col_t2:
            st.subheader("➕ Novo Item")
            n_op = st.text_input("Nome da nova opção:")
            if st.button("Adicionar Item"):
                if n_op.strip() != "":
                    if not ((df_config["Tabela"] == tab_sel) & (df_config["Opcao"].str.lower() == n_op.strip().lower())).any():
                        new_r = {"Tabela": tab_sel, "Opcao": n_op.strip(), "Ativo": True}
                        df_config = pd.concat([df_config, pd.DataFrame([new_r])], ignore_index=True)
                        df_config.to_csv(CONFIG_FILE, index=False)
                        st.success("Adicionado!")
                        st.rerun()

    # --- ABA 3: USUÁRIOS ---
    elif menu_gestao == "👥 Gerenciar Usuários":
        st.title("👥 Controle de Usuários")
        cu1, cu2 = st.columns([2, 1])
        with cu1:
            st.subheader("Usuários Ativos")
            st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
        with cu2:
            st.subheader("➕ Criar Novo Perfil")
            n_user = st.text_input("Login (Sem espaços)")
            n_senha = st.text_input("Senha", type="password")
            n_perm = st.selectbox("Permissão", ["Acesso Total", "Apenas Relatórios", "Apenas Configurar Tabelas"])
            
            if st.button("Gravar Usuário"):
                if n_user.strip() != "" and n_senha.strip() != "":
                    if not (df_usuarios["Usuario"].str.lower() == n_user.strip().lower()).any():
                        df_usuarios = pd.concat([df_usuarios, pd.DataFrame([{"Usuario": n_user.strip(), "Senha": n_senha, "Permissao": n_perm}])], ignore_index=True)
                        df_usuarios.to_csv(USERS_FILE, index=False)
                        st.success("Criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Este login já existe!")
