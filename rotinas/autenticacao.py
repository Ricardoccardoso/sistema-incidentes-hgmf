"""
rotinas/autenticacao.py — Tela de login do Painel de Gestão.

Fluxo de autenticação:
  1. Tenta login mestre (admin_master) via hash lido dos Secrets
  2. Tenta login normal consultando a tabela de usuários no Supabase

Inclui também o fluxo de "Esqueceu a senha?" (apenas informativo: registra
a intenção na tela e orienta o usuário a aguardar contato do administrador;
nada é persistido).
"""

import streamlit as st

import db

try:
    SENHA_ADMIN_MESTRE = st.secrets["admin_master"]["hash"]
except (KeyError, FileNotFoundError, AttributeError):
    SENHA_ADMIN_MESTRE = ""  # login mestre desabilitado se não configurado


def tela_login(logo_img_tag: str) -> None:
    """
    Exibe a tela de login (enquanto o usuário não estiver autenticado) e
    encerra a execução do script com st.stop(). Deve ser chamada apenas
    quando st.session_state["logado"] for False.
    """
    _logo_login = logo_img_tag.replace("__H__", "84").replace(
        'style="', 'style="margin:0 auto 12px; '
    ) if logo_img_tag else '<span style="font-size:2.8rem;">🔒</span>'
    st.markdown(f"""
    <div style="max-width:400px; margin:60px auto 0 auto;">
      <div style="text-align:center; margin-bottom:28px;">
        {_logo_login}
        <h2 style="margin:8px 0 4px; color:#0d47a1; font-weight:800; letter-spacing:0.4px;">NOTIFICARE</h2>
        <p style="color:#546e7a; font-size:0.88rem;">Sistema Integrado de Segurança do Paciente<br>Hospital Geral Menandro de Faria</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.form("login_form"):
            login    = st.text_input("👤 Usuário")
            senha    = st.text_input("🔑 Senha", type="password")
            entrar   = st.form_submit_button("Entrar no Sistema", use_container_width=True)

            # LOGIN MESTRE (administrador do sistema)
            if entrar:
                if login.strip() == "admin_master" and db.hash_senha(senha) == SENHA_ADMIN_MESTRE:
                    st.session_state.update({"logado": True, "user": "admin_master",
                                              "permissao": "Acesso Total"})
                    st.rerun()
                else:
                    df_usr = db.load_users()
                    validar = df_usr[
                        (df_usr["Usuario"].str.lower() == login.strip().lower()) &
                        (df_usr["Senha_Hash"] == db.hash_senha(senha)) &
                        (df_usr["Ativo"] == True)
                    ]
                    if not validar.empty:
                        perm = validar.iloc[0]["Permissao"]
                        st.session_state.update({"logado": True, "user": login.strip(),
                                                  "permissao": perm})
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos.")

        # ── Recuperação de senha ──────────────────────────────────────
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
