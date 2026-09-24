"""
rotinas/layout.py — CSS global, logo, barra lateral e cabeçalho/abas do Painel de Gestão.
"""

import base64
import os

import streamlit as st


def _carregar_b64(nome_arquivo: str) -> str | None:
    """Lê um arquivo de imagem do diretório do projeto e retorna a string base64, ou None se não encontrado."""
    caminho = os.path.join(os.path.dirname(__file__), "..", nome_arquivo)
    if not os.path.exists(caminho):
        caminho = nome_arquivo
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


_LOGO_B64 = _carregar_b64("logo.png")
LOGO_IMG_TAG = (
    f'<img src="data:image/png;base64,{_LOGO_B64}" alt="HGMF" style="height:__H__px; display:block" />'
    if _LOGO_B64 else ""
)

# Ícone/marca do sistema (sino + coração + cruz) — usado no cabeçalho e na
# tela de login. Independente do logo do hospital (LOGO_IMG_TAG), que segue
# usado nos documentos impressos/e-mails oficiais.
_ICON_B64 = _carregar_b64(os.path.join("assets", "notificare_icone.png"))
ICON_IMG_TAG = (
    f'<img src="data:image/png;base64,{_ICON_B64}" alt="NotifiCare" style="height:__H__px; display:block" />'
    if _ICON_B64 else ""
)


def injetar_css_global() -> None:
    """Injeta o CSS global do painel (esconde chrome padrão do Streamlit, estiliza sidebar,
    métricas, cards de incidente, badges e botões)."""
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
    border-radius: 3px;
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
    border-radius: 3px;
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
    border-radius: 3px;
    font-size: 0.74rem;
    font-weight: 600;
    margin-right: 4px;
}
.badge-novo      { background:#e3f2fd; color:#0d47a1; }
.badge-analise   { background:#fff8e1; color:#f57f17; }
.badge-concluido { background:#e8f5e9; color:#2e7d32; }
.badge-anulado   { background:#eceff1; color:#546e7a; }
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
    border-radius: 3px !important;
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


def render_sidebar(perm_label: str) -> None:
    """Renderiza a barra lateral com a identificação do usuário logado."""
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:16px 0 8px;">
          <span style="font-size:2rem;">👤</span>
          <p style="font-weight:700; font-size:1rem; margin:4px 0 2px;">{st.session_state['user']}</p>
          <p style="font-size:0.76rem; opacity:0.7; margin:0;">{perm_label}</p>
        </div>
        """, unsafe_allow_html=True)


def render_cabecalho(menu_items: list[str], perm_label: str) -> str:
    """
    Renderiza o cabeçalho (logo/título + usuário/Sair) com as abas de
    navegação embaixo. Trata o clique em "Sair" (limpa a sessão e reinicia)
    e o clique em cada aba (atualiza menu_modulo e reinicia).

    Retorna o nome do menu atualmente selecionado (st.session_state["menu_modulo"]).
    """
    st.markdown("""
    <style>
    .st-key-painel-header {
        background: linear-gradient(135deg,#082f66 0%,#0d47a1 60%,#1565c0 100%);
        border-radius: 10px;
        padding: 14px 20px 0;
        margin-bottom: 14px;
    }
    .st-key-painel-header div[data-testid="stButton"] button {
        background: rgba(255,255,255,0.12) !important;
        color: #fff !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        border-radius: 7px !important;
    }
    .st-key-painel-header div[data-testid="stButton"] button:hover {
        background: rgba(255,255,255,0.22) !important;
    }
    .st-key-painel-tabs { margin-top: 10px; }
    .st-key-painel-tabs div[data-testid="stButton"] button {
        background: transparent !important;
        color: #d6e6fb !important;
        border: none !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 6px !important;
        white-space: nowrap !important;
        font-size: 0.8rem !important;
    }
    .st-key-painel-tabs div[data-testid="stButton"] button:hover {
        background: rgba(255,255,255,0.12) !important;
        color: #fff !important;
    }
    .st-key-painel-tabs div[data-testid="stButton"] button[kind="primary"] {
        background: #eef1f6 !important;
        color: #0d47a1 !important;
    }
    .st-key-painel-tabs div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #eef1f6 !important;
        color: #0d47a1 !important;
    }
    .st-key-painel-header .st-key-btn_sair div[data-testid="stButton"] button {
        background: linear-gradient(135deg, #f57c00, #ff9800) !important;
        border: none !important;
    }
    .st-key-painel-header .st-key-btn_sair div[data-testid="stButton"] button:hover {
        background: linear-gradient(135deg, #ef6c00, #f57c00) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="painel-header"):
        col_logo, col_titulo, col_user, col_sair = st.columns([0.6, 4, 2.4, 1])
        with col_logo:
            if ICON_IMG_TAG:
                st.markdown(ICON_IMG_TAG.replace("__H__", "44"), unsafe_allow_html=True)
        with col_titulo:
            st.markdown(
                '<div style="color:#fff; font-size:17px; font-weight:800; letter-spacing:0.4px; padding-top:2px">NOTIFICARE</div>'
                '<div style="color:#b9d3f4; font-size:12px">Sistema Integrado de Segurança do Paciente — HGMF</div>',
                unsafe_allow_html=True
            )
        with col_user:
            st.markdown(
                f'<div style="text-align:right; color:#fff; font-size:13px; font-weight:600; padding-top:2px">{st.session_state["user"]}</div>'
                f'<div style="text-align:right; color:#b9d3f4; font-size:11.5px">{perm_label}</div>',
                unsafe_allow_html=True
            )
        with col_sair:
            if st.button("🚪 Sair", use_container_width=True, key="btn_sair"):
                for k in ["logado", "user", "permissao"]:
                    st.session_state[k] = "" if k != "logado" else False
                st.rerun()

        with st.container(key="painel-tabs"):
            tab_cols = st.columns(len(menu_items))
            for _col, _item in zip(tab_cols, menu_items):
                with _col:
                    _ativo = st.session_state["menu_modulo"] == _item
                    if st.button(_item, key=f"tab_{_item}", type=("primary" if _ativo else "secondary"), use_container_width=True):
                        if not _ativo:
                            st.session_state["menu_modulo"] = _item
                            st.rerun()

    return st.session_state["menu_modulo"]
