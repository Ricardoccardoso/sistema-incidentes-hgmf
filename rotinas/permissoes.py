"""
rotinas/permissoes.py — Matriz de permissões Tela × Ação do Painel de Gestão.

Cada permissão de usuário é um conjunto de tokens "Tela::Ação" (ex:
"Notificações::Alterar"). Existem três perfis predefinidos (Acesso Total,
Apenas Relatórios, Apenas Configurar Tabelas) ou uma combinação livre
("Personalizado"). O conjunto de tokens é serializado como string no campo
Permissao do usuário — o nome do perfil quando coincide exatamente com um
preset, ou os tokens juntados com ";" caso contrário.

Permissões salvas no formato antigo (nomes de menu soltos + capacidades
cap_editar_notificacoes/cap_registros_equipe) são migradas automaticamente
na leitura, sem exigir alteração manual dos usuários já cadastrados.
"""

import streamlit as st

from rotinas.constantes import MENU_LABELS

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


def tokens_aplicaveis_todos():
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
    for tok in tokens_aplicaveis_todos():
        st.session_state[f"chk_{tok}"] = tok in ativos


def matriz_atual_selecionada():
    """Lê o estado atual da grade de permissões diretamente de st.session_state."""
    return {tok for tok in tokens_aplicaveis_todos() if st.session_state.get(f"chk_{tok}", False)}
