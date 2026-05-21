import streamlit as st
import pandas as pd
import os
from datetime import datetime
import altair as alt

# Configuração da página (Garante que a barra lateral comece fechada/oculta)
st.set_page_config(page_title="Gestão de Incidentes - HGMF", layout="wide", initial_sidebar_state="collapsed")

# Nomes dos arquivos de banco de dados locais
CONFIG_FILE = "config_tabelas.csv"
USERS_FILE = "config_usuarios.csv"

# =====================================================================
# ⚠️ ADICIONE O LINK DA SUA PLANILHA GOOGLE DISPONÍVEL PARA EDIÇÃO AQUI
# =====================================================================
GOOGLE_SHEET_URL = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA_DO_GOOGLE"

# ---------------------------------------------------------
# FUNÇÕES DE BANCO DE DADOS E CARREGAMENTO
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

def load_users():
    """Carrega ou inicializa a tabela de usuários e permissões corporativas"""
    if not os.path.exists(USERS_FILE):
        usuarios_padrao = [
            {"Usuario": "admin", "Senha": "admin123", "Permissao": "Acesso Total"}
        ]
        df_usr = pd.DataFrame(usuarios_padrao)
        df_usr.to_csv(USERS_FILE, index=False)
        return df_usr
    return pd.read_csv(USERS_FILE)

def get_opcoes_ativas(df_conf, nome_tabela):
    opcoes = df_conf[(df_conf["Tabela"] == nome_tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return opcoes if opcoes else ["Nenhuma opção ativa"]

# Inicializar bases
df_config = load_config()
df_dados = load_data()
df_usuarios = load_users()

# Usar Session State do Streamlit para controlar se a pessoa está logada
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "usuario_ativo" not in st.session_state:
    st.session_state["usuario_ativo"] = ""
if "permissao_ativa" not in st.session_state:
    st.session_state["permissao_ativa"] = ""
if "quero_fazer_login" not in st.session_state:
    st.session_state["quero_fazer_login"] = False

# ---------------------------------------------------------
# 🛡️ CONTROLE RESTRITO DE EXIBIÇÃO DA NAVBAR LATERAL
# ---------------------------------------------------------
# Se o usuário NÃO está tentando fazer login e NÃO está logado, a barra lateral some por completo!
if not st.session_state["quero_fazer_login"] and not st.session_state["logado"]:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none !important;}
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
else:
    # Se ele clicou para logar, mantém apenas as ferramentas escondidas, mas mostra a navbar
    st.markdown("""<style>#MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MÓDULO 1: FORMULÁRIO PÚBLICO (ABRE DIRETO NO QR CODE)
# ---------------------------------------------------------
if not st.session_state["logado"]:
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

    st.markdown("---")
    # Botão discreto no rodapé que ativa a barra lateral para fazer o login
    if st.button("🔐 Área Restrita (Gestão)"):
        st.session_state["quero_fazer_login"] = True
        st.rerun()

# ---------------------------------------------------------
# TELA DE LOGIN NA BARRA LATERAL (APENAS QUANDO SOLICITADA)
# ---------------------------------------------------------
if st.session_state["quero_fazer_login"] and not st.session_state["logado"]:
    st.sidebar.title("🔒 Autenticação de Gestão")
    usuario = st.sidebar.text_input("👤 Usuário")
    senha = st.sidebar.text_input("🔑 Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        # Validar credenciais contra a tabela de usuários cadastrados
        validacao = df_usuarios[(df_usuarios["Usuario"] == usuario) & (df_usuarios["Senha"] == senha)]
        
        if not validacao.empty:
            st.session_state["logado"] = True
            st.session_state["usuario_ativo"] = usuario
            st.session_state["permissao_ativa"] = validacao.iloc[0]["Permissao"]
            st.session_state["quero_fazer_login"] = False
            st.sidebar.success("Login efetuado!")
            st.rerun()
        else:
            st.sidebar.error("❌ Usuário ou Senha inválidos!")
            
    if st.sidebar.button("❌ Cancelar e Voltar"):
        st.session_state["quero_fazer_login"] = False
        st.rerun()

# ---------------------------------------------------------
# MÓDULO 2: ÁREA ADMINISTRATIVA COMPLETA (BLOQUEADA POR LOGIN)
# ---------------------------------------------------------
if st.session_state["logado"]:
    st.sidebar.title(f"Olá, {st.session_state['usuario_ativo']}!")
    st.sidebar.info(f"Nível: {st.session_state['permissao_ativa']}")
    
    # Menu dinâmico baseado na permissão do usuário logado
    opcoes_menu = []
    if st.session_state["permissao_ativa"] in ["Acesso Total", "Apenas Relatórios"]:
        opcoes_menu.append("📊 Painel de Indicadores")
    if st.session_state["permissao_ativa"] in ["Acesso Total", "Apenas Configurar Tabelas"]:
        opcoes_menu.append("⚙️ Configuração de Tabelas")
        opcoes_menu.append("👥 Gerenciar Usuários")
        
    menu_gestao = st.sidebar.radio("Navegação Administrativa:", opcoes_menu)
    
    if st.sidebar.button("🚪 Sair do Sistema (Logout)"):
        st.session_state["logado"] = False
        st.session_state["usuario_ativo"] = ""
        st.session_state["permissao_ativa"] = ""
        st.rerun()

    # --- SUBMÓDULO: DASHBOARD ---
    if menu_gestao == "📊 Painel de Indicadores":
        st.title("📊 Dashboard de Segurança do Paciente")
        st.markdown(f"[🔗 Abrir Planilha Base de Dados Completa no Google Sheets]({GOOGLE_SHEET_URL})")
        
        if df_dados.empty:
            st.info("Ainda não existem dados de incidentes registrados.")
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

    # --- SUBMÓDULO: CONFIGURAÇÃO DE MENUS ---
    elif menu_gestao == "⚙️ Configuração de Tabelas":
        st.title("⚙️ Configuração de Tabelas dos Menus")
        tabelas_disponiveis = df_config["Tabela"].unique()
        tabela_selecionada = st.selectbox("Selecione o Menu que deseja configurar:", tabelas_disponiveis)
        
        df_filtro = df_config[df_config["Tabela"] == tabela_selecionada].copy()
        col1, col2 = st.columns([2, 1])
        
        with col1:
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
                        st.success("✅ Adicionado!")
                        st.rerun()

    # --- SUBMÓDULO: GERENCIADOR DE USUÁRIOS E PERMISSÕES (NOVO) ---
    elif menu_gestao == "👥 Gerenciar Usuários":
        st.title("👥 Controle de Usuários e Permissões Corporativas")
        
        col_u1, col_u2 = st.columns([2, 1])
        
        with col_u1:
            st.subheader("Lista de Usuários Cadastrados")
            # Mostra todos os usuários e senhas atuais para a gestão controlar
            st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
            st.warning("⚠️ O usuário padrão 'admin' com 'Acesso Total' não deve ser apagado para evitar bloqueios permanentes.")
            
        with col_u2:
            st.subheader("➕ Cadastrar Novo Usuário")
            novo_user = st.text_input("Nome do Usuário (Sem espaços)")
            nova_senha = st.text_input("Senha do Usuário", type="password")
            permissao = st.selectbox("Nível de Permissão", ["Acesso Total", "Apenas Relatórios", "Apenas Configurar Tabelas"])
            
            if st.button("💾 Salvar Usuário"):
                if novo_user.strip() == "" or nova_senha.strip() == "":
                    st.error("Usuário e Senha são obrigatórios!")
                else:
                    # Evitar duplicados
                    if (df_usuarios["Usuario"].str.lower() == novo_user.strip().lower()).any():
                        st.error("Este nome de usuário já existe!")
                    else:
                        novo_usr_dict = {"Usuario": novo_user.strip(), "Senha": nova_senha, "Permissao": permissao}
                        df_usuarios = pd.concat([df_usuarios, pd.DataFrame([novo_usr_dict])], ignore_index=True)
                        df_usuarios.to_csv(USERS_FILE, index=False)
                        st.success(f"✅ Usuário '{novo_user}' cadastrado com sucesso!")
                        st.rerun()
