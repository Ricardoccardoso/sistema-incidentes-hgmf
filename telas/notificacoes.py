"""
telas/notificacoes.py — Aba Notificações do Painel de Gestão.

Lista todas as notificações com filtros por status, categoria, setor e
gravidade. Cada notificação exibe um card resumido e um expander com:
  - Dados completos do evento e paciente
  - Botão de impressão individual (gera HTML/PDF para download)
  - Formulário de edição (se CAP_EDITAR)
  - Registros de ação da equipe de segurança (se CAP_INSERIR_REGISTRO)
  - Alteração de status e encaminhamento por e-mail (se CAP_SALVAR_STATUS)

Consome (e limpa) st.session_state["_nav_filtro"] / ["_force_open_id"],
gravados por telas/dashboard.py, para pré-selecionar os filtros e abrir
automaticamente o card da notificação de origem.
"""

import html as html_mod
import json as _json_mod
from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import db
from rotinas.constantes import STATUS_OPTS, cor_gravidade
from rotinas.permissoes import CAP_EDITAR, CAP_INSERIR_REGISTRO, CAP_SALVAR_STATUS, has_perm
from rotinas.impressao import gerar_html_impressao
from rotinas.email import emails_validos, gerar_html_email_notificacao, enviar_email_sendgrid


def render(df_dados: pd.DataFrame, df_config: pd.DataFrame, perm: str) -> None:
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
        cor = cor_gravidade(str(row.get("Gravidade", "")))
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
                        ops = db.get_opcoes(df_config, 'Turno')
                        cur_turno = row.get('Turno','')
                        try:
                            idx_turno = ops.index(cur_turno) if cur_turno in ops else 0
                        except Exception:
                            idx_turno = 0
                        new_turno = st.selectbox('Hora/Turno do Incidente', ops, index=idx_turno)
                        new_setor = st.selectbox('Setor', db.get_opcoes(df_config, 'Setor'), index=0)
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

            # Encaminhamento da notificação por e-mail (dados completos + registros)
            if has_perm(perm, CAP_SALVAR_STATUS):
                st.markdown("---")
                _enc_aberto = st.session_state.get(f"encaminhar_{idx}", False)
                if st.button(
                    "Fechar encaminhamento" if _enc_aberto else "📧 Encaminhar notificação",
                    key=f"btn_toggle_encaminhar_{idx}"
                ):
                    st.session_state[f"encaminhar_{idx}"] = not _enc_aberto
                    st.rerun()

                if st.session_state.get(f"encaminhar_{idx}", False):
                    st.markdown("**Encaminhar notificação por e-mail**")
                    st.caption(
                        "O e-mail sai com todos os dados da notificação e o histórico completo "
                        "de registros da equipe de segurança do paciente."
                    )
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        email_para = st.text_input(
                            "Enviar para", placeholder="setor@hgmf.com.br",
                            key=f"email_para_{idx}"
                        )
                    with col_e2:
                        email_cc = st.text_input(
                            "Com cópia (opcional)", placeholder="separar por vírgula",
                            key=f"email_cc_{idx}"
                        )
                    email_msg = st.text_area(
                        "Mensagem do encaminhamento (opcional)", key=f"email_msg_{idx}", height=90
                    )

                    _df_reg_email = db.load_registros_acao(row.get("id"))
                    _assunto, _corpo_email = gerar_html_email_notificacao(
                        row.to_dict(), idx + 1,
                        _df_reg_email if not _df_reg_email.empty else None,
                        email_msg, st.session_state.get("user", "")
                    )
                    _dest_validos = emails_validos(email_para)
                    _cc_validos = emails_validos(email_cc)

                    st.markdown("**Modelo que será enviado**")
                    st.markdown(
                        f"**Para:** {html_mod.escape(email_para) or '—'}  \n"
                        f"**Cc:** {html_mod.escape(email_cc) or '—'}  \n"
                        f"**Assunto:** {html_mod.escape(_assunto)}"
                    )
                    st.markdown(
                        f'<div style="border:1px solid #e7edf5;border-radius:10px;padding:16px;background:#fff">{_corpo_email}</div>',
                        unsafe_allow_html=True
                    )

                    col_e3, col_e4 = st.columns(2)
                    with col_e3:
                        if st.button("📨 Enviar e-mail", key=f"btn_enviar_email_{idx}", type="primary", use_container_width=True):
                            if not email_para.strip():
                                st.warning("Informe ao menos um destinatário.")
                            elif not _dest_validos:
                                st.warning("O campo 'Enviar para' não contém um e-mail válido.")
                            else:
                                _ok, _msg = enviar_email_sendgrid(_dest_validos, _cc_validos, _assunto, _corpo_email)
                                if _ok:
                                    st.session_state["_notif_banner"] = {"type": "success", "msg": f"✅ {_msg}"}
                                    st.session_state[f"encaminhar_{idx}"] = False
                                else:
                                    st.session_state["_notif_banner"] = {"type": "error", "msg": f"❌ {_msg}"}
                                st.rerun()
                    with col_e4:
                        if st.button("Cancelar", key=f"btn_cancelar_email_{idx}", use_container_width=True):
                            st.session_state[f"encaminhar_{idx}"] = False
                            st.rerun()

        st.markdown(
            '<div style="border-top:3px solid #dbe4f0;margin:20px 0 8px 0;border-radius:2px;"></div>',
            unsafe_allow_html=True
        )
