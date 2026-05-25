import streamlit as st
import pandas as pd
import altair as alt
import hashlib
from datetime import datetime, date, timedelta
import io
import db  # camada de acesso ao Supabase

st.set_page_config(
    page_title="Painel de Gestão — HGMF",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

[data-testid="stAppDeployButton"] {display:none !important;}
[data-testid="stHeader"]          {display:none !important; visibility:hidden !important;}
header                            {display:none !important; visibility:hidden !important;}
[data-testid="stDecoration"]      {display:none !important;}
footer                            {display:none !important;}
[data-testid="stSidebarNav"]      {display:none !important;}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a2744 0%, #0d3461 100%) !important;
}
[data-testid="stSidebar"] * { color: #e3f2fd !important; }
[data-testid="stSidebar"] .stRadio label { 
    font-size: 0.88rem !important; 
    padding: 6px 0 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #fff !important; }

/* Métricas */
[data-testid="metric-container"] {
    background: #f8faff;
    border: 1px solid #e3eaff;
    border-radius: 12px;
    padding: 18px 20px !important;
    box-shadow: 0 2px 8px rgba(13,71,161,0.06);
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: #0d47a1 !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #546e7a !important;
}

/* Cartão de incidente */
.card-incidente {
    background: #fff;
    border: 1px solid #e8edf5;
    border-left: 4px solid #1976d2;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
}
.card-incidente.grave   { border-left-color: #c62828; }
.card-incidente.moderado{ border-left-color: #e65100; }
.card-incidente.leve    { border-left-color: #f9a825; }
.card-incidente.semDano { border-left-color: #2e7d32; }
.card-incidente.near    { border-left-color: #6a1b9a; }

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.74rem;
    font-weight: 600;
    margin-right: 4px;
}
.badge-novo      { background:#e3f2fd; color:#0d47a1; }
.badge-analise   { background:#fff8e1; color:#f57f17; }
.badge-concluido { background:#e8f5e9; color:#2e7d32; }
.badge-critico   { background:#ffebee; color:#c62828; }

.secao-titulo {
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #1565c0;
    margin: 20px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 2px solid #e3f2fd;
}

div.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
div.stButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #0d47a1, #1976d2) !important;
    color: white !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
SENHA_ADMIN_MESTRE = hashlib.sha256("sp#9198sider".encode()).hexdigest()

COLUNAS_DADOS = [
    "id", "Data_Registro", "Data_Incidente", "Hora_Aproximada", "Turno", "Setor",
    "Cama_Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade", "Dano_Paciente",
    "Paciente_Foi_Comunicado", "Familiar_Foi_Comunicado", "Medico_Foi_Comunicado",
    "Fatores_Causadores", "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Relator", "Funcao_Relator", "Status"
]

STATUS_OPTS    = ["Novo", "Em Análise", "Concluído", "Arquivado"]
PERMISSOES     = ["Acesso Total", "Apenas Relatórios", "Apenas Configurar Tabelas"]

GRAVIDADE_CORES = {
    "Near Miss": "near",
    "Sem Dano":  "semDano",
    "Dano Leve": "leve",
    "Dano Moderado": "moderado",
    "Dano Grave": "grave",
    "Óbito":     "grave",
}

def _cor_gravidade(g: str) -> str:
    for k, v in GRAVIDADE_CORES.items():
        if k.lower() in str(g).lower():
            return v
    return "semDano"

# ─── Funções delegadas ao módulo db ──────────────────────────────────────────
hash_senha  = db.hash_senha
load_data   = db.load_data
load_config = db.load_config
load_users  = db.load_users

def save_data(df):
    """Não mais usado como dump completo. Alterações pontuais usam db.update_incidente."""
    pass

def save_config(df):
    """Compatibilidade: re-salva alterações via db (chamado nos pontos de edição abaixo)."""
    pass

def save_users(df):
    """Compatibilidade: re-salva via db (chamado nos pontos de edição abaixo)."""
    pass

def get_opcoes(df_conf, tabela):
    return db.get_opcoes(df_conf, tabela)

# ─── Session state ────────────────────────────────────────────────────────────
for k, v in {
    "logado": False, "user": "", "permissao": "",
    "tentativas": 0, "bloqueado_ate": None
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── TELA DE LOGIN ────────────────────────────────────────────────────────────
if not st.session_state["logado"]:
    st.markdown("""
    <div style="max-width:400px; margin:60px auto 0 auto;">
      <div style="text-align:center; margin-bottom:28px;">
        <span style="font-size:2.8rem;">🔒</span>
        <h2 style="margin:8px 0 4px; color:#0d47a1; font-weight:700;">Painel de Gestão</h2>
        <p style="color:#546e7a; font-size:0.88rem;">Hospital Geral Menandro de Faria<br>Núcleo de Segurança do Paciente</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        # Bloqueio por tentativas
        bloqueado = False
        if st.session_state["bloqueado_ate"]:
            if datetime.now() < st.session_state["bloqueado_ate"]:
                bloqueado = True
                resto = int((st.session_state["bloqueado_ate"] - datetime.now()).total_seconds())
                st.error(f"🚫 Muitas tentativas. Tente novamente em {resto}s.")
            else:
                st.session_state["bloqueado_ate"] = None
                st.session_state["tentativas"] = 0

        if not bloqueado:
            with st.form("login_form"):
                login    = st.text_input("👤 Usuário")
                senha    = st.text_input("🔑 Senha", type="password")
                entrar   = st.form_submit_button("Entrar no Sistema", use_container_width=True)

                # LOGIN MESTRE (administrador do sistema)
                if entrar:
                    if login.strip() == "admin_master" and hash_senha(senha) == SENHA_ADMIN_MESTRE:
                        st.session_state.update({"logado": True, "user": "admin_master",
                                                  "permissao": "Acesso Total", "tentativas": 0})
                        st.rerun()
                    else:
                        df_usr = load_users()
                        validar = df_usr[
                            (df_usr["Usuario"].str.lower() == login.strip().lower()) &
                            (df_usr["Senha_Hash"] == hash_senha(senha)) &
                            (df_usr["Ativo"] == True)
                        ]
                        if not validar.empty:
                            perm = validar.iloc[0]["Permissao"]
                            st.session_state.update({"logado": True, "user": login.strip(),
                                                      "permissao": perm, "tentativas": 0})
                            st.rerun()
                        else:
                            st.session_state["tentativas"] += 1
                            restantes = 5 - st.session_state["tentativas"]
                            if st.session_state["tentativas"] >= 5:
                                st.session_state["bloqueado_ate"] = datetime.now() + timedelta(minutes=5)
                                st.error("🚫 Conta bloqueada por 5 minutos.")
                            else:
                                st.error(f"❌ Usuário ou senha incorretos. Tentativas restantes: {restantes}")
    st.stop()

# ─── PAINEL AUTENTICADO ───────────────────────────────────────────────────────
df_dados    = load_data()
df_config   = load_config()
df_usuarios = load_users()

perm = st.session_state["permissao"]

# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 8px;">
      <span style="font-size:2rem;">👤</span>
      <p style="font-weight:700; font-size:1rem; margin:4px 0 2px;">{st.session_state['user']}</p>
      <p style="font-size:0.76rem; opacity:0.7; margin:0;">{perm}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    menu_items = []
    if perm in ["Acesso Total", "Apenas Relatórios"]:
        menu_items += ["📊 Dashboard", "📋 Notificações", "📈 Relatórios", "📁 Exportar Dados"]
    if perm in ["Acesso Total", "Apenas Configurar Tabelas"]:
        menu_items += ["⚙️ Configurar Menus", "👥 Usuários"]

    menu = st.radio("Navegação", menu_items, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        for k in ["logado", "user", "permissao"]:
            st.session_state[k] = "" if k != "logado" else False
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ABA: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📊 Dashboard":
    st.title("📊 Dashboard de Indicadores")

    if df_dados.empty:
        st.info("Nenhuma notificação registrada ainda.")
        st.stop()

    # Converter datas
    df_dados["Data_Incidente"] = pd.to_datetime(df_dados["Data_Incidente"], errors="coerce")
    df_dados["Data_Registro"]  = pd.to_datetime(df_dados["Data_Registro"],  errors="coerce")

    # ── Filtro de período ──────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🗓️ Filtro de Período</div>', unsafe_allow_html=True)
    cf1, cf2, cf3 = st.columns([2, 2, 2])
    with cf1:
        data_ini = st.date_input("De", value=(date.today() - timedelta(days=30)))
    with cf2:
        data_fim = st.date_input("Até", value=date.today())
    with cf3:
        filtro_setor = st.selectbox("Setor", ["Todos"] + sorted(df_dados["Setor"].dropna().unique().tolist()))

    df_f = df_dados[
        (df_dados["Data_Incidente"] >= pd.to_datetime(data_ini)) &
        (df_dados["Data_Incidente"] <= pd.to_datetime(data_fim))
    ].copy()
    if filtro_setor != "Todos":
        df_f = df_f[df_f["Setor"] == filtro_setor]

    # ── KPIs ──────────────────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">📌 Indicadores do Período</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Notificações",    len(df_f))
    k2.metric("Near Miss",             len(df_f[df_f["Gravidade"].str.contains("Near", na=False)]))
    k3.metric("Sem Dano",              len(df_f[df_f["Gravidade"].str.contains("Sem Dano", na=False)]))
    k4.metric("Dano Grave / Óbito",    len(df_f[df_f["Gravidade"].str.contains("Grave|Óbito", na=False, regex=True)]))
    k5.metric("LPP",                   len(df_f[df_f["Categoria_Incidente"].str.contains("Pressão", na=False)]))
    k6.metric("Quedas",                len(df_f[df_f["Categoria_Incidente"].str.contains("Queda", na=False)]))

    st.markdown("---")

    # ── Gráficos linha 1 ──────────────────────────────────────────────────
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Incidentes por Gravidade")
        df_grav = df_f["Gravidade"].value_counts().reset_index()
        df_grav.columns = ["Gravidade", "Qtd"]
        chart_grav = alt.Chart(df_grav).mark_arc(innerRadius=55, outerRadius=110).encode(
            theta=alt.Theta("Qtd:Q"),
            color=alt.Color("Gravidade:N", scale=alt.Scale(
                domain=["Near Miss (Quase Evento - não atingiu o paciente)",
                        "Sem Dano (atingiu, sem lesão)",
                        "Dano Leve (lesão leve/temporária)",
                        "Dano Moderado (lesão moderada/temporária)",
                        "Dano Grave (lesão grave/permanente)", "Óbito"],
                range=["#7b1fa2", "#43a047", "#fdd835", "#ff8f00", "#e53935", "#b71c1c"]
            )),
            tooltip=["Gravidade", "Qtd"]
        ).properties(height=280)
        st.altair_chart(chart_grav, use_container_width=True)

    with g2:
        st.subheader("Incidentes por Categoria")
        df_cat = df_f["Categoria_Incidente"].value_counts().reset_index()
        df_cat.columns = ["Categoria", "Qtd"]
        chart_cat = alt.Chart(df_cat).mark_bar(cornerRadiusTopRight=5, cornerRadiusTopLeft=5).encode(
            x=alt.X("Qtd:Q", title="Quantidade"),
            y=alt.Y("Categoria:N", sort="-x", title=""),
            color=alt.value("#1565c0"),
            tooltip=["Categoria", "Qtd"]
        ).properties(height=280)
        st.altair_chart(chart_cat, use_container_width=True)

    # ── Gráficos linha 2 ──────────────────────────────────────────────────
    g3, g4 = st.columns(2)

    with g3:
        st.subheader("Evolução Temporal (por semana)")
        df_tmp = df_f.copy()
        df_tmp["Semana"] = df_tmp["Data_Incidente"].dt.to_period("W").apply(lambda r: str(r.start_time.date()))
        df_sem = df_tmp.groupby("Semana").size().reset_index(name="Qtd")
        chart_sem = alt.Chart(df_sem).mark_line(point=True, strokeWidth=2, color="#1565c0").encode(
            x=alt.X("Semana:O", title="Semana"),
            y=alt.Y("Qtd:Q",   title="Notificações"),
            tooltip=["Semana", "Qtd"]
        ).properties(height=250)
        st.altair_chart(chart_sem, use_container_width=True)

    with g4:
        st.subheader("Incidentes por Setor")
        df_set = df_f["Setor"].value_counts().reset_index()
        df_set.columns = ["Setor", "Qtd"]
        chart_set = alt.Chart(df_set).mark_bar(cornerRadiusTopRight=5, cornerRadiusTopLeft=5).encode(
            x=alt.X("Qtd:Q", title="Quantidade"),
            y=alt.Y("Setor:N", sort="-x", title=""),
            color=alt.value("#0288d1"),
            tooltip=["Setor", "Qtd"]
        ).properties(height=250)
        st.altair_chart(chart_set, use_container_width=True)

    # ── Gráficos linha 3 ──────────────────────────────────────────────────
    g5, g6 = st.columns(2)

    with g5:
        st.subheader("Distribuição por Turno")
        df_turno = df_f["Turno"].value_counts().reset_index()
        df_turno.columns = ["Turno", "Qtd"]
        chart_turno = alt.Chart(df_turno).mark_bar().encode(
            x=alt.X("Turno:N", title=""),
            y=alt.Y("Qtd:Q",   title="Qtd"),
            color=alt.Color("Turno:N", legend=None),
            tooltip=["Turno", "Qtd"]
        ).properties(height=220)
        st.altair_chart(chart_turno, use_container_width=True)

    with g6:
        st.subheader("Fatores Causadores Mais Frequentes")
        if df_f["Fatores_Causadores"].notna().any():
            fatores_todos = df_f["Fatores_Causadores"].dropna().str.split(", ").explode()
            df_fat = fatores_todos.value_counts().head(8).reset_index()
            df_fat.columns = ["Fator", "Qtd"]
            chart_fat = alt.Chart(df_fat).mark_bar(cornerRadiusTopRight=4).encode(
                x=alt.X("Qtd:Q"),
                y=alt.Y("Fator:N", sort="-x"),
                color=alt.value("#6a1b9a"),
                tooltip=["Fator", "Qtd"]
            ).properties(height=240)
            st.altair_chart(chart_fat, use_container_width=True)
        else:
            st.info("Sem dados de fatores causadores.")

    # ── Status das notificações ───────────────────────────────────────────
    if "Status" in df_f.columns:
        st.subheader("Status das Notificações")
        df_status = df_f["Status"].value_counts().reset_index()
        df_status.columns = ["Status", "Qtd"]
        s1, s2, s3, s4 = st.columns(4)
        for col_k, status_n in zip([s1, s2, s3, s4], STATUS_OPTS):
            qtd = int(df_status[df_status["Status"] == status_n]["Qtd"].sum()) if not df_status.empty else 0
            col_k.metric(status_n, qtd)

# ══════════════════════════════════════════════════════════════════════════════
# ABA: NOTIFICAÇÕES (lista e gerenciamento)
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📋 Notificações":
    st.title("📋 Gerenciamento de Notificações")

    if df_dados.empty:
        st.info("Nenhuma notificação registrada.")
        st.stop()

    df_dados["Data_Incidente"] = pd.to_datetime(df_dados["Data_Incidente"], errors="coerce")

    # Filtros
    st.markdown('<div class="secao-titulo">🔎 Filtros</div>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_status = st.selectbox("Status", ["Todos"] + STATUS_OPTS)
    with fc2:
        cats = ["Todas"] + sorted(df_dados["Categoria_Incidente"].dropna().unique().tolist())
        f_cat = st.selectbox("Categoria", cats)
    with fc3:
        setos = ["Todos"] + sorted(df_dados["Setor"].dropna().unique().tolist())
        f_set = st.selectbox("Setor", setos)
    with fc4:
        gravs = ["Todas"] + sorted(df_dados["Gravidade"].dropna().unique().tolist())
        f_grav = st.selectbox("Gravidade", gravs)

    df_view = df_dados.copy()
    if f_status != "Todos":
        df_view = df_view[df_view["Status"] == f_status]
    if f_cat != "Todas":
        df_view = df_view[df_view["Categoria_Incidente"] == f_cat]
    if f_set != "Todos":
        df_view = df_view[df_view["Setor"] == f_set]
    if f_grav != "Todas":
        df_view = df_view[df_view["Gravidade"] == f_grav]

    st.markdown(f"**{len(df_view)}** notificações encontradas")
    st.markdown("---")

    for idx, row in df_view.sort_values("Data_Registro", ascending=False).iterrows():
        cor = _cor_gravidade(str(row.get("Gravidade", "")))
        status_val = str(row.get("Status", "Novo"))
        badge_class = {
            "Novo": "badge-novo", "Em Análise": "badge-analise",
            "Concluído": "badge-concluido", "Arquivado": "badge-critico"
        }.get(status_val, "badge-novo")

        st.markdown(f"""
        <div class="card-incidente {cor}">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
            <div>
              <strong>#{idx+1}</strong> &nbsp;
              <span class="badge badge-novo">{row.get('Categoria_Incidente','—')}</span>
              <span class="badge {badge_class}">{status_val}</span>
            </div>
            <div style="font-size:0.82rem; color:#546e7a;">
              📅 {str(row.get('Data_Incidente',''))[:10]} &nbsp;|&nbsp;
              🏥 {row.get('Setor','—')} &nbsp;|&nbsp;
              ⚠️ {str(row.get('Gravidade',''))[:30]}
            </div>
          </div>
          <p style="margin:8px 0 4px; font-size:0.88rem; color:#37474f;">
            {str(row.get('Descricao',''))[:220]}{"..." if len(str(row.get('Descricao',''))) > 220 else ""}
          </p>
          <div style="font-size:0.78rem; color:#90a4ae;">
            Relator: {row.get('Relator','Anônimo') or 'Anônimo'} — {row.get('Funcao_Relator','') or ''}
            &nbsp;|&nbsp; Registrado em: {str(row.get('Data_Registro',''))[:16]}
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Ver detalhes e gerenciar — Notificação #{idx+1}"):
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Dados do Evento**")
                st.write(f"- Data/Hora: {str(row.get('Data_Incidente',''))[:10]} às {row.get('Hora_Aproximada','')}")
                st.write(f"- Turno: {row.get('Turno','')}")
                st.write(f"- Setor: {row.get('Setor','')} | Leito: {row.get('Cama_Leito','')}")
                st.write(f"- Tipo: {row.get('Tipo_Geral','')}")
                st.write(f"- Categoria: {row.get('Categoria_Incidente','')}")
                if row.get("Subcategoria"):
                    st.write(f"- Subcategoria: {row.get('Subcategoria','')}")
                if row.get("Medicamento_Envolvido"):
                    st.write(f"- Medicamento: {row.get('Medicamento_Envolvido','')}")
            with d2:
                st.markdown("**Gravidade e Comunicação**")
                st.write(f"- Gravidade: {row.get('Gravidade','')}")
                st.write(f"- Dano: {row.get('Dano_Paciente','') or 'Não informado'}")
                st.write(f"- Paciente comunicado: {row.get('Paciente_Foi_Comunicado','')}")
                st.write(f"- Familiar comunicado: {row.get('Familiar_Foi_Comunicado','')}")
                st.write(f"- Médico comunicado: {row.get('Medico_Foi_Comunicado','')}")

            st.markdown("**Fatores Causadores**")
            st.write(row.get("Fatores_Causadores","Não informado") or "Não informado")

            st.markdown("**Descrição Completa**")
            st.info(row.get("Descricao",""))

            if row.get("Acoes_Imediatas"):
                st.markdown("**Ações Imediatas Realizadas**")
                st.success(row.get("Acoes_Imediatas",""))

            if row.get("Sugestao_Melhoria"):
                st.markdown("**Sugestão de Melhoria**")
                st.warning(row.get("Sugestao_Melhoria",""))

            # Gerenciamento de status
            if perm in ["Acesso Total", "Apenas Relatórios"]:
                st.markdown("---")
                col_s1, col_s2 = st.columns([2, 1])
                with col_s1:
                    novo_status = st.selectbox(
                        "Alterar Status", STATUS_OPTS,
                        index=STATUS_OPTS.index(status_val) if status_val in STATUS_OPTS else 0,
                        key=f"status_{idx}"
                    )
                with col_s2:
                    if st.button("💾 Salvar Status", key=f"btn_status_{idx}"):
                        row_id = row.get("id")
                        db.update_incidente(row_id, {"Status": novo_status})
                        st.success("Status atualizado!")
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ABA: RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Gerenciais")

    if df_dados.empty:
        st.info("Sem dados para gerar relatórios.")
        st.stop()

    df_dados["Data_Incidente"] = pd.to_datetime(df_dados["Data_Incidente"], errors="coerce")

    tipo_rel = st.selectbox("Selecione o Relatório", [
        "Resumo Mensal por Categoria",
        "Ranking de Setores com Mais Incidentes",
        "Análise de Near Miss",
        "Incidentes com Dano Grave ou Óbito",
        "Notificações Pendentes de Análise",
        "Análise de LPP (Lesão por Pressão)",
        "Análise de Quedas",
        "Análise Medicamentosa",
        "Sugestões de Melhoria Coletadas",
    ])

    st.markdown("---")

    if tipo_rel == "Resumo Mensal por Categoria":
        df_dados["Mes"] = df_dados["Data_Incidente"].dt.to_period("M").astype(str)
        df_pivot = df_dados.groupby(["Mes", "Categoria_Incidente"]).size().unstack(fill_value=0)
        st.subheader("Notificações por Mês e Categoria")
        st.dataframe(df_pivot, use_container_width=True)
        df_melt = df_dados.groupby(["Mes", "Categoria_Incidente"]).size().reset_index(name="Qtd")
        chart = alt.Chart(df_melt).mark_bar().encode(
            x=alt.X("Mes:O"),
            y=alt.Y("Qtd:Q"),
            color=alt.Color("Categoria_Incidente:N"),
            tooltip=["Mes", "Categoria_Incidente", "Qtd"]
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)

    elif tipo_rel == "Ranking de Setores com Mais Incidentes":
        df_rank = df_dados.groupby("Setor").agg(
            Total=("Setor", "count"),
            Graves=("Gravidade", lambda x: x.str.contains("Grave|Óbito", na=False).sum()),
            NearMiss=("Gravidade", lambda x: x.str.contains("Near", na=False).sum()),
        ).sort_values("Total", ascending=False).reset_index()
        st.dataframe(df_rank, use_container_width=True, hide_index=True)
        chart = alt.Chart(df_rank).mark_bar(cornerRadiusTopRight=5).encode(
            x=alt.X("Total:Q"),
            y=alt.Y("Setor:N", sort="-x"),
            color=alt.value("#1565c0"),
            tooltip=["Setor", "Total", "Graves", "NearMiss"]
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

    elif tipo_rel == "Análise de Near Miss":
        df_nm = df_dados[df_dados["Gravidade"].str.contains("Near", na=False)].copy()
        st.metric("Total de Near Miss", len(df_nm))
        if not df_nm.empty:
            st.dataframe(df_nm[["Data_Incidente","Setor","Categoria_Incidente","Fatores_Causadores","Descricao"]],
                         use_container_width=True, hide_index=True)

    elif tipo_rel == "Incidentes com Dano Grave ou Óbito":
        df_gr = df_dados[df_dados["Gravidade"].str.contains("Grave|Óbito", na=False, regex=True)].copy()
        st.metric("Total de Incidentes Graves", len(df_gr))
        if not df_gr.empty:
            st.dataframe(df_gr[["Data_Incidente","Setor","Categoria_Incidente","Gravidade",
                                  "Dano_Paciente","Descricao","Relator"]],
                         use_container_width=True, hide_index=True)

    elif tipo_rel == "Notificações Pendentes de Análise":
        df_pend = df_dados[df_dados["Status"].isin(["Novo", "Em Análise"])].copy()
        st.metric("Pendentes de Análise", len(df_pend))
        if not df_pend.empty:
            st.dataframe(df_pend[["Data_Registro","Data_Incidente","Setor","Categoria_Incidente","Gravidade","Status"]],
                         use_container_width=True, hide_index=True)

    elif tipo_rel == "Análise de LPP (Lesão por Pressão)":
        df_lpp = df_dados[df_dados["Categoria_Incidente"].str.contains("Pressão|LPP", na=False)].copy()
        st.metric("Total LPP", len(df_lpp))
        if not df_lpp.empty:
            df_lpp_g = df_lpp["Subcategoria"].value_counts().reset_index()
            df_lpp_g.columns = ["Estágio", "Qtd"]
            st.dataframe(df_lpp_g, use_container_width=True, hide_index=True)
            chart = alt.Chart(df_lpp_g).mark_bar().encode(
                x="Qtd:Q", y=alt.Y("Estágio:N", sort="-x"), color=alt.value("#c62828"),
                tooltip=["Estágio","Qtd"]
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)

    elif tipo_rel == "Análise de Quedas":
        df_q = df_dados[df_dados["Categoria_Incidente"].str.contains("Queda", na=False)].copy()
        st.metric("Total de Quedas", len(df_q))
        if not df_q.empty:
            col_qa, col_qb = st.columns(2)
            with col_qa:
                df_tipo_queda = df_q["Subcategoria"].value_counts().reset_index()
                df_tipo_queda.columns = ["Tipo", "Qtd"]
                st.dataframe(df_tipo_queda, use_container_width=True, hide_index=True)
            with col_qb:
                df_queda_set = df_q["Setor"].value_counts().reset_index()
                df_queda_set.columns = ["Setor", "Qtd"]
                st.dataframe(df_queda_set, use_container_width=True, hide_index=True)

    elif tipo_rel == "Análise Medicamentosa":
        df_med = df_dados[df_dados["Categoria_Incidente"].str.contains("Medic|Medicament", na=False)].copy()
        st.metric("Total Falhas Medicamentosas", len(df_med))
        if not df_med.empty:
            st.dataframe(df_med[["Data_Incidente","Setor","Subcategoria","Medicamento_Envolvido",
                                   "Gravidade","Descricao"]],
                         use_container_width=True, hide_index=True)

    elif tipo_rel == "Sugestões de Melhoria Coletadas":
        df_sug = df_dados[df_dados["Sugestao_Melhoria"].notna() &
                          (df_dados["Sugestao_Melhoria"].str.strip() != "")].copy()
        st.metric("Sugestões Recebidas", len(df_sug))
        for _, r in df_sug.iterrows():
            st.markdown(f"""
            <div style="background:#f3f8ff; border-left:3px solid #1976d2; border-radius:8px;
                        padding:12px 16px; margin-bottom:8px; font-size:0.88rem;">
              <strong>{r.get('Setor','—')}</strong> — {str(r.get('Data_Incidente',''))[:10]}<br>
              {r.get('Sugestao_Melhoria','')}
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ABA: EXPORTAR DADOS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📁 Exportar Dados":
    st.title("📁 Exportar Base de Dados")

    if df_dados.empty:
        st.info("Sem dados para exportar.")
        st.stop()

    st.markdown("Faça o download da base completa ou filtrada de notificações.")

    e1, e2 = st.columns(2)
    with e1:
        data_ini_e = st.date_input("De", value=(date.today() - timedelta(days=90)), key="exp_ini")
    with e2:
        data_fim_e = st.date_input("Até", value=date.today(), key="exp_fim")

    df_dados["Data_Incidente"] = pd.to_datetime(df_dados["Data_Incidente"], errors="coerce")
    df_exp = df_dados[
        (df_dados["Data_Incidente"] >= pd.to_datetime(data_ini_e)) &
        (df_dados["Data_Incidente"] <= pd.to_datetime(data_fim_e))
    ].copy()

    st.markdown(f"**{len(df_exp)}** registros no período selecionado.")

    csv_bytes = df_exp.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar CSV (Excel compatível)",
        data=csv_bytes,
        file_name=f"incidentes_hgmf_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Pré-visualização")
    st.dataframe(df_exp.head(50), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ABA: CONFIGURAR MENUS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "⚙️ Configurar Menus":
    st.title("⚙️ Configuração de Menus e Opções")

    if df_config.empty:
        st.warning("Arquivo de configuração não encontrado. Execute o app.py primeiro para criar as opções padrão.")
        st.stop()

    lista_tabelas = sorted(df_config["Tabela"].unique().tolist())
    tab_sel = st.selectbox("Selecione o menu para editar:", lista_tabelas)

    df_f2 = df_config[df_config["Tabela"] == tab_sel].copy()
    col_t1, col_t2 = st.columns([3, 1])

    with col_t1:
        st.markdown(f"**Opções do menu: {tab_sel}**")
        df_ed = st.data_editor(
            df_f2,
            column_config={
                "Ativo":  st.column_config.CheckboxColumn("Ativo?"),
                "Tabela": None,
            },
            disabled=["Opcao"],
            hide_index=True,
            use_container_width=True
        )
        if st.button("💾 Gravar Alterações", type="primary"):
            for _, r in df_ed.iterrows():
                row_id = r.get("id")
                if row_id:
                    db.save_config_opcao(row_id, bool(r["Ativo"]))
            st.success("✅ Configuração salva!")
            st.rerun()

    with col_t2:
        st.markdown("**➕ Adicionar Opção**")
        n_op = st.text_input("Nome da nova opção")
        if st.button("Adicionar", use_container_width=True):
            if n_op.strip():
                existe = ((df_config["Tabela"] == tab_sel) &
                          (df_config["Opcao"].str.lower() == n_op.strip().lower())).any()
                if not existe:
                    db.add_config_opcao(tab_sel, n_op.strip())
                    st.success("Adicionado!")
                    st.rerun()
                else:
                    st.warning("Opção já existe.")
            else:
                st.warning("Digite um nome.")

# ══════════════════════════════════════════════════════════════════════════════
# ABA: USUÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "👥 Usuários":
    st.title("👥 Gerenciamento de Usuários")

    u1, u2 = st.columns([3, 2])

    with u1:
        st.subheader("Usuários Cadastrados")
        df_show = df_usuarios[["Usuario", "Permissao", "Ativo", "Data_Criacao"]].copy()
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔒 Alterar Status / Permissão")
        usuario_sel = st.selectbox("Selecione o usuário", df_usuarios["Usuario"].tolist(), key="usr_sel")
        row_sel = df_usuarios[df_usuarios["Usuario"] == usuario_sel].iloc[0]
        col_pa, col_pb = st.columns(2)
        with col_pa:
            nova_perm = st.selectbox("Permissão", PERMISSOES,
                                     index=PERMISSOES.index(row_sel["Permissao"]) if row_sel["Permissao"] in PERMISSOES else 0,
                                     key="nova_perm")
        with col_pb:
            novo_ativo = st.checkbox("Usuário Ativo", value=bool(row_sel["Ativo"]), key="novo_ativo")

        col_pc, col_pd = st.columns(2)
        with col_pc:
            if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                row_u = df_usuarios[df_usuarios["Usuario"] == usuario_sel].iloc[0]
                db.update_user(row_u["id"], {"Permissao": nova_perm, "Ativo": novo_ativo})
                st.success("Usuário atualizado!")
                st.rerun()
        with col_pd:
            if usuario_sel != st.session_state["user"] and usuario_sel != "admin":
                if st.button("🗑️ Remover Usuário", use_container_width=True):
                    row_u = df_usuarios[df_usuarios["Usuario"] == usuario_sel].iloc[0]
                    db.delete_user(row_u["id"])
                    st.success("Usuário removido.")
                    st.rerun()

        st.markdown("---")
        st.subheader("🔑 Redefinir Senha de Usuário")
        usr_troca = st.selectbox("Usuário", df_usuarios["Usuario"].tolist(), key="usr_troca")
        nova_senha_admin = st.text_input("Nova Senha", type="password", key="nova_senha_admin")
        if st.button("Redefinir Senha", use_container_width=True):
            if nova_senha_admin.strip():
                row_t = df_usuarios[df_usuarios["Usuario"] == usr_troca].iloc[0]
                db.update_user(row_t["id"], {"Senha_Hash": hash_senha(nova_senha_admin)})
                st.success(f"Senha de '{usr_troca}' redefinida com sucesso!")
            else:
                st.warning("Digite a nova senha.")

    with u2:
        st.subheader("➕ Criar Novo Usuário")
        with st.form("form_novo_usuario"):
            n_user  = st.text_input("Login (sem espaços)")
            n_senha = st.text_input("Senha", type="password")
            n_conf  = st.text_input("Confirmar Senha", type="password")
            n_perm  = st.selectbox("Nível de Acesso", PERMISSOES)
            criar   = st.form_submit_button("✅ Criar Usuário", use_container_width=True)

            if criar:
                if not n_user.strip() or not n_senha.strip():
                    st.error("Preencha login e senha.")
                elif " " in n_user:
                    st.error("Login não pode conter espaços.")
                elif n_senha != n_conf:
                    st.error("As senhas não coincidem.")
                elif (df_usuarios["Usuario"].str.lower() == n_user.strip().lower()).any():
                    st.error("Este login já está em uso.")
                elif len(n_senha) < 6:
                    st.error("A senha deve ter ao menos 6 caracteres.")
                else:
                    novo_usr = {
                        "Usuario":      n_user.strip(),
                        "Senha_Hash":   hash_senha(n_senha),
                        "Permissao":    n_perm,
                        "Ativo":        True,
                        "Data_Criacao": date.today().strftime("%Y-%m-%d"),
                    }
                    db.save_user(novo_usr)
                    st.success(f"Usuário '{n_user.strip()}' criado com sucesso!")
                    st.rerun()

        st.markdown("---")
        st.markdown("**ℹ️ Níveis de Acesso**")
        st.markdown("""
        - **Acesso Total**: Dashboard, Notificações, Relatórios, Exportar, Configurar Menus e Usuários
        - **Apenas Relatórios**: Dashboard, Notificações, Relatórios e Exportar
        - **Apenas Configurar Tabelas**: Configurar Menus e Usuários
        """)
        st.markdown("---")
        st.markdown("**🔑 Login Mestre do Sistema**")
        st.info("O usuário `admin_master` tem acesso irrestrito e não aparece na lista de usuários. Use-o apenas para configuração inicial.")
