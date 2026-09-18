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
  - Matriz Tela × Ação ("Ver", "Inserir", "Alterar", "Excluir", "Salvar"), com perfis
    predefinidos (Acesso Total / Apenas Relatórios / Apenas Configurar Tabelas) ou
    combinação livre ("Personalizado"). Armazenada como string "Tela::Ação;..." no
    campo Permissao do usuário (ou o nome do perfil quando coincide com um preset).
  - "Tela::Ver" controla se o menu correspondente aparece na navegação
  - CAP_EDITAR          ("Notificações::Alterar"): exibe botão de edição de registros
  - CAP_INSERIR_REGISTRO ("Notificações::Inserir"): exibe registros da equipe e permite inserir
  - CAP_SALVAR_STATUS    ("Notificações::Salvar"):  permite alterar o status da notificação
"""

import streamlit as st
import streamlit.components.v1 as components  # necessário para injetar JS de impressão
import pandas as pd
import altair as alt
import hashlib
import html as html_mod
import json as _json_mod
import base64
import os
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

# ─── Logo (embutido em base64 — evita depender de arquivos estáticos servidos) ─
def _carregar_logo_b64():
    """Lê logo.png do diretório do script e retorna a string base64, ou None se não encontrado."""
    caminho = os.path.join(os.path.dirname(__file__), "..", "logo.png")
    if not os.path.exists(caminho):
        caminho = "logo.png"
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

_LOGO_B64 = _carregar_logo_b64()
LOGO_IMG_TAG = (
    f'<img src="data:image/png;base64,{_LOGO_B64}" alt="HGMF" style="height:__H__px; display:block" />'
    if _LOGO_B64 else ""
)

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

STATUS_OPTS    = ["Novo", "Investigar", "Notificar", "Em Análise", "Pendência", "Concluído", "Anulado"]
MENU_OPTIONS   = [
    ("📊 Dashboard", "Dashboard"),
    ("📋 Notificações", "Notificações"),
    ("📈 Relatórios", "Relatórios"),
    ("📁 Exportar Dados", "Exportar Dados"),
    ("⚙️ Configurar Menus", "Configurar Menus"),
    ("👥 Usuários", "Usuários"),
]
MENU_LABELS    = [label for _, label in MENU_OPTIONS]

# ─── Matriz de permissões: Tela × Ação ────────────────────────────────────────
# Cada permissão é armazenada como token "Tela::Ação" (ex: "Notificações::Alterar").
ACOES_PERM = ["Ver", "Inserir", "Alterar", "Excluir", "Salvar"]

APLICAVEL_PERM = {
    "Dashboard":         ["Ver"],
    "Notificações":      ["Ver", "Inserir", "Alterar", "Excluir", "Salvar"],
    "Relatórios":        ["Ver", "Salvar"],
    "Exportar Dados":    ["Ver", "Salvar"],
    "Configurar Menus":  ["Ver", "Inserir", "Alterar", "Excluir", "Salvar"],
    "Usuários":          ["Ver", "Inserir", "Alterar", "Excluir", "Salvar"],
}
TELAS_PERM = MENU_LABELS


def _tokens_tela(tela):
    """Retorna todos os tokens 'Tela::Ação' aplicáveis a uma tela."""
    return [f"{tela}::{acao}" for acao in APLICAVEL_PERM.get(tela, [])]


def _tokens_perfil(mapa):
    """Expande um mapa {Tela: [Ações]} em uma lista de tokens 'Tela::Ação'."""
    tokens = []
    for tela, acoes in mapa.items():
        tokens += [f"{tela}::{acao}" for acao in acoes]
    return tokens


PRESET_PERMISSIONS = {
    "Acesso Total": [tok for tela in TELAS_PERM for tok in _tokens_tela(tela)],
    "Apenas Relatórios": _tokens_perfil({
        "Dashboard": ["Ver"],
        "Relatórios": ["Ver", "Salvar"],
        "Exportar Dados": ["Ver", "Salvar"],
    }),
    "Apenas Configurar Tabelas": _tokens_perfil({
        "Dashboard": ["Ver"],
        "Configurar Menus": ["Ver", "Inserir", "Alterar", "Excluir", "Salvar"],
    }),
}
PERM_LABELS = list(PRESET_PERMISSIONS.keys())

# Capacidades especiais usadas dentro da aba Notificações
CAP_EDITAR            = "Notificações::Alterar"
CAP_INSERIR_REGISTRO  = "Notificações::Inserir"
CAP_SALVAR_STATUS     = "Notificações::Salvar"
CAP_EXCLUIR_NOTIF     = "Notificações::Excluir"

# Tokens legados (formato anterior à matriz) — mantidos para migrar permissões
# já salvas no banco sem exigir alteração manual dos usuários existentes.
_LEGACY_CAP_EDITAR    = "cap_editar_notificacoes"
_LEGACY_CAP_REGISTROS = "cap_registros_equipe"


def _migrar_permissoes_legado(itens):
    """
    Converte uma lista de tokens no formato antigo (nomes de menu soltos +
    capacidades cap_editar_notificacoes/cap_registros_equipe) para o novo
    formato de tokens "Tela::Ação".
    """
    tokens = set()
    for item in itens:
        if item in MENU_LABELS:
            tokens.add(f"{item}::Ver")
        elif item == _LEGACY_CAP_EDITAR:
            tokens.add(CAP_EDITAR)
        elif item == _LEGACY_CAP_REGISTROS:
            tokens.add(CAP_INSERIR_REGISTRO)
            tokens.add(CAP_SALVAR_STATUS)
    return tokens


def parse_permissions(value):
    """
    Converte o campo Permissao (string) no conjunto de tokens "Tela::Ação" ativos.

    Aceita:
      - Strings predefinidas ("Acesso Total", etc.) → expande via PRESET_PERMISSIONS
      - Strings semicolon-separated no formato novo ("Dashboard::Ver;Notificações::Alterar")
      - Strings semicolon-separated no formato antigo (menus soltos + capacidades legadas)
        → migradas automaticamente para o novo formato
      - Qualquer outro valor → conjunto vazio

    Retorna um set de strings "Tela::Ação".
    """
    if value in PRESET_PERMISSIONS:
        return set(PRESET_PERMISSIONS[value])
    if not isinstance(value, str) or not value.strip():
        return set()
    itens = [item.strip() for item in value.split(";") if item.strip()]
    if any("::" in item for item in itens):
        return set(itens)
    return _migrar_permissoes_legado(itens)


def permissions_to_string(tokens):
    """
    Converte um conjunto/lista de tokens "Tela::Ação" de volta para string
    armazenável no banco.

    Se o conjunto coincidir exatamente com um dos perfis predefinidos, retorna
    o nome compacto do perfil (ex: "Acesso Total"). Caso contrário, junta os
    tokens com ";" (permissão "Personalizada").

    Parâmetros:
      tokens — coleção de strings "Tela::Ação"
    """
    tokens = set(tokens)
    for nome, preset_tokens in PRESET_PERMISSIONS.items():
        if tokens == set(preset_tokens):
            return nome
    return ";".join(sorted(tokens))


def has_perm(perm_str, token):
    """
    Verifica se uma string de permissão contém um token específico.

    Parâmetros:
      perm_str — string armazenada no banco (ex: "Acesso Total" ou "Dashboard::Ver;Notificações::Alterar")
      token    — token a verificar (ex: CAP_EDITAR, "Dashboard::Ver")

    Retorna True se o token estiver presente, False caso contrário.
    """
    return token in parse_permissions(perm_str)


def rotulo_permissao(perm_str):
    """Retorna o nome do perfil predefinido correspondente, ou 'Personalizado'."""
    tokens = parse_permissions(perm_str)
    if not tokens:
        return "Sem permissões"
    for nome, preset_tokens in PRESET_PERMISSIONS.items():
        if tokens == set(preset_tokens):
            return nome
    return "Personalizado"


def _tokens_aplicaveis_todos():
    """Lista todos os tokens 'Tela::Ação' aplicáveis, na ordem da matriz de permissões."""
    return [f"{tela}::{acao}" for tela in TELAS_PERM for acao in APLICAVEL_PERM.get(tela, [])]


def seed_checkbox_matriz(tokens_ativos):
    """
    Pré-popula st.session_state para os checkboxes da matriz de permissões
    (chaves "chk_<token>") a partir de um conjunto de tokens ativos.

    Necessário porque st.checkbox com `key` fixo ignora o parâmetro `value`
    em reruns subsequentes — a única forma confiável de "resetar" a grade
    (ex: ao trocar de perfil ou trocar de usuário em edição) é escrever
    diretamente em st.session_state ANTES do próximo st.rerun().
    """
    ativos = set(tokens_ativos)
    for tok in _tokens_aplicaveis_todos():
        st.session_state[f"chk_{tok}"] = tok in ativos


def matriz_atual_selecionada():
    """Lê o estado atual da grade de permissões diretamente de st.session_state."""
    return {tok for tok in _tokens_aplicaveis_todos() if st.session_state.get(f"chk_{tok}", False)}

CAMPO_LABELS = {
    "Acoes_Imediatas":      "Ações Imediatas",
    "Categoria_Incidente":  "Categoria do Incidente",
    "Data_Incidente":       "Data do Incidente",
    "Data_Nascimento":      "Data de Nascimento",
    "Data_Internacao":      "Data de Internação / Atendimento",
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


def gerar_html_impressao(df_rows: pd.DataFrame, df_registros: pd.DataFrame | None = None) -> str:
    """
    Gera um documento HTML formatado para impressão/PDF de uma ou mais notificações.

    O HTML inclui:
      - Cabeçalho com nome do hospital e data de geração
      - Uma seção por notificação com todos os campos relevantes
      - Tabela de registros da equipe de segurança (se df_registros for fornecido)
      - CSS de impressão (A4, page-break-inside:avoid)
      - Botão fixo "Imprimir / Salvar PDF" que aciona window.print()

    Todos os valores são escapados via html.escape() para evitar XSS.

    Parâmetros:
      df_rows      — DataFrame com uma ou mais linhas de incidentes
      df_registros — DataFrame com os registros de ação da equipe (opcional)

    Retorna string HTML pronta para download ou exibição.
    """
    def esc(v):
        """Escapa caracteres HTML especiais para evitar XSS no documento gerado."""
        return html_mod.escape(str(v or "—"))

    # Monta tabela de registros da equipe de segurança
    bloco_registros = ""
    if df_registros is not None and not df_registros.empty:
        linhas_reg = ""
        for _, reg in df_registros.iterrows():
            data_hora = str(reg.get("Data_Registro", ""))[:16]
            usuario   = esc(reg.get("Usuario", "—"))
            descricao = esc(reg.get("Descricao", "—"))
            linhas_reg += f"""
            <tr>
              <td style="white-space:nowrap;width:120px">{data_hora}</td>
              <td style="white-space:nowrap;width:110px">{usuario}</td>
              <td>{descricao}</td>
            </tr>"""
        bloco_registros = f"""
        <div class="secao-reg">
          <div class="reg-titulo">📋 Registros da Equipe de Segurança</div>
          <table class="tabela-reg">
            <thead>
              <tr>
                <th>Data / Hora</th>
                <th>Usuário</th>
                <th>Descrição da Ação</th>
              </tr>
            </thead>
            <tbody>{linhas_reg}</tbody>
          </table>
        </div>"""

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
          {bloco_registros}
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
  .secao-reg {{ margin:10px 0 6px 0; }}
  .reg-titulo {{ font-size:10px; font-weight:700; text-transform:uppercase; color:#0d47a1;
                 letter-spacing:0.8px; margin-bottom:5px; padding-left:2px; }}
  .tabela-reg {{ width:100%; border-collapse:collapse; font-size:10px; }}
  .tabela-reg th {{ background:#e8f0fe; color:#0d47a1; font-weight:700; text-align:left;
                    padding:5px 8px; border:1px solid #c8d8f0; font-size:9px;
                    text-transform:uppercase; letter-spacing:0.5px; }}
  .tabela-reg td {{ padding:5px 8px; border:1px solid #dde; vertical-align:top; }}
  .tabela-reg tbody tr:nth-child(even) {{ background:#f5f8ff; }}
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
    _logo_login = LOGO_IMG_TAG.replace("__H__", "52").replace(
        'style="', 'style="margin:0 auto 12px; '
    ) if LOGO_IMG_TAG else '<span style="font-size:2.8rem;">🔒</span>'
    st.markdown(f"""
    <div style="max-width:400px; margin:60px auto 0 auto;">
      <div style="text-align:center; margin-bottom:28px;">
        {_logo_login}
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

            # ── Recuperação de senha ──────────────────────────────────────
            # Fluxo apenas informativo: registra a intenção na tela e orienta
            # o usuário a aguardar contato do administrador. Nada é persistido.
            col_esq_a, col_esq_b, col_esq_c = st.columns([1, 2, 1])
            with col_esq_b:
                if st.button("Esqueceu a senha?", use_container_width=True, key="btn_esqueci_senha"):
                    st.session_state["mostrar_recuperacao"] = not st.session_state.get("mostrar_recuperacao", False)
                    st.session_state["recuperacao_enviada"] = False
                    st.session_state["erro_recuperacao"] = False

            if st.session_state.get("mostrar_recuperacao"):
                st.markdown("---")
                if st.session_state.get("recuperacao_enviada"):
                    st.success(
                        "Solicitação registrada. O administrador do sistema foi avisado e "
                        f"entrará em contato para redefinir a senha do usuário "
                        f"**{st.session_state.get('recuperacao_usuario', '')}**."
                    )
                    if st.button("Voltar ao login", key="btn_voltar_login"):
                        st.session_state["mostrar_recuperacao"] = False
                        st.session_state["recuperacao_enviada"] = False
                        st.rerun()
                else:
                    st.markdown("**Recuperar acesso**")
                    st.caption(
                        "Informe seu usuário. O Núcleo de Segurança do Paciente valida a "
                        "solicitação e envia uma senha provisória."
                    )
                    rec_usuario = st.text_input(
                        "Seu usuário",
                        value=st.session_state.get("recuperacao_usuario", ""),
                        key="rec_usuario_input"
                    )
                    if st.session_state.get("erro_recuperacao"):
                        st.error("Informe o usuário para continuar.")
                    col_rec1, col_rec2 = st.columns(2)
                    with col_rec1:
                        if st.button("Solicitar redefinição", use_container_width=True, key="btn_solicitar_rec"):
                            if rec_usuario.strip():
                                st.session_state["recuperacao_usuario"] = rec_usuario.strip()
                                st.session_state["recuperacao_enviada"] = True
                                st.session_state["erro_recuperacao"] = False
                            else:
                                st.session_state["erro_recuperacao"] = True
                            st.rerun()
                    with col_rec2:
                        if st.button("Cancelar", use_container_width=True, key="btn_cancelar_rec"):
                            st.session_state["mostrar_recuperacao"] = False
                            st.session_state["erro_recuperacao"] = False
                            st.rerun()
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
    if f"{label}::Ver" in user_perms:
        menu_items.append(display)

if not menu_items:
    st.warning("Seu usuário não possui menus autorizados. Contate o administrador.")
    st.stop()

_perm_label = rotulo_permissao(perm)

# Sidebar — apenas identificação do usuário (informativo, opcional no celular)
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 8px;">
      <span style="font-size:2rem;">👤</span>
      <p style="font-weight:700; font-size:1rem; margin:4px 0 2px;">{st.session_state['user']}</p>
      <p style="font-size:0.76rem; opacity:0.7; margin:0;">{_perm_label}</p>
    </div>
    """, unsafe_allow_html=True)

# Navegação disparada programaticamente (ex: clique em alerta ou na matriz do dashboard)
if "_ir_para_menu" in st.session_state:
    _alvo_menu = st.session_state.pop("_ir_para_menu")
    if _alvo_menu in menu_items:
        st.session_state["menu_modulo"] = _alvo_menu
if st.session_state.get("menu_modulo") not in menu_items:
    st.session_state["menu_modulo"] = menu_items[0]

# ── Cabeçalho: logo/título + usuário/Sair, com abas de navegação embaixo ──────
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
</style>
""", unsafe_allow_html=True)

with st.container(key="painel-header"):
    col_logo, col_titulo, col_user, col_sair = st.columns([0.6, 4, 2.4, 1])
    with col_logo:
        if LOGO_IMG_TAG:
            st.markdown(LOGO_IMG_TAG.replace("__H__", "38"), unsafe_allow_html=True)
    with col_titulo:
        st.markdown(
            '<div style="color:#fff; font-size:15px; font-weight:700; padding-top:2px">Painel de Gestão — HGMF</div>'
            '<div style="color:#b9d3f4; font-size:12px">Núcleo de Segurança do Paciente</div>',
            unsafe_allow_html=True
        )
    with col_user:
        st.markdown(
            f'<div style="text-align:right; color:#fff; font-size:13px; font-weight:600; padding-top:2px">{st.session_state["user"]}</div>'
            f'<div style="text-align:right; color:#b9d3f4; font-size:11.5px">{_perm_label}</div>',
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

menu = st.session_state["menu_modulo"]

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

    # ── Alertas: notificações novas aguardando triagem ─────────────────────
    # "Vistas" fica apenas na sessão do usuário — reflete o comportamento do
    # protótipo, sem gravar nada no banco.
    alertas_vistos = st.session_state.setdefault("alertas_vistos", set())
    df_alertas = df_dados[
        (df_dados["Status"].fillna("Novo") == "Novo") & (~df_dados["id"].isin(alertas_vistos))
    ].sort_values("Data_Registro", ascending=False)

    if not df_alertas.empty:
        # Mostra só os mais recentes: com muitas notificações "Novo" acumuladas,
        # renderizar um card+botões por item deixava a página inteira lenta.
        # "Marcar todas como vistas" continua operando sobre o conjunto completo.
        _LIMITE_ALERTAS = 8
        df_alertas_exibir = df_alertas.head(_LIMITE_ALERTAS)
        _restantes = len(df_alertas) - len(df_alertas_exibir)

        with st.container(border=True):
            col_al1, col_al2 = st.columns([5, 2])
            with col_al1:
                st.markdown(f"🔔 **{len(df_alertas)}** notificações novas aguardando triagem")
            with col_al2:
                if st.button("Marcar todas como vistas", use_container_width=True, key="btn_dispensar_todos_alertas"):
                    st.session_state["alertas_vistos"] = alertas_vistos | set(df_alertas["id"].tolist())
                    st.rerun()

            for _, arow in df_alertas_exibir.iterrows():
                a_id = arow.get("id")
                titulo = str(arow.get("Categoria_Incidente", "—"))
                if arow.get("Subcategoria"):
                    titulo += f" — {arow.get('Subcategoria')}"
                meta = (
                    f"{str(arow.get('Data_Incidente',''))[:10]} · {arow.get('Setor','—')} · "
                    f"{arow.get('Gravidade','')} · registrada em {str(arow.get('Data_Registro',''))[:16]}"
                )
                ca1, ca2, ca3 = st.columns([5, 2, 1])
                with ca1:
                    st.markdown(
                        f"**{titulo}**  \n"
                        f"<span style='font-size:0.8rem;color:#5f7086'>{meta}</span>",
                        unsafe_allow_html=True
                    )
                with ca2:
                    if st.button("Abrir notificação", key=f"abrir_alerta_{a_id}", use_container_width=True):
                        st.session_state["_ir_para_menu"] = "📋 Notificações"
                        st.session_state["_nav_filtro"] = {
                            "categoria": arow.get("Categoria_Incidente"),
                            "gravidade": arow.get("Gravidade"),
                            "status": "Todos",
                        }
                        st.session_state["_force_open_id"] = a_id
                        st.session_state["alertas_vistos"] = alertas_vistos | {a_id}
                        st.rerun()
                with ca3:
                    if st.button("Visto", key=f"visto_alerta_{a_id}", use_container_width=True):
                        st.session_state["alertas_vistos"] = alertas_vistos | {a_id}
                        st.rerun()

            if _restantes > 0:
                st.caption(
                    f"+ {_restantes} notificação(ões) adicional(is) — "
                    "veja a aba Notificações filtrando por Status = Novo."
                )

    # ── Filtro de período ──────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🗓️ Filtro de Período</div>', unsafe_allow_html=True)

    # Data mínima disponível no banco (ou 2020 como fallback)
    _datas_validas = df_dados["Data_Incidente"].dropna()
    _data_min = _datas_validas.min().date() if not _datas_validas.empty else date(2020, 1, 1)

    cf1, cf2, cf3 = st.columns([2, 2, 2])
    with cf1:
        data_ini = st.date_input("De", value=_data_min, format="DD/MM/YYYY")
    with cf2:
        data_fim = st.date_input("Até", value=date.today(), format="DD/MM/YYYY")
    with cf3:
        filtro_setor = st.selectbox("Setor", ["Todos"] + sorted(df_dados["Setor"].dropna().unique().tolist()))

    # Inclui registros sem Data_Incidente (NaT) e os que estão dentro do período
    _sem_data = df_dados["Data_Incidente"].isna()
    _no_periodo = (
        (df_dados["Data_Incidente"] >= pd.to_datetime(data_ini)) &
        (df_dados["Data_Incidente"] <= pd.to_datetime(data_fim))
    )
    df_f = df_dados[_sem_data | _no_periodo].copy()
    if filtro_setor != "Todos":
        df_f = df_f[df_f["Setor"] == filtro_setor]
    df_f = df_f[df_f["Status"].fillna("") != "Anulado"]

    st.caption(f"Exibindo **{len(df_f)}** notificações no período selecionado.")

    # ── KPIs por Gravidade ────────────────────────────────────────────────
    # Mostra a distribuição completa da escala de dano — do Near Miss ao Óbito
    st.markdown('<div class="secao-titulo">⚠️ Indicadores por Gravidade</div>', unsafe_allow_html=True)
    kg1, kg2, kg3, kg4, kg5, kg6 = st.columns(6)
    kg1.metric("Total",          len(df_f))
    kg2.metric("Near Miss",      len(df_f[df_f["Gravidade"].str.contains("Near",      na=False)]))
    kg3.metric("Sem Dano",       len(df_f[df_f["Gravidade"].str.contains("Sem Dano",  na=False)]))
    kg4.metric("Dano Leve",      len(df_f[df_f["Gravidade"].str.contains("Leve",      na=False)]))
    kg5.metric("Dano Moderado",  len(df_f[df_f["Gravidade"].str.contains("Moderado",  na=False)]))
    kg6.metric("Grave / Óbito",  len(df_f[df_f["Gravidade"].str.contains("Grave|Óbito", na=False, regex=True)]))

    # ── KPIs por Categoria ────────────────────────────────────────────────
    # Total + 5 categorias clínicas prioritárias + Outras (tudo que não se encaixa nas 5)
    st.markdown('<div class="secao-titulo">🏷️ Indicadores por Categoria</div>', unsafe_allow_html=True)
    _cat = df_f["Categoria_Incidente"].fillna("")
    _lpp   = _cat.str.contains("Pressão|LPP",   regex=True)
    _queda = _cat.str.contains("Queda")
    _med   = _cat.str.contains("Medic")
    _ident = _cat.str.contains("Identif")
    _inf   = _cat.str.contains("Infecção|IRAS", regex=True)
    _outras = ~(_lpp | _queda | _med | _ident | _inf) & (_cat != "")
    kc1, kc2, kc3, kc4, kc5, kc6, kc7 = st.columns(7)
    kc1.metric("Total",         len(df_f))
    kc2.metric("LPP",           int(_lpp.sum()))
    kc3.metric("Quedas",        int(_queda.sum()))
    kc4.metric("Medicamentos",  int(_med.sum()))
    kc5.metric("Identificação", int(_ident.sum()))
    kc6.metric("Infecção",      int(_inf.sum()))
    kc7.metric("Outras",        int(_outras.sum()))

    # ── Matriz: nível de incidente por categoria ────────────────────────────
    # Cada célula é um botão que leva à aba Notificações já filtrada.
    st.markdown('<div class="secao-titulo">🧩 Nível de Incidente por Categoria</div>', unsafe_allow_html=True)
    st.caption("Clique em um número para abrir a aba Notificações já filtrada por aquela categoria e gravidade.")

    _GRAV_BUCKETS = [
        ("Near Miss", "Near"),
        ("Sem Dano", "Sem Dano"),
        ("Dano Leve", "Leve"),
        ("Dano Moderado", "Moderado"),
        ("Dano Grave", "Grave"),
        ("Óbito", "Óbito"),
    ]

    def _valor_gravidade_real(serie, padrao):
        for v in serie.dropna().unique().tolist():
            if padrao.lower() in str(v).lower():
                return v
        return None

    _cats_presentes = df_f["Categoria_Incidente"].dropna().value_counts().index.tolist()

    if _cats_presentes:
        _grid_ratio = [2.2] + [1] * len(_GRAV_BUCKETS) + [1]
        _hcols = st.columns(_grid_ratio)
        _hcols[0].markdown("**Categoria**")
        for _i, (_nome_curto, _) in enumerate(_GRAV_BUCKETS):
            _hcols[_i + 1].markdown(
                f"<div style='text-align:center;font-size:0.72rem;font-weight:700;color:#0d47a1'>{_nome_curto}</div>",
                unsafe_allow_html=True
            )
        _hcols[-1].markdown(
            "<div style='text-align:center;font-size:0.72rem;font-weight:700;color:#0d47a1'>Total</div>",
            unsafe_allow_html=True
        )

        for _cat in _cats_presentes:
            _df_cat_row = df_f[df_f["Categoria_Incidente"] == _cat]
            _rcols = st.columns(_grid_ratio)
            _rcols[0].markdown(f"<div style='font-size:0.85rem;padding-top:6px'>{_cat}</div>", unsafe_allow_html=True)
            for _i, (_nome_curto, _padrao) in enumerate(_GRAV_BUCKETS):
                _qtd = int(_df_cat_row["Gravidade"].str.contains(_padrao, case=False, na=False).sum())
                with _rcols[_i + 1]:
                    if _qtd:
                        if st.button(str(_qtd), key=f"mtx_{_cat}_{_nome_curto}", use_container_width=True):
                            _grav_real = _valor_gravidade_real(_df_cat_row["Gravidade"], _padrao)
                            st.session_state["_ir_para_menu"] = "📋 Notificações"
                            st.session_state["_nav_filtro"] = {
                                "categoria": _cat, "gravidade": _grav_real or "Todas", "status": "Todos"
                            }
                            st.rerun()
                    else:
                        st.markdown("<div style='text-align:center;color:#c2ccd7'>—</div>", unsafe_allow_html=True)
            with _rcols[-1]:
                _total_cat = len(_df_cat_row)
                if st.button(str(_total_cat), key=f"mtx_total_{_cat}", use_container_width=True):
                    st.session_state["_ir_para_menu"] = "📋 Notificações"
                    st.session_state["_nav_filtro"] = {"categoria": _cat, "gravidade": "Todas", "status": "Todos"}
                    st.rerun()

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
        chart_sem = alt.Chart(df_sem).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#1565c0").encode(
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
        s1, s2, s3, s4, s5, s6, s7 = st.columns(7)
        for col_k, status_n in zip([s1, s2, s3, s4, s5, s6, s7], STATUS_OPTS):
            qtd = int(df_status[df_status["Status"] == status_n]["Qtd"].sum()) if not df_status.empty else 0
            col_k.metric(status_n, qtd)

# ══════════════════════════════════════════════════════════════════════════════
# ABA: NOTIFICAÇÕES
# Lista todas as notificações com filtros por status, categoria, setor e gravidade.
# Cada notificação exibe um card resumido e um expander com:
#   - Dados completos do evento e paciente
#   - Botão de impressão individual (gera HTML/PDF para download)
#   - Formulário de edição (se CAP_EDITAR)
#   - Registros de ação da equipe de segurança (se CAP_INSERIR_REGISTRO)
#   - Alteração de status (se CAP_SALVAR_STATUS)
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📋 Notificações":
    st.title("📋 Gerenciamento de Notificações")

    if df_dados.empty:
        st.info("Nenhuma notificação registrada.")
        st.stop()

    df_dados["Data_Incidente"] = pd.to_datetime(df_dados["Data_Incidente"], errors="coerce")

    # Navegação vinda dos alertas ou da matriz do Dashboard: pré-seleciona os
    # filtros e guarda o id da notificação a abrir automaticamente.
    _nav_filtro = st.session_state.pop("_nav_filtro", None)
    _force_open_id = st.session_state.pop("_force_open_id", None)
    if _nav_filtro:
        if _nav_filtro.get("status"):
            st.session_state["notif_f_status"] = _nav_filtro["status"]
        if _nav_filtro.get("categoria"):
            st.session_state["notif_f_cat"] = _nav_filtro["categoria"]
        if _nav_filtro.get("gravidade"):
            st.session_state["notif_f_grav"] = _nav_filtro["gravidade"]

    # Filtros
    st.markdown('<div class="secao-titulo">🔎 Filtros</div>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_status = st.selectbox("Status", ["Todos"] + STATUS_OPTS, key="notif_f_status")
    with fc2:
        cats = ["Todas"] + sorted(df_dados["Categoria_Incidente"].dropna().unique().tolist())
        f_cat = st.selectbox("Categoria", cats, key="notif_f_cat")
    with fc3:
        setos = ["Todos"] + sorted(df_dados["Setor"].dropna().unique().tolist())
        f_set = st.selectbox("Setor", setos, key="notif_f_set")
    with fc4:
        gravs = ["Todas"] + sorted(df_dados["Gravidade"].dropna().unique().tolist())
        f_grav = st.selectbox("Gravidade", gravs, key="notif_f_grav")

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
            "Novo":       "badge-novo",
            "Investigar": "badge-analise", "Notificar": "badge-critico",
            "Em Análise": "badge-analise", "Pendência": "badge-critico",
            "Concluído": "badge-concluido",
            "Anulado": "badge-anulado"
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

        _expandir = _force_open_id is not None and row.get("id") == _force_open_id
        with st.expander(f"Ver detalhes e gerenciar — Notificação #{idx+1}", expanded=_expandir):
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
                st.write(f"- Internação / Atendimento: {str(row.get('Data_Internacao',''))[:10]}")
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
                # Carrega registros da equipe para incluir na impressão
                _df_reg_print = db.load_registros_acao(row.get("id"))
                st.session_state[f"_print_html_{idx}"] = gerar_html_impressao(
                    pd.DataFrame([row.to_dict()]),
                    df_registros=_df_reg_print if not _df_reg_print.empty else None
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
            if has_perm(perm, CAP_INSERIR_REGISTRO):
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
            if has_perm(perm, CAP_SALVAR_STATUS):
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
    df_dados = df_dados[df_dados["Status"].fillna("") != "Anulado"].copy()

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
            df_nm_set = df_nm["Setor"].value_counts().reset_index()
            df_nm_set.columns = ["Setor", "Qtd"]
            chart = alt.Chart(df_nm_set).mark_bar(cornerRadiusTopRight=3, cornerRadiusTopLeft=3, color="#7b1fa2").encode(
                x=alt.X("Setor:N", sort="-y", title=""),
                y=alt.Y("Qtd:Q", title="Ocorrências"),
                tooltip=["Setor", "Qtd"]
            ).properties(height=260)
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(df_nm[["Data_Incidente","Setor","Categoria_Incidente","Fatores_Causadores","Descricao"]],
                         use_container_width=True, hide_index=True)

    elif tipo_rel == "Incidentes com Dano Grave ou Óbito":
        df_gr = df_dados[df_dados["Gravidade"].str.contains("Grave|Óbito", na=False, regex=True)].copy()
        st.metric("Total de Incidentes Graves", len(df_gr))
        if not df_gr.empty:
            gra1, gra2 = st.columns(2)
            with gra1:
                df_gr_set = df_gr["Setor"].value_counts().reset_index()
                df_gr_set.columns = ["Setor", "Qtd"]
                chart = alt.Chart(df_gr_set).mark_bar(cornerRadiusTopRight=3, color="#c62828").encode(
                    x=alt.X("Qtd:Q", title="Ocorrências"),
                    y=alt.Y("Setor:N", sort="-x", title=""),
                    tooltip=["Setor", "Qtd"]
                ).properties(height=260)
                st.altair_chart(chart, use_container_width=True)
            with gra2:
                df_gr_cat = df_gr["Categoria_Incidente"].value_counts().reset_index()
                df_gr_cat.columns = ["Categoria", "Qtd"]
                chart2 = alt.Chart(df_gr_cat).mark_bar(cornerRadiusTopRight=3, color="#b71c1c").encode(
                    x=alt.X("Qtd:Q", title="Ocorrências"),
                    y=alt.Y("Categoria:N", sort="-x", title=""),
                    tooltip=["Categoria", "Qtd"]
                ).properties(height=260)
                st.altair_chart(chart2, use_container_width=True)
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
                chart_q1 = alt.Chart(df_tipo_queda).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#f57f17").encode(
                    x=alt.X("Tipo:N", sort="-y", title=""),
                    y=alt.Y("Qtd:Q", title="Ocorrências"),
                    tooltip=["Tipo", "Qtd"]
                ).properties(height=240)
                st.altair_chart(chart_q1, use_container_width=True)
                st.dataframe(df_tipo_queda, use_container_width=True, hide_index=True)
            with col_qb:
                df_queda_set = df_q["Setor"].value_counts().reset_index()
                df_queda_set.columns = ["Setor", "Qtd"]
                chart_q2 = alt.Chart(df_queda_set).mark_bar(cornerRadiusTopRight=3, color="#e65100").encode(
                    x=alt.X("Qtd:Q", title="Ocorrências"),
                    y=alt.Y("Setor:N", sort="-x", title=""),
                    tooltip=["Setor", "Qtd"]
                ).properties(height=240)
                st.altair_chart(chart_q2, use_container_width=True)
                st.dataframe(df_queda_set, use_container_width=True, hide_index=True)

    elif tipo_rel == "Análise Medicamentosa":
        df_med = df_dados[df_dados["Categoria_Incidente"].str.contains("Medic|Medicament", na=False)].copy()
        st.metric("Total Falhas Medicamentosas", len(df_med))
        if not df_med.empty:
            med1, med2 = st.columns(2)
            with med1:
                df_med_sub = df_med["Subcategoria"].value_counts().reset_index()
                df_med_sub.columns = ["Tipo de Falha", "Qtd"]
                chart_med = alt.Chart(df_med_sub).mark_bar(cornerRadiusTopRight=3, color="#1565c0").encode(
                    x=alt.X("Qtd:Q", title="Ocorrências"),
                    y=alt.Y("Tipo de Falha:N", sort="-x", title=""),
                    tooltip=["Tipo de Falha", "Qtd"]
                ).properties(height=240)
                st.altair_chart(chart_med, use_container_width=True)
            with med2:
                df_med_set = df_med["Setor"].value_counts().reset_index()
                df_med_set.columns = ["Setor", "Qtd"]
                chart_med2 = alt.Chart(df_med_set).mark_bar(cornerRadiusTopRight=3, color="#0288d1").encode(
                    x=alt.X("Qtd:Q", title="Ocorrências"),
                    y=alt.Y("Setor:N", sort="-x", title=""),
                    tooltip=["Setor", "Qtd"]
                ).properties(height=240)
                st.altair_chart(chart_med2, use_container_width=True)
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
        data_ini_e = st.date_input("De", value=(date.today() - timedelta(days=90)), key="exp_ini", format="DD/MM/YYYY")
    with e2:
        data_fim_e = st.date_input("Até", value=date.today(), key="exp_fim", format="DD/MM/YYYY")

    df_dados["Data_Incidente"] = pd.to_datetime(df_dados["Data_Incidente"], errors="coerce")
    df_exp = df_dados[
        (df_dados["Data_Incidente"] >= pd.to_datetime(data_ini_e)) &
        (df_dados["Data_Incidente"] <= pd.to_datetime(data_fim_e))
    ].copy()
    df_exp = df_exp[df_exp["Status"].fillna("") != "Anulado"]

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

        # Para Gravidade: garante coluna Ordem no DataFrame mesmo antes do SQL migration
        if tab_sel == "Gravidade":
            if "Ordem" not in df_ed.columns:
                df_ed["Ordem"] = 0
            df_ed["Ordem"] = pd.to_numeric(df_ed["Ordem"], errors="coerce").fillna(0).astype(int)
            # Reordena as colunas para Ordem aparecer logo após Opcao na tabela
            cols = ["id", "Tabela", "Opcao", "Ordem", "Ativo", "Excluir"]
            df_ed = df_ed.reindex(columns=[c for c in cols if c in df_ed.columns or c == "Excluir"], fill_value=0)
            df_ed["Excluir"] = df_ed["Excluir"].fillna(False).astype(bool)

        # Configuração de colunas: Ordem só aparece (obrigatório) em Gravidade
        col_config_ed = {
            "id":      None,
            "Tabela":  None,
            "Opcao":   st.column_config.TextColumn("Opção", required=True),
            "Ativo":   st.column_config.CheckboxColumn("Ativo?"),
            "Excluir": st.column_config.CheckboxColumn("✖ Excluir"),
            "Ordem":   None,  # oculto para outros menus
        }
        if tab_sel == "Gravidade":
            col_config_ed["Ordem"] = st.column_config.NumberColumn(
                "Ordem",
                help="Posição na escala (1 = menos grave). Digite o número e clique em Salvar.",
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
#   - Listar usuários cadastrados com perfil de permissão e status
#   - Cadastrar/editar usuário em um único formulário com matriz de permissões
#     Tela × Ação (Ver/Inserir/Alterar/Excluir/Salvar), com perfis predefinidos
#     ou combinação livre ("Personalizado")
#   - Ativar/desativar conta (sem exclusão definitiva)
#   - Redefinir senha integrado ao formulário de edição
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "👥 Usuários":
    st.title("👥 Gerenciamento de Usuários")

    st.markdown('<div class="secao-titulo">Usuários Cadastrados</div>', unsafe_allow_html=True)
    col_ut1, col_ut2 = st.columns([5, 2])
    with col_ut2:
        if st.button("➕ Cadastrar novo usuário", use_container_width=True, key="btn_novo_usuario"):
            st.session_state["modo_novo_usuario"] = True
            st.session_state["usr_editando"] = None
            st.session_state["nome_novo_usuario"] = ""
            st.session_state["perm_perfil"] = PERM_LABELS[0]
            st.session_state["sel_perfil_permissao"] = PERM_LABELS[0]
            seed_checkbox_matriz(PRESET_PERMISSIONS[PERM_LABELS[0]])
            st.rerun()

    hu1, hu2, hu3, hu4 = st.columns([2, 2, 1, 1.6])
    hu1.markdown("**Usuário**")
    hu2.markdown("**Permissão**")
    hu3.markdown("**Ativo**")
    hu4.markdown("**Ações**")
    st.markdown('<hr style="margin:2px 0 10px;border-color:#e8edf5;">', unsafe_allow_html=True)

    for _, u in df_usuarios.iterrows():
        ru1, ru2, ru3, ru4 = st.columns([2, 2, 1, 1.6])
        ru1.write(u["Usuario"])
        ru2.write(rotulo_permissao(u["Permissao"]))
        ativo_u = bool(u["Ativo"])
        ru3.write("Sim" if ativo_u else "Não")
        with ru4:
            cbtn1, cbtn2 = st.columns(2)
            with cbtn1:
                if st.button("Editar", key=f"editar_usr_{u['Usuario']}", use_container_width=True):
                    st.session_state["usr_editando"] = u["Usuario"]
                    st.session_state["modo_novo_usuario"] = False
                    perfil_atual = rotulo_permissao(u["Permissao"])
                    perfil_atual = perfil_atual if perfil_atual in PRESET_PERMISSIONS else "Personalizado"
                    st.session_state["perm_perfil"] = perfil_atual
                    st.session_state["sel_perfil_permissao"] = perfil_atual
                    seed_checkbox_matriz(parse_permissions(u["Permissao"]))
                    st.rerun()
            with cbtn2:
                if u["Usuario"] != st.session_state["user"] and u["Usuario"] != "admin":
                    rotulo_ativar = "Inativar" if ativo_u else "Reativar"
                    if st.button(rotulo_ativar, key=f"toggle_ativo_{u['Usuario']}", use_container_width=True):
                        try:
                            db.update_user(u["id"], {"Ativo": not ativo_u})
                            st.session_state["_notif_banner"] = {
                                "type": "success",
                                "msg": f"✅ Usuário {u['Usuario']} {'inativado' if ativo_u else 'reativado'}."
                            }
                        except Exception as e:
                            st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro: {e}"}
                        st.rerun()

    # ── Formulário de cadastro/edição ───────────────────────────────────────
    if st.session_state.get("usr_editando") or st.session_state.get("modo_novo_usuario"):
        st.markdown("---")
        modo_novo = st.session_state.get("modo_novo_usuario", False)
        titulo_form = "Cadastrar novo usuário" if modo_novo else f"Editar usuário — {st.session_state.get('usr_editando')}"
        st.markdown(f'<div class="secao-titulo">{titulo_form}</div>', unsafe_allow_html=True)

        # Garante que toda a grade tenha estado inicializado (evita KeyError na
        # primeira renderização). Widgets com key fixo (selectbox/checkbox) não
        # podem ter seu st.session_state reescrito depois de já instanciados
        # NESTA MESMA execução — por isso qualquer troca de perfil decidida
        # depois desse ponto (grade manual, "Desmarcar tudo") é apenas
        # agendada em "_perfil_pendente" e só é aplicada aqui, no topo da
        # PRÓXIMA execução, antes dos widgets existirem.
        _pendente = st.session_state.pop("_perfil_pendente", None)
        if _pendente:
            if _pendente["tokens"] is not None:
                seed_checkbox_matriz(_pendente["tokens"])
            st.session_state["perm_perfil"] = _pendente["label"]
            st.session_state["sel_perfil_permissao"] = _pendente["label"]

        for _tok in _tokens_aplicaveis_todos():
            st.session_state.setdefault(f"chk_{_tok}", False)
        st.session_state.setdefault("perm_perfil", PERM_LABELS[0])
        st.session_state.setdefault("sel_perfil_permissao", st.session_state["perm_perfil"])

        cf_a, cf_b, cf_c = st.columns(3)
        nome_novo = None
        with cf_a:
            if modo_novo:
                nome_novo = st.text_input(
                    "Usuário", value=st.session_state.get("nome_novo_usuario", ""),
                    key="input_nome_novo_usuario", placeholder="ex. a.souza"
                )
        with cf_b:
            _perfil_atual = st.session_state["perm_perfil"]
            _perfil_opcoes = PERM_LABELS + (["Personalizado"] if _perfil_atual == "Personalizado" else [])
            perfil_sel = st.selectbox("Perfil de acesso", _perfil_opcoes, key="sel_perfil_permissao")
            if perfil_sel != _perfil_atual:
                st.session_state["perm_perfil"] = perfil_sel
                if perfil_sel != "Personalizado":
                    seed_checkbox_matriz(PRESET_PERMISSIONS[perfil_sel])
                st.rerun()
        with cf_c:
            rotulo_senha = "Senha provisória" if modo_novo else "Redefinir senha"
            placeholder_senha = "Mínimo 8 caracteres" if modo_novo else "Deixe vazio para manter"
            senha_form = st.text_input(rotulo_senha, type="password", key="input_senha_usuario", placeholder=placeholder_senha)

        st.markdown("---")
        col_pm1, col_pm2 = st.columns([5, 2])
        with col_pm1:
            st.markdown("**Permissões por tela e funcionalidade**")
            st.caption("O perfil preenche a grade automaticamente. Qualquer ajuste manual muda o perfil para Personalizado.")
        with col_pm2:
            if st.button("Desmarcar tudo", key="btn_desmarcar_permissoes", use_container_width=True):
                st.session_state["_perfil_pendente"] = {"label": "Personalizado", "tokens": set()}
                st.rerun()

        _grid_perm = [2.4] + [1] * len(ACOES_PERM)
        _hh = st.columns(_grid_perm)
        _hh[0].markdown("**Tela**")
        for _i, _acao in enumerate(ACOES_PERM):
            _hh[_i + 1].markdown(f"<div style='text-align:center;font-size:0.76rem;font-weight:700'>{_acao}</div>", unsafe_allow_html=True)

        for tela in TELAS_PERM:
            _rr = st.columns(_grid_perm)
            _rr[0].markdown(f"<div style='padding-top:6px;font-size:0.85rem'>{tela}</div>", unsafe_allow_html=True)
            for _i, acao in enumerate(ACOES_PERM):
                token = f"{tela}::{acao}"
                with _rr[_i + 1]:
                    if acao in APLICAVEL_PERM.get(tela, []):
                        st.checkbox(token, key=f"chk_{token}", label_visibility="collapsed")
                    else:
                        st.markdown("<div style='text-align:center;color:#c2ccd7'>—</div>", unsafe_allow_html=True)

        # Se o ajuste manual na grade fez a seleção deixar de bater com o
        # perfil mostrado no dropdown, recalcula e força a atualização do
        # rótulo (inclui trocar para "Personalizado" quando aplicável).
        _tokens_atuais = matriz_atual_selecionada()
        _perfil_real = "Personalizado"
        for _nome, _preset_tokens in PRESET_PERMISSIONS.items():
            if _tokens_atuais == set(_preset_tokens):
                _perfil_real = _nome
                break
        if _perfil_real != st.session_state["perm_perfil"]:
            st.session_state["_perfil_pendente"] = {"label": _perfil_real, "tokens": None}
            st.rerun()

        st.markdown("---")
        cbtn_save, cbtn_cancel = st.columns(2)
        with cbtn_save:
            _rotulo_salvar = "💾 Cadastrar usuário" if modo_novo else "💾 Salvar alterações"
            if st.button(_rotulo_salvar, type="primary", use_container_width=True, key="btn_salvar_usuario"):
                tokens_sel = list(matriz_atual_selecionada())
                if modo_novo:
                    nome_final = (nome_novo or "").strip()
                    if not nome_final:
                        st.warning("Informe o nome do usuário.")
                    elif " " in nome_final:
                        st.warning("Login não pode conter espaços.")
                    elif (df_usuarios["Usuario"].str.lower() == nome_final.lower()).any():
                        st.warning("Este login já está em uso.")
                    elif not senha_form or len(senha_form) < 6:
                        st.warning("Defina uma senha com ao menos 6 caracteres.")
                    elif not tokens_sel:
                        st.warning("Selecione ao menos uma permissão.")
                    else:
                        novo_usr = {
                            "Usuario":      nome_final,
                            "Senha_Hash":   hash_senha(senha_form),
                            "Permissao":    permissions_to_string(tokens_sel),
                            "Ativo":        True,
                            "Data_Criacao": date.today().strftime("%Y-%m-%d"),
                        }
                        try:
                            db.save_user(novo_usr)
                            st.session_state["_notif_banner"] = {"type": "success", "msg": f"✅ Usuário '{nome_final}' cadastrado."}
                        except Exception as e:
                            st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao cadastrar: {e}"}
                        st.session_state["modo_novo_usuario"] = False
                        st.session_state["usr_editando"] = None
                        st.rerun()
                else:
                    if not tokens_sel:
                        st.warning("Selecione ao menos uma permissão.")
                    else:
                        row_u = df_usuarios[df_usuarios["Usuario"] == st.session_state["usr_editando"]].iloc[0]
                        campos = {"Permissao": permissions_to_string(tokens_sel)}
                        _senha_valida = True
                        if senha_form.strip():
                            if len(senha_form.strip()) < 6:
                                st.warning("A nova senha deve ter ao menos 6 caracteres.")
                                _senha_valida = False
                            else:
                                campos["Senha_Hash"] = hash_senha(senha_form.strip())
                        if _senha_valida:
                            try:
                                db.update_user(row_u["id"], campos)
                                st.session_state["_notif_banner"] = {"type": "success", "msg": f"✅ Usuário {row_u['Usuario']} atualizado."}
                            except Exception as e:
                                st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ Erro ao salvar: {e}"}
                            st.session_state["usr_editando"] = None
                            st.rerun()
        with cbtn_cancel:
            if st.button("Cancelar", use_container_width=True, key="btn_cancelar_usuario"):
                st.session_state["usr_editando"] = None
                st.session_state["modo_novo_usuario"] = False
                st.rerun()

    st.markdown("---")
    st.markdown("**🔑 Login Mestre do Sistema**")
    st.info("O usuário `admin_master` tem acesso irrestrito e não aparece na lista de usuários. Use-o apenas para configuração inicial.")
