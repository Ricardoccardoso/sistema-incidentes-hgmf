"""
Gestao.py — Painel de Gestão do sistema de incidentes HGMF

Página protegida por login destinada à equipe do Núcleo de Segurança do Paciente.
Funcionalidades disponíveis conforme permissão do usuário:

  📊 Dashboard        — indicadores e gráficos do período
  📋 Notificações     — lista, detalhe, edição, registros de ação e status
  📈 Relatórios       — análises temáticas (LPP, quedas, medicamentos, etc.)
  📁 Exportar Dados   — download em Excel do período filtrado
  ⚙️ Configurar Menus — gerenciar opções dos selectboxes e campos obrigatórios
  👥 Usuários         — criar, editar permissões e remover usuários

Sistema de permissões:
  - Menus: controlam quais abas o usuário vê na navegação
  - CAP_EDITAR    (cap_editar_notificacoes):  exibe botão de edição de registros
  - CAP_REGISTROS (cap_registros_equipe):     exibe registros de ação e alterar status
"""

import streamlit as st
import streamlit.components.v1 as components  # necessário para injetar JS de impressão
import pandas as pd
import altair as alt
import hashlib
import html as html_mod
import json as _json_mod
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
try:
    SENHA_ADMIN_MESTRE = st.secrets["admin_master"]["hash"]
except (KeyError, FileNotFoundError, AttributeError):
    SENHA_ADMIN_MESTRE = ""  # login mestre desabilitado se não configurado

COLUNAS_DADOS = [
    "id", "Data_Registro", "Data_Incidente", "Turno", "Setor",
    "Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade",
    "Fatores_Causadores", "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Data_Relato", "Hora_Relato", "Nome_Paciente", "Data_Nascimento",
    "Relator", "Funcao_Relator", "Status"
]

STATUS_OPTS    = ["Investigar", "Notificar", "Em Análise", "Pendência", "Concluído"]
PERMISSOES     = ["Acesso Total", "Apenas Relatórios", "Apenas Configurar Tabelas"]
MENU_OPTIONS   = [
    ("📊 Dashboard", "Dashboard"),
    ("📋 Notificações", "Notificações"),
    ("📈 Relatórios", "Relatórios"),
    ("📁 Exportar Dados", "Exportar Dados"),
    ("⚙️ Configurar Menus", "Configurar Menus"),
    ("👥 Usuários", "Usuários"),
]
MENU_LABELS    = [label for _, label in MENU_OPTIONS]

# Capacidades especiais (não são menus, mas ações dentro das páginas)
CAP_EDITAR    = "cap_editar_notificacoes"
CAP_REGISTROS = "cap_registros_equipe"

PRESET_PERMISSIONS = {
    "Acesso Total": MENU_LABELS + [CAP_EDITAR, CAP_REGISTROS],
    "Apenas Relatórios": ["Dashboard", "Notificações", "Relatórios", "Exportar Dados", CAP_REGISTROS],
    "Apenas Configurar Tabelas": ["Configurar Menus", "Usuários"],
}

def parse_permissions(value):
    """
    Converte o campo Permissao (string) em lista de permissões individuais.

    Aceita:
      - Strings predefinidas ("Acesso Total", etc.) → expande via PRESET_PERMISSIONS
      - Strings semicolon-separated ("Dashboard;Notificações;cap_editar_notificacoes")
      - Qualquer outro valor → lista vazia

    Retorna lista de strings com menus e/ou capacidades especiais.
    """
    if value in PRESET_PERMISSIONS:
        return PRESET_PERMISSIONS[value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(";") if item.strip()]
    return []


def permissions_to_string(selected):
    """
    Converte uma lista de permissões de volta para string armazenável no banco.

    Se a lista contiver todos os menus E todas as capacidades especiais,
    retorna a string compacta "Acesso Total". Caso contrário, junta com ";".

    Parâmetros:
      selected — lista de strings com menus e/ou capacidades
    """
    if set(selected) == set(MENU_LABELS + [CAP_EDITAR, CAP_REGISTROS]):
        return "Acesso Total"
    return ";".join(selected)


def has_perm(perm_str, capability):
    """
    Verifica se uma string de permissão contém uma capacidade específica.

    Parâmetros:
      perm_str   — string armazenada no banco (ex: "Acesso Total" ou "Dashboard;cap_editar_notificacoes")
      capability — constante a verificar (ex: CAP_EDITAR, CAP_REGISTROS)

    Retorna True se a capacidade estiver presente, False caso contrário.
    """
    return capability in parse_permissions(perm_str)

CAMPO_LABELS = {
    "Acoes_Imediatas":      "Ações Imediatas",
    "Categoria_Incidente":  "Categoria do Incidente",
    "Data_Incidente":       "Data do Incidente",
    "Data_Nascimento":      "Data de Nascimento",
    "Data_Registro":        "Data do Registro",
    "Data_Relato":          "Data do Relato",
    "Descricao":            "Descrição do Incidente",
    "Fatores_Causadores":   "Fatores Causadores",
    "Funcao_Relator":       "Função / Cargo do Relator",
    "Gravidade":            "Gravidade",
    "Hora_Relato":          "Hora do Relato",
    "Leito":                "Leito",
    "Medicamento_Envolvido":"Medicamento Envolvido",
    "Nome_Paciente":        "Nome do Paciente",
    "Raca_Cor":             "Raça / Cor",
    "Relator":              "Nome do Relator",
    "Setor":                "Setor / Unidade",
    "Status":               "Status",
    "Subcategoria":         "Subcategoria",
    "Sugestao_Melhoria":    "Sugestão de Melhoria",
    "Tipo_Geral":           "Tipo Geral",
    "Turno":                "Hora/Turno",
}

GRAVIDADE_CORES = {
    "Near Miss": "near",
    "Sem Dano":  "semDano",
    "Dano Leve": "leve",
    "Dano Moderado": "moderado",
    "Dano Grave": "grave",
    "Óbito":     "grave",
}

def _cor_gravidade(g: str) -> str:
    """
    Retorna a classe CSS correspondente ao nível de gravidade do incidente.
    Usada para colorir a borda esquerda dos cards de notificação.

    Parâmetros:
      g — string de gravidade (ex: "Dano Grave (lesão grave/permanente)")

    Retorna uma das classes: "near", "semDano", "leve", "moderado", "grave"
    """
    for k, v in GRAVIDADE_CORES.items():
        if k.lower() in str(g).lower():
            return v
    return "semDano"  # padrão verde quando a gravidade não é reconhecida

# ─── Funções delegadas ao módulo db ──────────────────────────────────────────
hash_senha  = db.hash_senha
load_data   = db.load_data
load_config = db.load_config
load_users  = db.load_users

def save_data(df):
    """Stub de compatibilidade — não usado. Alterações pontuais usam db.update_incidente()."""
    pass


def save_config(df):
    """Stub de compatibilidade — não usado. Alterações usam db.save_config_opcao()."""
    pass


def save_users(df):
    """Stub de compatibilidade — não usado. Alterações usam db.update_user()."""
    pass


def get_opcoes(df_conf, tabela):
    """Wrapper local para db.get_opcoes — retorna opções ativas de um menu de configuração."""
    return db.get_opcoes(df_conf, tabela)


def gerar_html_impressao(df_rows: pd.DataFrame) -> str:
    """
    Gera um documento HTML formatado para impressão/PDF de uma ou mais notificações.

    O HTML inclui:
      - Cabeçalho com nome do hospital e data de geração
      - Uma seção por notificação com todos os campos relevantes
      - CSS de impressão (A4, page-break-inside:avoid)
      - Botão fixo "Imprimir / Salvar PDF" que aciona window.print()

    Todos os valores são escapados via html.escape() para evitar XSS.

    Parâmetros:
      df_rows — DataFrame com uma ou mais linhas de incidentes

    Retorna string HTML pronta para download ou exibição.
    """
    def esc(v):
        """Escapa caracteres HTML especiais para evitar XSS no documento gerado."""
        return html_mod.escape(str(v or "—"))

    linhas = []
    for i, (_, row) in enumerate(df_rows.iterrows()):
        acoes = str(row.get("Acoes_Imediatas", "") or "").strip()
        bloco_acoes = (
            f'<div class="campo"><div class="lbl">Ações Imediatas</div>{esc(acoes)}</div>'
            if acoes and acoes.lower() != "nan" else ""
        )
        linhas.append(f"""
        <div class="notificacao">
          <div class="notif-header">
            <span class="n">#{i+1}</span>
            {esc(row.get("Categoria_Incidente","—"))} &nbsp;·&nbsp;
            {esc(row.get("Gravidade","—"))} &nbsp;·&nbsp;
            Status: <strong>{esc(row.get("Status","—"))}</strong>
          </div>
          <table>
            <tr>
              <td><div class="lbl">Data do Incidente</div>{str(row.get("Data_Incidente",""))[:10]}</td>
              <td><div class="lbl">Turno</div>{esc(row.get("Turno","—"))}</td>
              <td><div class="lbl">Setor / Leito</div>{esc(row.get("Setor","—"))} / {esc(row.get("Leito","—"))}</td>
              <td><div class="lbl">Tipo</div>{esc(row.get("Tipo_Geral","—"))}</td>
            </tr>
            <tr>
              <td><div class="lbl">Paciente</div>{esc(row.get("Nome_Paciente","") or "Não informado")}</td>
              <td><div class="lbl">Nasc. / Idade</div>{str(row.get("Data_Nascimento",""))[:10]}</td>
              <td><div class="lbl">Raça / Cor</div>{esc(row.get("Raca_Cor","") or "—")}</td>
              <td><div class="lbl">Relator / Função</div>{esc(row.get("Relator","") or "Anônimo")} — {esc(row.get("Funcao_Relator","") or "—")}</td>
            </tr>
          </table>
          <div class="campo"><div class="lbl">Fatores Causadores</div>{esc(row.get("Fatores_Causadores","") or "—")}</div>
          <div class="campo"><div class="lbl">Descrição do Incidente</div>{esc(row.get("Descricao","") or "—")}</div>
          {bloco_acoes}
          <div class="rodape">
            Registrado em: {str(row.get("Data_Registro",""))[:16]} &nbsp;|&nbsp;
            Relato: {str(row.get("Data_Relato",""))[:10]} {str(row.get("Hora_Relato",""))[:5]}
          </div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Notificações — HGMF</title>
<style>
  @media print {{ @page {{ margin:1.5cm; size:A4; }} }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:Arial,sans-serif; font-size:11px; color:#222; background:#fff; padding:24px; }}
  .topo {{ text-align:center; border-bottom:3px solid #0d47a1; margin-bottom:24px; padding-bottom:12px; }}
  .topo h2 {{ color:#0d47a1; font-size:16px; }}
  .topo p {{ color:#555; font-size:11px; margin-top:4px; }}
  .notificacao {{ page-break-inside:avoid; border:1px solid #c8d8f0; border-radius:6px; padding:14px; margin-bottom:20px; }}
  .notif-header {{ background:#e8f0fe; padding:8px 12px; border-radius:4px; margin-bottom:10px; font-size:12px; font-weight:600; color:#0d47a1; }}
  .n {{ font-size:13px; margin-right:8px; }}
  table {{ width:100%; border-collapse:collapse; margin:8px 0; }}
  td {{ padding:5px 8px; border:1px solid #dde; vertical-align:top; width:25%; }}
  .lbl {{ font-size:8.5px; text-transform:uppercase; color:#666; font-weight:700; margin-bottom:2px; }}
  .campo {{ padding:8px; background:#f8f9fc; border-radius:4px; margin:6px 0; line-height:1.5; }}
  .rodape {{ font-size:9px; color:#888; margin-top:10px; border-top:1px solid #eee; padding-top:6px; }}
  .print-btn {{ position:fixed; top:16px; right:16px; background:#0d47a1; color:#fff; border:none;
                padding:10px 20px; border-radius:6px; cursor:pointer; font-size:13px; z-index:999; }}
  @media print {{ .print-btn {{ display:none; }} }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>
<div class="topo">
  <h2>Hospital Geral Menandro de Faria</h2>
  <p>Núcleo de Segurança do Paciente — Notificações de Incidente</p>
  <p style="margin-top:4px;font-size:10px;color:#888;">Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}</p>
</div>
{"".join(linhas)}
</body>
</html>"""


# ─── Session state ────────────────────────────────────────────────────────────
# Inicializa as chaves de sessão apenas se ainda não existirem.
# Isso preserva os valores entre reruns sem sobrescrever o estado atual.
#   logado       — True quando o usuário completou o login com sucesso
#   user         — nome de usuário logado
#   permissao    — string de permissão armazenada no banco
#   tentativas   — contador de tentativas de login falhas (proteção brute-force)
#   bloqueado_ate — datetime até quando o login está bloqueado (None = desbloqueado)
for k, v in {
    "logado": False, "user": "", "permissao": "",
    "tentativas": 0, "bloqueado_ate": None
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── TELA DE LOGIN ────────────────────────────────────────────────────────────
# Exibida enquanto o usuário não estiver autenticado.
# Fluxo de autenticação:
#   1. Verifica se o login está bloqueado por excesso de tentativas
#   2. Tenta login mestre (admin_master) via hash lido dos Secrets
#   3. Tenta login normal consultando a tabela de usuários no Supabase
#   4. Após 5 tentativas falhas, bloqueia por 5 minutos (armazenado na sessão)
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
# A partir daqui o usuário está logado.
# Carrega os dados necessários para todas as abas do painel.
# O banner de notificação (sucesso/erro) é exibido no topo antes de qualquer aba.
df_dados    = load_data()   # todos os incidentes registrados
df_config   = load_config()
df_usuarios = load_users()

_banner = st.session_state.pop("_notif_banner", None)
if _banner:
    if _banner["type"] == "success":
        st.success(_banner["msg"])
    else:
        st.error(_banner["msg"])

perm = st.session_state["permissao"]

# Monta lista de menus permitidos
menu_items = []
user_perms = parse_permissions(perm)
for display, label in MENU_OPTIONS:
    if label in user_perms:
        menu_items.append(display)

if not menu_items:
    st.warning("Seu usuário não possui menus autorizados. Contate o administrador.")
    st.stop()

# Sidebar — apenas identificação do usuário (informativo, opcional no celular)
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 8px;">
      <span style="font-size:2rem;">👤</span>
      <p style="font-weight:700; font-size:1rem; margin:4px 0 2px;">{st.session_state['user']}</p>
      <p style="font-size:0.76rem; opacity:0.7; margin:0;">{perm}</p>
    </div>
    """, unsafe_allow_html=True)

# ── Barra de navegação — acessível em qualquer dispositivo ───────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d47a1,#1565c0);
            border-radius:10px; padding:10px 18px; margin-bottom:12px;
            display:flex; justify-content:space-between; align-items:center;">
  <span style="color:#fff; font-size:0.88rem; font-weight:600;">
    👤 {st.session_state['user']}
    <span style="font-weight:400; opacity:0.75; font-size:0.78rem; margin-left:8px;">{perm}</span>
  </span>
</div>
""", unsafe_allow_html=True)

_nc_menu, _nc_sair = st.columns([6, 1])
with _nc_menu:
    menu = st.selectbox("Módulo", menu_items, label_visibility="collapsed")
with _nc_sair:
    if st.button("🚪 Sair", use_container_width=True):
        for k in ["logado", "user", "permissao"]:
            st.session_state[k] = "" if k != "logado" else False
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ABA: DASHBOARD
# Exibe indicadores agregados e gráficos para o período selecionado.
# Permite filtrar por data, setor e exibe KPIs + 6 gráficos Altair:
#   - Gravidade (donut), Categoria (barras), Evolução temporal (linha),
#     Setor (barras), Turno (barras), Fatores causadores (barras)
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
        s1, s2, s3, s4, s5 = st.columns(5)
        for col_k, status_n in zip([s1, s2, s3, s4, s5], STATUS_OPTS):
            qtd = int(df_status[df_status["Status"] == status_n]["Qtd"].sum()) if not df_status.empty else 0
            col_k.metric(status_n, qtd)

# ══════════════════════════════════════════════════════════════════════════════
# ABA: NOTIFICAÇÕES
# Lista todas as notificações com filtros por status, categoria, setor e gravidade.
# Cada notificação exibe um card resumido e um expander com:
#   - Dados completos do evento e paciente
#   - Botão de impressão individual (gera HTML/PDF para download)
#   - Formulário de edição (se CAP_EDITAR)
#   - Registros de ação da equipe de segurança (se CAP_REGISTROS)
#   - Alteração de status (se CAP_REGISTROS)
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

    df_sorted_view = df_view.sort_values("Data_Registro", ascending=False).reset_index(drop=True)

    st.markdown(f"**{len(df_sorted_view)}** notificações encontradas")
    st.markdown("---")

    for idx, row in df_sorted_view.iterrows():
        cor = _cor_gravidade(str(row.get("Gravidade", "")))
        status_val = str(row.get("Status", "Novo"))
        badge_class = {
            "Investigar": "badge-analise", "Notificar": "badge-critico",
            "Em Análise": "badge-analise", "Pendência": "badge-critico",
            "Concluído": "badge-concluido"
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
                st.write(f"- Data do Incidente: {str(row.get('Data_Incidente',''))[:10]}")
                st.write(f"- Hora/Turno: {row.get('Turno','')}")
                st.write(f"- Setor: {row.get('Setor','')} | Leito: {row.get('Leito','')}")
                st.write(f"- Tipo: {row.get('Tipo_Geral','')}")
                st.write(f"- Categoria: {row.get('Categoria_Incidente','')}")
                if row.get("Subcategoria"):
                    st.write(f"- Subcategoria: {row.get('Subcategoria','')}")
                if row.get("Medicamento_Envolvido"):
                    st.write(f"- Medicamento: {row.get('Medicamento_Envolvido','')}")
                # dados do relato/paciente
                st.write(f"- Data do Relato: {str(row.get('Data_Relato',''))[:10]}")
                st.write(f"- Hora do Relato: {row.get('Hora_Relato','')}")
                st.write(f"- Paciente: {row.get('Nome_Paciente','')}")
                st.write(f"- Data Nascimento: {str(row.get('Data_Nascimento',''))[:10]}")
            with d2:
                st.markdown("**Gravidade**")
                st.write(f"- Gravidade: {row.get('Gravidade','')}")

            st.markdown("**Fatores Causadores**")
            st.write(row.get("Fatores_Causadores","Não informado") or "Não informado")

            st.markdown("**Descrição Completa**")
            st.info(row.get("Descricao",""))

            acoes_val = str(row.get("Acoes_Imediatas", "") or "").strip()
            if acoes_val and acoes_val.lower() != "nan":
                st.markdown("**Ações Imediatas Realizadas**")
                st.success(acoes_val)

            sug_val = str(row.get("Sugestao_Melhoria", "") or "").strip()
            if sug_val and sug_val.lower() != "nan":
                st.markdown("**Sugestão de Melhoria**")
                st.warning(sug_val)

            # Botão de impressão: abre nova aba com conteúdo formatado e dispara window.print()
            st.markdown("---")
            if st.button("🖨️ Imprimir esta notificação", key=f"print_{idx}", use_container_width=True):
                # Gera o HTML e armazena na sessão para o componente JS abaixo
                st.session_state[f"_print_html_{idx}"] = gerar_html_impressao(
                    pd.DataFrame([row.to_dict()])
                )

            # Componente JS renderizado apenas após o clique — abre janela e imprime
            if f"_print_html_{idx}" in st.session_state:
                _ph    = st.session_state.pop(f"_print_html_{idx}")
                _ph_js = _json_mod.dumps(_ph)  # escapa corretamente para literal JS
                components.html(f"""
                <script>
                (function(){{
                  var html = {_ph_js};
                  try {{
                    var blob = new Blob([html], {{type:'text/html;charset=utf-8'}});
                    var url  = URL.createObjectURL(blob);
                    var pw   = window.parent.open(url, '_blank');
                    if (pw) {{
                      pw.addEventListener('load', function(){{ pw.focus(); pw.print(); }});
                    }} else {{
                      document.body.innerHTML =
                        '<p style="font-family:Arial,sans-serif;font-size:13px;padding:8px;">'
                        +'⚠️ Popup bloqueado. '
                        +'<a href="'+url+'" target="_blank" style="color:#0d47a1;font-weight:600;">'
                        +'Clique aqui para abrir e imprimir</a></p>';
                    }}
                  }} catch(e) {{}}
                }})();
                </script>
                """, height=40, scrolling=False)

            # Edição disponível para usuários com permissão Editar Notificações
            if has_perm(perm, CAP_EDITAR):
                st.markdown('---')
                if st.button('✏️ Editar registro', key=f'edit_btn_{idx}'):
                    st.session_state[f'edit_{idx}'] = True
                if st.session_state.get(f'edit_{idx}', False):
                    with st.form(f'edit_form_{idx}'):
                        # pré-preenche valores atuais
                        cur_date = None
                        try:
                            cur_date = pd.to_datetime(row.get('Data_Incidente')).date()
                        except Exception:
                            cur_date = date.today()
                        new_data = st.date_input('Data do Incidente', value=cur_date, format="DD/MM/YYYY")
                        ops = get_opcoes(df_config, 'Turno')
                        cur_turno = row.get('Turno','')
                        try:
                            idx_turno = ops.index(cur_turno) if cur_turno in ops else 0
                        except Exception:
                            idx_turno = 0
                        new_turno = st.selectbox('Hora/Turno do Incidente', ops, index=idx_turno)
                        new_setor = st.selectbox('Setor', get_opcoes(df_config, 'Setor'), index=0)
                        new_leito = st.text_input('Leito', value=row.get('Leito',''))
                        new_nome = st.text_input('Nome do Paciente', value=row.get('Nome_Paciente','') or '')
                        # data de nascimento
                        try:
                            val = row.get('Data_Nascimento')
                            if val and str(val).strip():
                                cur_nasc = pd.to_datetime(val).date()
                            else:
                                cur_nasc = date(2000, 1, 1)
                        except Exception:
                            cur_nasc = date(2000,1,1)
                        new_nasc = st.date_input('Data de Nascimento', value=cur_nasc, min_value=date(1900, 1, 1), format="DD/MM/YYYY")
                        new_descricao = st.text_area('Descrição completa', value=row.get('Descricao',''))
                        new_acoes = st.text_area('Ações Imediatas', value=row.get('Acoes_Imediatas',''))
                        new_sug = st.text_area('Sugestão de melhoria', value=row.get('Sugestao_Melhoria',''))
                        if st.form_submit_button('💾 Salvar alterações'):
                            campos = {
                                'Data_Incidente': str(new_data),
                                'Turno': new_turno,
                                'Setor': new_setor,
                                'Leito': new_leito,
                                'Nome_Paciente': new_nome,
                                'Data_Nascimento': str(new_nasc),
                                'Descricao': new_descricao,
                                'Acoes_Imediatas': new_acoes,
                                'Sugestao_Melhoria': new_sug
                            }
                            try:
                                db.update_incidente(row.get('id'), campos)
                                st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Salvo com sucesso!"}
                            except Exception as e:
                                st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar: {e}"}
                            st.rerun()

            # Registros de ação da equipe de segurança
            if has_perm(perm, CAP_REGISTROS):
                st.markdown("---")
                st.markdown("**📋 Registros da Equipe de Segurança**")
                incidente_id = row.get("id")
                df_reg = db.load_registros_acao(incidente_id)
                if not df_reg.empty:
                    df_reg_show = df_reg[["Data_Registro", "Usuario", "Descricao"]].copy()
                    df_reg_show.columns = ["Data / Hora", "Usuário", "Descrição"]
                    df_reg_show["Data / Hora"] = df_reg_show["Data / Hora"].astype(str).str[:16]
                    st.dataframe(df_reg_show, use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhum registro de ação ainda.")

                with st.form(f"form_acao_{idx}"):
                    nova_acao = st.text_area(
                        "Descreva a ação realizada pela equipe",
                        height=80,
                        placeholder="Ex: Notificado o médico responsável, aberta investigação...",
                        key=f"ta_acao_{idx}"
                    )
                    submit_acao = st.form_submit_button("➕ Inserir Registro", use_container_width=True)

                if submit_acao:
                    if nova_acao.strip():
                        try:
                            db.save_registro_acao(incidente_id, nova_acao, st.session_state.get("user", ""))
                            st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Registro inserido com sucesso!"}
                        except Exception as e:
                            st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao inserir registro: {e}"}
                        st.rerun()
                    else:
                        st.warning("Digite a descrição da ação.")

            # Gerenciamento de status
            if has_perm(perm, CAP_REGISTROS):
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
                        try:
                            db.update_incidente(row_id, {"Status": novo_status})
                            st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Status atualizado com sucesso!"}
                        except Exception as e:
                            st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar status: {e}"}
                        st.rerun()

        st.markdown(
            '<div style="border-top:3px solid #dbe4f0;margin:20px 0 8px 0;border-radius:2px;"></div>',
            unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# ABA: RELATÓRIOS
# Relatórios temáticos pré-configurados — o usuário seleciona o tipo e
# o sistema filtra e exibe tabelas + gráficos específicos. Tipos disponíveis:
#   Resumo Mensal, Ranking Setores, Near Miss, Dano Grave, Pendências,
#   LPP, Quedas, Medicamentos, Sugestões de Melhoria
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
                                  "Nome_Paciente","Data_Nascimento","Descricao","Relator"]],
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
# Permite baixar a base de incidentes filtrada por período em formato Excel (.xlsx).
# Usa openpyxl via pandas ExcelWriter. Exibe pré-visualização dos primeiros 50 registros.
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

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_exp.to_excel(writer, index=False, sheet_name="Incidentes")
    excel_buffer.seek(0)

    st.download_button(
        "⬇️ Baixar Excel (.xlsx)",
        data=excel_buffer,
        file_name=f"incidentes_hgmf_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Pré-visualização")
    st.dataframe(df_exp.head(50), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ABA: CONFIGURAR MENUS
# Duas funcionalidades nesta aba:
#   1. Editar opções dos selectboxes do formulário (turnos, setores, categorias, etc.)
#      — tabela editável com opção de ativar/desativar/excluir itens e adicionar novos
#   2. Campos Obrigatórios — marcar quais campos do formulário exibem * e são validados
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
        if tab_sel == "Gravidade":
            st.caption("ℹ️ Defina a **Ordem** de cada nível (1 = menos grave). Esse campo é obrigatório e controla a sequência no formulário.")

        df_ed = df_f2.copy()
        df_ed["Excluir"] = False

        # Configuração de colunas: Ordem só aparece (e é obrigatório) em Gravidade
        col_config_ed = {
            "id":      None,
            "Tabela":  None,
            "Ativo":   st.column_config.CheckboxColumn("Ativo?"),
            "Excluir": st.column_config.CheckboxColumn("✖"),
            "Ordem":   None,  # oculto por padrão para outros menus
        }
        if tab_sel == "Gravidade":
            col_config_ed["Ordem"] = st.column_config.NumberColumn(
                "Ordem",
                help="Posição na escala de gravidade (1 = menos grave, 6 = mais grave). Obrigatório.",
                min_value=1,
                step=1,
                required=True,
            )

        edited = st.data_editor(
            df_ed,
            column_config=col_config_ed,
            disabled=["id", "Tabela"],
            hide_index=True,
            use_container_width=True
        )
        if st.button("💾 Salvar Alterações", type="primary"):
            rows_ativos = edited[edited["Excluir"] != True]
            invalid_nome = rows_ativos[rows_ativos["Opcao"].astype(str).str.strip().eq("")]
            if not invalid_nome.empty:
                st.warning("Cada opção de menu deve ter um nome válido ou ser marcada para exclusão.")
            elif tab_sel == "Gravidade":
                # Valida que Ordem foi preenchida para todos os itens de Gravidade
                invalid_ordem = rows_ativos[
                    rows_ativos["Ordem"].isna() | (pd.to_numeric(rows_ativos["Ordem"], errors="coerce") < 1)
                ]
                if not invalid_ordem.empty:
                    st.warning("⚠️ Preencha a **Ordem** (número ≥ 1) para todas as opções de gravidade antes de salvar.")
                else:
                    erros = []
                    for _, row in edited[edited["Excluir"] == True].iterrows():
                        try:
                            db.delete_config_opcao(row["id"], row["Tabela"])
                        except Exception as e:
                            erros.append(str(e))
                    for _, row in rows_ativos.iterrows():
                        try:
                            db.save_config_opcao(
                                row["id"], row["Tabela"],
                                str(row["Opcao"]).strip(), bool(row["Ativo"]),
                                int(row["Ordem"])
                            )
                        except Exception as e:
                            erros.append(str(e))
                    if erros:
                        st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar: {'; '.join(erros)}"}
                    else:
                        st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Salvo com sucesso!"}
                    st.rerun()
            else:
                erros = []
                for _, row in edited[edited["Excluir"] == True].iterrows():
                    try:
                        db.delete_config_opcao(row["id"], row["Tabela"])
                    except Exception as e:
                        erros.append(str(e))
                for _, row in rows_ativos.iterrows():
                    try:
                        db.save_config_opcao(row["id"], row["Tabela"], str(row["Opcao"]).strip(), bool(row["Ativo"]))
                    except Exception as e:
                        erros.append(str(e))
                if erros:
                    st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar: {'; '.join(erros)}"}
                else:
                    st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Salvo com sucesso!"}
                st.rerun()

    with col_t2:
        st.markdown("**➕ Adicionar Opção**")
        n_op = st.text_input("Nome da nova opção")
        # Campo Ordem obrigatório somente para Gravidade
        n_ordem = None
        if tab_sel == "Gravidade":
            n_ordem = st.number_input("Ordem *", min_value=1, step=1, value=1,
                                      help="Posição na escala (1 = menos grave)")
        if st.button("Adicionar", use_container_width=True):
            if n_op.strip():
                existe = ((df_config["Tabela"] == tab_sel) &
                          (df_config["Opcao"].str.lower() == n_op.strip().lower())).any()
                if not existe:
                    try:
                        db.add_config_opcao(tab_sel, n_op.strip(),
                                            int(n_ordem) if n_ordem is not None else None)
                        st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Opção adicionada com sucesso!"}
                    except Exception as e:
                        st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao adicionar: {e}"}
                    st.rerun()
                else:
                    st.warning("Opção já existe.")
            else:
                st.warning("Digite um nome.")

        st.markdown("*Marque as linhas com ✖ para excluir as opções e clique em **Gravar Alterações**.*")

    st.markdown("---")
    st.subheader("⚙️ Campos Obrigatórios")
    try:
        df_flags = db.load_field_flags()
    except Exception:
        df_flags = None

    if df_flags is None or df_flags.empty:
        st.info("Nenhuma configuração de campos encontrada. Verifique a tabela config_campos no Supabase.")
    else:
        df_display = df_flags.copy()
        df_display.insert(1, "Nome do Campo",
                          df_display["Campo"].map(CAMPO_LABELS).fillna(df_display["Campo"]))
        dff = st.data_editor(
            df_display,
            column_config={
                "id":            None,
                "Campo":         None,
                "Nome do Campo": st.column_config.TextColumn("Campo", disabled=True),
                "Obrigatorio":   st.column_config.CheckboxColumn("Obrigatório?"),
            },
            hide_index=True,
            use_container_width=True
        )
        if st.button("💾 Salvar Campos Obrigatórios"):
            erros = []
            for _, r in dff.iterrows():
                row_id = r.get("id")
                if row_id is not None:
                    try:
                        db.save_field_flag(row_id, bool(r["Obrigatorio"]))
                    except Exception as e:
                        erros.append(str(e))
            if erros:
                st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar: {'; '.join(erros)}"}
            else:
                st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Salvo com sucesso!"}
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ABA: USUÁRIOS
# Gerenciamento completo de usuários do painel de gestão:
#   - Listar usuários cadastrados com permissão e status
#   - Editar menus autorizados e permissões especiais (CAP_EDITAR, CAP_REGISTROS)
#   - Ativar/desativar conta
#   - Remover usuário (exceto o próprio usuário logado e o "admin")
#   - Redefinir senha de qualquer usuário
#   - Criar novo usuário com login, senha e permissões configuráveis
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "👥 Usuários":
    st.title("👥 Gerenciamento de Usuários")

    u1, u2 = st.columns([3, 2])

    with u1:
        st.subheader("Usuários Cadastrados")
        df_show = df_usuarios[["Usuario", "Permissao", "Ativo", "Data_Criacao"]].copy()
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("✏️ Editar Usuário")
        usuario_sel = st.selectbox("Usuário", df_usuarios["Usuario"].tolist(), key="usr_sel")
        row_sel     = df_usuarios[df_usuarios["Usuario"] == usuario_sel].iloc[0]
        user_perms  = parse_permissions(row_sel["Permissao"])

        col_pa, col_pb = st.columns(2)
        with col_pa:
            st.markdown("**Menus autorizados**")
            selected_menus = st.multiselect(
                "Menus",
                MENU_LABELS,
                default=[p for p in user_perms if p in MENU_LABELS],
                key="menus_sel",
                label_visibility="collapsed"
            )
        with col_pb:
            st.markdown("**Permissões especiais**")
            cap_editar_sel = st.checkbox(
                "✏️ Editar Notificações",
                value=has_perm(row_sel["Permissao"], CAP_EDITAR),
                key="cap_editar_sel"
            )
            cap_reg_sel = st.checkbox(
                "📋 Registros da Equipe de Segurança",
                value=has_perm(row_sel["Permissao"], CAP_REGISTROS),
                key="cap_reg_sel"
            )
            novo_ativo = st.checkbox("✅ Usuário Ativo", value=bool(row_sel["Ativo"]), key="novo_ativo")

        col_pc, col_pd = st.columns(2)
        with col_pc:
            if st.button("💾 Salvar", type="primary", use_container_width=True):
                sel_caps = []
                if cap_editar_sel: sel_caps.append(CAP_EDITAR)
                if cap_reg_sel:    sel_caps.append(CAP_REGISTROS)
                row_u = df_usuarios[df_usuarios["Usuario"] == usuario_sel].iloc[0]
                try:
                    db.update_user(row_u["id"], {
                        "Permissao": permissions_to_string(selected_menus + sel_caps),
                        "Ativo": novo_ativo
                    })
                    st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Usuário atualizado com sucesso!"}
                except Exception as e:
                    st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar: {e}"}
                st.rerun()
        with col_pd:
            if usuario_sel != st.session_state["user"] and usuario_sel != "admin":
                if st.button("🗑️ Remover", use_container_width=True):
                    row_u = df_usuarios[df_usuarios["Usuario"] == usuario_sel].iloc[0]
                    try:
                        db.delete_user(row_u["id"])
                        st.session_state["_notif_banner"] = {"type": "success", "msg": "✅ Usuário removido com sucesso!"}
                    except Exception as e:
                        st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao remover usuário: {e}"}
                    st.rerun()

        st.markdown("---")
        st.subheader("🔑 Redefinir Senha de Usuário")
        usr_troca = st.selectbox("Usuário", df_usuarios["Usuario"].tolist(), key="usr_troca")
        nova_senha_admin = st.text_input("Nova Senha", type="password", key="nova_senha_admin")
        if st.button("Redefinir Senha", use_container_width=True):
            if nova_senha_admin.strip():
                row_t = df_usuarios[df_usuarios["Usuario"] == usr_troca].iloc[0]
                try:
                    db.update_user(row_t["id"], {"Senha_Hash": hash_senha(nova_senha_admin)})
                    st.session_state["_notif_banner"] = {"type": "success", "msg": f"✅ Senha de '{usr_troca}' redefinida com sucesso!"}
                except Exception as e:
                    st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao redefinir senha: {e}"}
                st.rerun()
            else:
                st.warning("Digite a nova senha.")

    with u2:
        st.subheader("➕ Criar Novo Usuário")
        with st.form("form_novo_usuario"):
            n_user  = st.text_input("Login (sem espaços)")
            n_senha = st.text_input("Senha", type="password")
            n_conf  = st.text_input("Confirmar Senha", type="password")
            st.markdown("**Menus autorizados**")
            n_menus = st.multiselect("Menus", MENU_LABELS,
                                     default=["Dashboard", "Notificações"],
                                     label_visibility="collapsed")
            st.markdown("**Permissões especiais**")
            nc_editar    = st.checkbox("✏️ Editar Notificações", value=False)
            nc_registros = st.checkbox("📋 Registros da Equipe de Segurança", value=False)
            criar = st.form_submit_button("✅ Criar Usuário", use_container_width=True)

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
                elif not n_menus:
                    st.error("Selecione ao menos um menu para o usuário.")
                else:
                    n_caps = []
                    if nc_editar:    n_caps.append(CAP_EDITAR)
                    if nc_registros: n_caps.append(CAP_REGISTROS)
                    novo_usr = {
                        "Usuario":      n_user.strip(),
                        "Senha_Hash":   hash_senha(n_senha),
                        "Permissao":    permissions_to_string(n_menus + n_caps),
                        "Ativo":        True,
                        "Data_Criacao": date.today().strftime("%Y-%m-%d"),
                    }
                    try:
                        db.save_user(novo_usr)
                        st.session_state["_notif_banner"] = {"type": "success", "msg": f"✅ Usuário '{n_user.strip()}' criado com sucesso!"}
                    except Exception as e:
                        st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao criar usuário: {e}"}
                    st.rerun()

        st.markdown("---")
        st.markdown("**ℹ️ Permissões Especiais**")
        st.markdown("""
        - **✏️ Editar Notificações**: permite abrir e salvar o formulário de edição de um registro
        - **📋 Registros da Equipe**: permite visualizar, inserir e alterar o status das notificações
        """)
        st.markdown("---")
        st.markdown("**🔑 Login Mestre do Sistema**")
        st.info("O usuário `admin_master` tem acesso irrestrito e não aparece na lista de usuários. Use-o apenas para configuração inicial.")
