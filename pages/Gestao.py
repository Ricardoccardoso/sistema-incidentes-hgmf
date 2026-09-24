"""
Gestao.py — Painel de Gestão do sistema de incidentes HGMF

Página protegida por login destinada à equipe do Núcleo de Segurança do Paciente.
Funcionalidades disponíveis conforme permissão do usuário:

  📊 Dashboard        — indicadores e gráficos do período
  📋 Notificações     — lista, detalhe, edição, registros de ação, status e encaminhamento por e-mail
  📈 Relatórios       — análises temáticas (LPP, quedas, medicamentos, etc.)
  📁 Exportar Dados   — download em Excel do período filtrado
  ⚙️ Configurar Menus — gerenciar opções dos selectboxes e campos obrigatórios
  👥 Usuários         — criar, editar permissões e remover usuários

Sistema de permissões:
  - Matriz Tela × Ação ("Ver", "Inserir", "Alterar", "Excluir", "Salvar"), com perfis
    predefinidos (Acesso Total / Apenas Relatórios / Apenas Configurar Tabelas) ou
    combinação livre ("Personalizado"). Armazenada como string "Tela::Ação;..." no
    campo Permissao do usuário (ou o nome do perfil quando coincide com um preset).
  - "Tela::Ver" controla se o menu correspondente aparece na navegação
  - CAP_EDITAR          ("Notificações::Alterar"): exibe botão de edição de registros
  - CAP_INSERIR_REGISTRO ("Notificações::Inserir"): exibe registros da equipe e permite inserir
  - CAP_SALVAR_STATUS    ("Notificações::Salvar"):  permite alterar o status e encaminhar a notificação por e-mail

Encaminhamento por e-mail:
  - Envia a notificação completa (todos os campos + histórico de registros da
    equipe de segurança) via API da SendGrid (https://sendgrid.com), com
    remetente único verificado (não exige domínio próprio)
  - Requer SENDGRID_API_KEY e SENDGRID_FROM_EMAIL configurados nos Secrets do
    Streamlit (seção [sendgrid]); sem isso, exibe aviso claro ao tentar enviar
"""

import os

import streamlit as st
import db  # camada de acesso ao Supabase

from rotinas.constantes import MENU_OPTIONS
from rotinas.permissoes import parse_permissions, rotulo_permissao
from rotinas.autenticacao import tela_login
from rotinas import layout
from rotinas.layout import ICON_IMG_TAG
from telas import dashboard, notificacoes, relatorios, exportar, configurar_menus, usuarios

_favicon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "notificare_icone.png")

st.set_page_config(
    page_title="NotifiCare — HGMF",
    page_icon=_favicon_path if os.path.exists(_favicon_path) else "🔔",
    layout="wide",
    initial_sidebar_state="expanded"
)

layout.injetar_css_global()

# ─── Session state ────────────────────────────────────────────────────────────
# Inicializa as chaves de sessão apenas se ainda não existirem.
# Isso preserva os valores entre reruns sem sobrescrever o estado atual.
#   logado       — True quando o usuário completou o login com sucesso
#   user         — nome de usuário logado
#   permissao    — string de permissão armazenada no banco
for k, v in {
    "logado": False, "user": "", "permissao": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── TELA DE LOGIN ────────────────────────────────────────────────────────────
if not st.session_state["logado"]:
    tela_login(ICON_IMG_TAG)

# ─── PAINEL AUTENTICADO ───────────────────────────────────────────────────────
# A partir daqui o usuário está logado.
# Carrega os dados necessários para todas as abas do painel.
# O banner de notificação (sucesso/erro) é exibido no topo antes de qualquer aba.
df_dados    = db.load_data()   # todos os incidentes registrados
df_config   = db.load_config()
df_usuarios = db.load_users()

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
    if f"{label}::Ver" in user_perms:
        menu_items.append(display)

if not menu_items:
    st.warning("Seu usuário não possui menus autorizados. Contate o administrador.")
    st.stop()

_perm_label = rotulo_permissao(perm)

# Sidebar — apenas identificação do usuário (informativo, opcional no celular)
layout.render_sidebar(_perm_label)

# Navegação disparada programaticamente (ex: clique em alerta ou na matriz do dashboard)
if "_ir_para_menu" in st.session_state:
    _alvo_menu = st.session_state.pop("_ir_para_menu")
    if _alvo_menu in menu_items:
        st.session_state["menu_modulo"] = _alvo_menu
if st.session_state.get("menu_modulo") not in menu_items:
    st.session_state["menu_modulo"] = menu_items[0]

# ── Cabeçalho: logo/título + usuário/Sair, com abas de navegação embaixo ──────
menu = layout.render_cabecalho(menu_items, _perm_label)

# ══════════════════════════════════════════════════════════════════════════════
# Despacha para a tela selecionada
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📊 Dashboard":
    dashboard.render(df_dados)
elif menu == "📋 Notificações":
    notificacoes.render(df_dados, df_config, perm)
elif menu == "📈 Relatórios":
    relatorios.render(df_dados)
elif menu == "📁 Exportar Dados":
    exportar.render(df_dados)
elif menu == "⚙️ Configurar Menus":
    configurar_menus.render(df_config)
elif menu == "👥 Usuários":
    usuarios.render(df_usuarios)
