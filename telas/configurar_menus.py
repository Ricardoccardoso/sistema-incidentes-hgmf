"""
telas/configurar_menus.py — Aba Configurar Menus do Painel de Gestão.

Duas funcionalidades nesta aba:
  1. Editar opções dos selectboxes do formulário (turnos, setores,
     categorias, etc.) — tabela editável com opção de ativar/desativar/
     excluir itens e adicionar novos
  2. Campos Obrigatórios — marcar quais campos do formulário exibem * e
     são validados
"""

import pandas as pd
import streamlit as st

import db
from rotinas.constantes import CAMPO_LABELS


def render(df_config: pd.DataFrame) -> None:
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
