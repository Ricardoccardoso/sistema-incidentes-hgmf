import streamlit as st
import pandas as pd
import os
import altair as alt

st.set_page_config(page_title="Painel de Gestão", layout="wide")

# Remove apenas os botões de edição do Streamlit, mas MANTÉM a barra lateral
st.markdown("""
    <style>
    [data-testid="stAppDeployButton"] {display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    footer {display: none !important;}
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
        df = pd.DataFrame(columns=["Data_Registro", "Data_Incidente", "Turno", "Setor", "Cama_Leito", "Tipo_Geral", "Categoria_Incidente", "Medicamento_Envolvido", "Gravidade", "Fatores_Causadores", "Descricao", "Relator", "Funcao_Relator"])
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
    return pd.read_csv(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else pd.DataFrame([{"Tabela": "Gravidade", "Opcao": "Sem Dano", "Ativo": True}])

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
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("login_admin"):
            input_user = st.text_input("👤 Usuário")
            input_senha = st.text_input("🔑 Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                validacao = df_usuarios[(df_usuarios["Usuario"] == input_user) & (df_usuarios["Senha"] == input_senha)]
                if not validacao.empty:
                    st.session_state["admin_logado"] = True
                    st.session_state["user_nome"] = input_user
                    st.session_state["user_permissao"] = validacao.iloc[0]["Permissao"]
                    st.rerun()
                else:
                    st.error("Credenciais incorretas.")
else:
    st.sidebar.title(f"👤 {st.session_state['user_nome']}")
    st.sidebar.markdown(f"Nível: `{st.session_state['user_permissao']}`")
    st.sidebar.markdown("---")
    
    abas = []
    if st.session_state["user_permissao"] in ["Acesso Total", "Apenas Relatórios"]:
        abas.append("📊 Indicadores")
    if st.session_state["user_permissao"] in ["Acesso Total", "Apenas Configurar Tabelas"]:
        abas.append("⚙️ Tabelas")
        abas.append("👥 Usuários")
        
    menu = st.sidebar.radio("Navegação", abas)
    
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state["admin_logado"] = False
        st.rerun()

    if menu == "📊 Indicadores":
        st.title("📊 Indicadores de Segurança")
        st.markdown(f"[Abrir Planilha Base]({GOOGLE_SHEET_URL})")
        
        if not df_dados.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Notificações", len(df_dados))
            c2.metric("Sem Dano", len(df_dados[df_dados["Gravidade"] == "Sem Dano"]))
            c3.metric("LPP", len(df_dados[df_dados["Categoria_Incidente"] == "Lesão por Pressão (LPP)"]))
            c4.metric("Quedas", len(df_dados[df_dados["Categoria_Incidente"] == "Queda do Paciente"]))
            
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Gravidade")
                df_g = df_dados["Gravidade"].value_counts().reset_index()
                df_g.columns = ["Gravidade", "Qtd"]
                st.altair_chart(alt.Chart(df_g).mark_arc(innerRadius=50).encode(theta="Qtd", color="Gravidade"), use_container_width=True)
            with g2:
                st.subheader("Categorias")
                st.bar_chart(df_dados["Categoria_Incidente"].value_counts())

    elif menu == "⚙️ Tabelas":
        st.title("⚙️ Gerenciar Menus")
        tab_sel = st.selectbox("Escolha o menu:", df_config["Tabela"].unique())
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            df_ed = st.data_editor(df_config[df_config["Tabela"] == tab_sel].copy(), column_config={"Ativo": st.column_config.CheckboxColumn("Ativo?")}, disabled=["Opcao"], hide_index=True)
            if st.button("Gravar Alterações"):
                for _, r in df_ed.iterrows():
                    df_config.loc[(df_config["Tabela"] == tab_sel) & (df_config["Opcao"] == r["Opcao"]), "Ativo"] = r["Ativo"]
                df_config.to_csv(CONFIG_FILE, index=False)
                st.success("Atualizado!")
                st.rerun()
        with col_t2:
            n_op = st.text_input("Nova Opção:")
            if st.button("Adicionar") and n_op:
                df_config = pd.concat([df_config, pd.DataFrame([{"Tabela": tab_sel, "Opcao": n_op.strip(), "Ativo": True}])], ignore_index=True)
                df_config.to_csv(CONFIG_FILE, index=False)
                st.success("Adicionado!")
                st.rerun()

    elif menu == "👥 Usuários":
        st.title("👥 Usuários do Sistema")
        col_u1, col_u2 = st.columns([2, 1])
        with col_u1:
            st.dataframe(df_usuarios, hide_index=True, use_container_width=True)
        with col_u2:
            n_user = st.text_input("Login")
            n_senha = st.text_input("Senha", type="password")
            n_perm = st.selectbox("Permissão", ["Acesso Total", "Apenas Relatórios", "Apenas Configurar Tabelas"])
            if st.button("Criar Usuário") and n_user and n_senha:
                df_usuarios = pd.concat([df_usuarios, pd.DataFrame([{"Usuario": n_user.strip(), "Senha": n_senha, "Permissao": n_perm}])], ignore_index=True)
                df_usuarios.to_csv(USERS_FILE, index=False)
                st.success("Criado!")
                st.rerun()
