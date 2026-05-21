import streamlit as st
import pandas as pd
import os
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Painel de Gestão - HGMF", layout="wide", initial_sidebar_state="expanded")

# Oculta elementos do Streamlit sem esconder o sidebar (necessário para a navegação interna)
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
DATA_FILE = "dados_backup_nuvem.csv"

# =====================================================================
GOOGLE_SHEET_URL = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA_DO_GOOGLE"
# =====================================================================

def load_data():
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
            {"Tabela": "Gravidade", "Opcao": "Dano Moderado", "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Dano Grave", "Ativo": True},
            {"Tabela": "Gravidade", "Opcao": "Óbito", "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Déficit de pessoal / Sobrecarga", "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha na comunicação", "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha no processo / protocolo", "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Ambiente / Infraestrutura", "Ativo": True},
            {"Tabela": "Fator Causador", "Opcao": "Falha de equipamento", "Ativo": True},
        ]
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

# ---- INICIALIZAÇÃO DE ESTADO ----
if "admin_logado" not in st.session_state:
    st.session_state["admin_logado"] = False
if "user_nome" not in st.session_state:
    st.session_state["user_nome"] = ""
if "user_permissao" not in st.session_state:
    st.session_state["user_permissao"] = ""

df_usuarios = load_users()

# ==================================================================
# TELA DE LOGIN
# ==================================================================
if not st.session_state["admin_logado"]:
    st.title("🔒 Núcleo de Segurança — Painel de Controle")
    st.subheader("Autenticação Administrativa")
    st.markdown("---")

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("login_admin"):
            input_user = st.text_input("👤 Usuário")
            input_senha = st.text_input("🔑 Senha", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)

            if btn_login:
                validacao = df_usuarios[
                    (df_usuarios["Usuario"] == input_user) &
                    (df_usuarios["Senha"] == input_senha)
                ]
                if not validacao.empty:
                    st.session_state["admin_logado"] = True
                    st.session_state["user_nome"] = input_user
                    st.session_state["user_permissao"] = validacao.iloc[0]["Permissao"]
                    st.success("✅ Acesso liberado!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou Senha incorretos.")

    st.markdown("---")
    st.page_link("app.py", label="← Voltar ao Formulário de Notificação", icon="🏥")

# ==================================================================
# PAINEL APÓS LOGIN
# ==================================================================
else:
    df_config = load_config()
    df_dados = load_data()

    # ---- SIDEBAR ----
    with st.sidebar:
        st.title(f"👤 {st.session_state['user_nome']}")
        st.markdown(f"**Nível:** `{st.session_state['user_permissao']}`")
        st.markdown("---")

        abas_disponiveis = []
        if st.session_state["user_permissao"] in ["Acesso Total", "Apenas Relatórios"]:
            abas_disponiveis.append("📊 Painel de Indicadores")
            abas_disponiveis.append("📋 Registros Completos")
        if st.session_state["user_permissao"] in ["Acesso Total", "Apenas Configurar Tabelas"]:
            abas_disponiveis.append("⚙️ Configuração de Tabelas")
            abas_disponiveis.append("👥 Gerenciar Usuários")

        menu_gestao = st.radio("Navegação", abas_disponiveis)
        st.markdown("---")
        st.page_link("app.py", label="🏥 Formulário Público", icon="↩️")
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            st.session_state["admin_logado"] = False
            st.session_state["user_nome"] = ""
            st.session_state["user_permissao"] = ""
            st.rerun()

    # ==================================================================
    # ABA 1: PAINEL DE INDICADORES
    # ==================================================================
    if menu_gestao == "📊 Painel de Indicadores":
        st.title("📊 Painel Gerencial de Incidentes")
        if GOOGLE_SHEET_URL != "COLE_AQUI_O_LINK_DA_SUA_PLANILHA_DO_GOOGLE":
            st.markdown(f"[🔗 Abrir Base de Dados no Google Sheets]({GOOGLE_SHEET_URL})")

        if df_dados.empty:
            st.info("ℹ️ Nenhum dado registrado até o momento.")
        else:
            # ---- FILTROS ----
            with st.expander("🔎 Filtros", expanded=False):
                f1, f2, f3 = st.columns(3)
                with f1:
                    setor_filtro = st.multiselect("Setor", df_dados["Setor"].dropna().unique().tolist())
                with f2:
                    grav_filtro = st.multiselect("Gravidade", df_dados["Gravidade"].dropna().unique().tolist())
                with f3:
                    cat_filtro = st.multiselect("Categoria", df_dados["Categoria_Incidente"].dropna().unique().tolist())

            df_filtrado = df_dados.copy()
            if setor_filtro:
                df_filtrado = df_filtrado[df_filtrado["Setor"].isin(setor_filtro)]
            if grav_filtro:
                df_filtrado = df_filtrado[df_filtrado["Gravidade"].isin(grav_filtro)]
            if cat_filtro:
                df_filtrado = df_filtrado[df_filtrado["Categoria_Incidente"].isin(cat_filtro)]

            # ---- MÉTRICAS ----
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("📋 Total de Notificações", len(df_filtrado))
            c2.metric("✅ Sem Dano", len(df_filtrado[df_filtrado["Gravidade"] == "Sem Dano"]))
            c3.metric("⚠️ Dano Leve/Moderado", len(df_filtrado[df_filtrado["Gravidade"].isin(["Dano Leve", "Dano Moderado"])]))
            c4.metric("🩹 LPP", len(df_filtrado[df_filtrado["Categoria_Incidente"] == "Lesão por Pressão (LPP)"]))
            c5.metric("🚶 Quedas", len(df_filtrado[df_filtrado["Categoria_Incidente"] == "Queda do Paciente"]))

            st.markdown("---")

            # ---- GRÁFICOS ----
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Gravidade dos Danos")
                df_g = df_filtrado["Gravidade"].value_counts().reset_index()
                df_g.columns = ["Gravidade", "Qtd"]
                pizza = alt.Chart(df_g).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="Qtd", type="quantitative"),
                    color=alt.Color(field="Gravidade", type="nominal"),
                    tooltip=["Gravidade", "Qtd"]
                ).properties(height=300)
                st.altair_chart(pizza, use_container_width=True)

            with g2:
                st.subheader("Incidentes por Categoria")
                df_cat = df_filtrado["Categoria_Incidente"].value_counts().reset_index()
                df_cat.columns = ["Categoria", "Qtd"]
                bar = alt.Chart(df_cat).mark_bar().encode(
                    x=alt.X("Qtd:Q"),
                    y=alt.Y("Categoria:N", sort="-x"),
                    color=alt.Color("Categoria:N", legend=None),
                    tooltip=["Categoria", "Qtd"]
                ).properties(height=300)
                st.altair_chart(bar, use_container_width=True)

            g3, g4 = st.columns(2)
            with g3:
                st.subheader("Incidentes por Setor")
                df_set = df_filtrado["Setor"].value_counts().reset_index()
                df_set.columns = ["Setor", "Qtd"]
                bar2 = alt.Chart(df_set).mark_bar().encode(
                    x=alt.X("Qtd:Q"),
                    y=alt.Y("Setor:N", sort="-x"),
                    tooltip=["Setor", "Qtd"]
                ).properties(height=250)
                st.altair_chart(bar2, use_container_width=True)

            with g4:
                st.subheader("Incidentes por Turno")
                df_turno = df_filtrado["Turno"].value_counts().reset_index()
                df_turno.columns = ["Turno", "Qtd"]
                bar3 = alt.Chart(df_turno).mark_bar().encode(
                    x=alt.X("Turno:N"),
                    y=alt.Y("Qtd:Q"),
                    color=alt.Color("Turno:N", legend=None),
                    tooltip=["Turno", "Qtd"]
                ).properties(height=250)
                st.altair_chart(bar3, use_container_width=True)

    # ==================================================================
    # ABA 2: REGISTROS COMPLETOS
    # ==================================================================
    elif menu_gestao == "📋 Registros Completos":
        st.title("📋 Registros de Incidentes")

        if df_dados.empty:
            st.info("Nenhum dado registrado.")
        else:
            st.dataframe(df_dados, use_container_width=True, hide_index=True)

            # ---- EXPORTAR CSV ----
            csv = df_dados.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Baixar Base de Dados (.csv)",
                data=csv,
                file_name=f"incidentes_HGMF_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

            # ---- EXCLUIR REGISTRO ----
            if st.session_state["user_permissao"] == "Acesso Total":
                st.markdown("---")
                st.subheader("🗑️ Excluir Registro")
                idx_excluir = st.number_input("Número da linha a excluir (índice):", min_value=0, max_value=len(df_dados)-1, step=1)
                if st.button("Excluir Linha Selecionada", type="primary"):
                    df_dados = df_dados.drop(index=idx_excluir).reset_index(drop=True)
                    df_dados.to_csv(DATA_FILE, index=False)
                    st.success("Registro excluído.")
                    st.rerun()

    # ==================================================================
    # ABA 3: CONFIGURAÇÃO DE TABELAS
    # ==================================================================
    elif menu_gestao == "⚙️ Configuração de Tabelas":
        st.title("⚙️ Gerenciar Opções dos Menus")
        lista_tabelas = df_config["Tabela"].unique()
        tab_sel = st.selectbox("Escolha o menu para editar:", lista_tabelas)

        df_f = df_config[df_config["Tabela"] == tab_sel].copy()
        col_t1, col_t2 = st.columns([2, 1])

        with col_t1:
            st.subheader("Opções existentes")
            df_ed = st.data_editor(
                df_f,
                column_config={
                    "Ativo": st.column_config.CheckboxColumn("Ativo?"),
                    "Tabela": None
                },
                disabled=["Opcao"],
                hide_index=True,
                use_container_width=True
            )
            if st.button("💾 Gravar Alterações"):
                for _, r in df_ed.iterrows():
                    mask = (df_config["Tabela"] == tab_sel) & (df_config["Opcao"] == r["Opcao"])
                    df_config.loc[mask, "Ativo"] = r["Ativo"]
                df_config.to_csv(CONFIG_FILE, index=False)
                st.success("✅ Configurações atualizadas!")
                st.rerun()

        with col_t2:
            st.subheader("➕ Novo Item")
            n_op = st.text_input("Nome da nova opção:")
            if st.button("Adicionar Item", use_container_width=True):
                if n_op.strip():
                    duplicado = ((df_config["Tabela"] == tab_sel) &
                                 (df_config["Opcao"].str.lower() == n_op.strip().lower())).any()
                    if not duplicado:
                        new_r = {"Tabela": tab_sel, "Opcao": n_op.strip(), "Ativo": True}
                        df_config = pd.concat([df_config, pd.DataFrame([new_r])], ignore_index=True)
                        df_config.to_csv(CONFIG_FILE, index=False)
                        st.success("✅ Item adicionado!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Esta opção já existe.")
                else:
                    st.warning("Digite um nome para a opção.")

    # ==================================================================
    # ABA 4: GERENCIAR USUÁRIOS
    # ==================================================================
    elif menu_gestao == "👥 Gerenciar Usuários":
        st.title("👥 Controle de Usuários")
        cu1, cu2 = st.columns([2, 1])

        with cu1:
            st.subheader("Usuários Ativos")
            # Oculta a senha na exibição
            df_exibir = df_usuarios.copy()
            df_exibir["Senha"] = "••••••••"
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)

        with cu2:
            st.subheader("➕ Criar Novo Perfil")
            n_user = st.text_input("Login (sem espaços)")
            n_senha = st.text_input("Senha", type="password")
            n_perm = st.selectbox("Permissão", ["Acesso Total", "Apenas Relatórios", "Apenas Configurar Tabelas"])

            if st.button("Gravar Usuário", use_container_width=True):
                if n_user.strip() and n_senha.strip():
                    if not (df_usuarios["Usuario"].str.lower() == n_user.strip().lower()).any():
                        df_usuarios = pd.concat([
                            df_usuarios,
                            pd.DataFrame([{"Usuario": n_user.strip(), "Senha": n_senha, "Permissao": n_perm}])
                        ], ignore_index=True)
                        df_usuarios.to_csv(USERS_FILE, index=False)
                        st.success("✅ Usuário criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Este login já existe!")
                else:
                    st.warning("⚠️ Preencha login e senha.")

            st.markdown("---")
            st.subheader("🗑️ Remover Usuário")
            usuarios_lista = df_usuarios[df_usuarios["Usuario"] != st.session_state["user_nome"]]["Usuario"].tolist()
            if usuarios_lista:
                user_del = st.selectbox("Selecione o usuário:", usuarios_lista)
                if st.button("Remover Usuário", type="primary"):
                    df_usuarios = df_usuarios[df_usuarios["Usuario"] != user_del].reset_index(drop=True)
                    df_usuarios.to_csv(USERS_FILE, index=False)
                    st.success(f"✅ Usuário '{user_del}' removido.")
                    st.rerun()
            else:
                st.info("Não há outros usuários para remover.")
