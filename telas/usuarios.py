"""
telas/usuarios.py — Aba Usuários do Painel de Gestão.

Gerenciamento completo de usuários do painel de gestão:
  - Listar usuários cadastrados com perfil de permissão e status
  - Cadastrar/editar usuário em um único formulário com matriz de permissões
    Tela × Ação (Ver/Inserir/Alterar/Excluir/Salvar), com perfis predefinidos
    ou combinação livre ("Personalizado")
  - Ativar/desativar conta (sem exclusão definitiva)
  - Redefinir senha integrado ao formulário de edição
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from rotinas.permissoes import (
    ACOES_PERM, APLICAVEL_PERM, TELAS_PERM, PRESET_PERMISSIONS, PERM_LABELS,
    parse_permissions, permissions_to_string, rotulo_permissao,
    tokens_aplicaveis_todos, seed_checkbox_matriz, matriz_atual_selecionada,
)


def render(df_usuarios: pd.DataFrame) -> None:
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

        for _tok in tokens_aplicaveis_todos():
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
            st.markdown("""
            <style>
            .st-key-btn-desmarcar-permissoes div[data-testid="stButton"] { text-align:right; }
            .st-key-btn-desmarcar-permissoes button {
                background: none !important;
                border: none !important;
                box-shadow: none !important;
                color: #0d47a1 !important;
                font-size: 0.8rem !important;
                padding: 0 !important;
            }
            .st-key-btn-desmarcar-permissoes button:hover { text-decoration: underline !important; }
            </style>
            """, unsafe_allow_html=True)
            with st.container(key="btn-desmarcar-permissoes"):
                if st.button("Desmarcar tudo", key="btn_desmarcar_permissoes"):
                    st.session_state["_perfil_pendente"] = {"label": "Personalizado", "tokens": set()}
                    st.rerun()

        st.markdown("""
        <style>
        .st-key-perm-matrix {
            border: 1px solid #e7edf5;
            border-radius: 8px;
            overflow: hidden;
            margin-top: 4px;
        }
        .st-key-perm-matrix-header {
            background: #f4f8fd;
            padding: 8px 0;
        }
        .st-key-perm-matrix-header [data-testid="stMarkdownContainer"] p {
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            color: #0d47a1 !important;
            margin: 0 !important;
        }
        .st-key-perm-matrix [class*="st-key-perm-row-"] {
            border-top: 1px solid #e7edf5;
            padding: 6px 0;
        }
        .st-key-perm-matrix [class*="st-key-perm-row-"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.85rem !important;
            margin: 0 !important;
        }
        .st-key-perm-matrix div[data-testid="stCheckbox"] { display:flex; justify-content:center; }
        /* O preenchimento marcado é pintado via background-color numa classe
           atômica gerada pelo Streamlit (não uma CSS var nem accent-color),
           então mira-se o estado real via aria-checked, estável entre versões. */
        .st-key-perm-matrix label:has(input[aria-checked="true"]) > span {
            background-color: #0d47a1 !important;
            border-color: #0d47a1 !important;
        }
        .st-key-perm-matrix label:has(input[aria-checked="false"]) > span {
            border-color: #cfd8e3 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container(key="perm-matrix"):
            _grid_perm = [2.4] + [1] * len(ACOES_PERM)
            with st.container(key="perm-matrix-header"):
                _hh = st.columns(_grid_perm)
                _hh[0].markdown("Tela")
                for _i, _acao in enumerate(ACOES_PERM):
                    _hh[_i + 1].markdown(f"<div style='text-align:center'>{_acao}</div>", unsafe_allow_html=True)

            for _row_i, tela in enumerate(TELAS_PERM):
                with st.container(key=f"perm-row-{_row_i}"):
                    _rr = st.columns(_grid_perm)
                    _rr[0].markdown(f"<div style='padding-top:6px'>{tela}</div>", unsafe_allow_html=True)
                    for _i, acao in enumerate(ACOES_PERM):
                        token = f"{tela}::{acao}"
                        with _rr[_i + 1]:
                            if acao in APLICAVEL_PERM.get(tela, []):
                                st.checkbox(token, key=f"chk_{token}", label_visibility="collapsed")
                            else:
                                st.markdown("<div style='text-align:center;color:#c2ccd7;padding-top:6px'>—</div>", unsafe_allow_html=True)

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
                            "Senha_Hash":   db.hash_senha(senha_form),
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
                                campos["Senha_Hash"] = db.hash_senha(senha_form.strip())
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
