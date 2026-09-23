"""
telas/relatorios.py — Aba Relatórios do Painel de Gestão.

Relatórios temáticos pré-configurados — o usuário seleciona o tipo e o
sistema filtra e exibe tabelas + gráficos específicos. Tipos disponíveis:
Resumo Mensal, Ranking Setores, Near Miss, Dano Grave, Pendências, LPP,
Quedas, Medicamentos, Sugestões de Melhoria.
"""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st


def exibir_tabela_relatorio(df: pd.DataFrame, colunas: list[str] | None = None,
                             msg_vazio: str = "Nenhum registro para este relatório no período selecionado.") -> None:
    """
    Exibe uma tabela de relatório padronizada: legenda de quantidade de
    linhas e mensagem amigável quando não há registros no período/filtro
    selecionado.
    """
    if df.empty:
        st.info(msg_vazio)
        return
    df_show = df[colunas].copy() if colunas else df.copy()
    st.caption(f"**{len(df_show)}** {'linha' if len(df_show) == 1 else 'linhas'}")
    st.dataframe(df_show, use_container_width=True, hide_index=True)


def render(df_dados: pd.DataFrame) -> None:
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

    # ── Filtro de período e setor — aplicado a todos os relatórios ─────────
    # Widgets com key fixo não podem ter seu session_state reescrito depois de
    # já instanciados NESTA MESMA execução — por isso o botão "Ano corrente
    # até hoje" apenas agenda a troca, aplicada aqui no topo antes dos
    # date_input existirem nesta execução (mesmo padrão usado na matriz de
    # permissões da aba Usuários).
    _rel_periodo_pendente = st.session_state.pop("_rel_periodo_pendente", None)
    if _rel_periodo_pendente:
        st.session_state["rel_de"] = _rel_periodo_pendente["de"]
        st.session_state["rel_ate"] = _rel_periodo_pendente["ate"]

    st.markdown('<div class="secao-titulo">🗓️ Filtro de Período</div>', unsafe_allow_html=True)
    cr1, cr2, cr3 = st.columns([2, 2, 2])
    with cr1:
        rel_de = st.date_input("De", value=date(date.today().year, 1, 1), format="DD/MM/YYYY", key="rel_de")
    with cr2:
        rel_ate = st.date_input("Até", value=date.today(), format="DD/MM/YYYY", key="rel_ate")
    with cr3:
        rel_setor = st.selectbox(
            "Setor", ["Todos"] + sorted(df_dados["Setor"].dropna().unique().tolist()), key="rel_setor"
        )

    _sem_data_rel = df_dados["Data_Incidente"].isna()
    _no_periodo_rel = (
        (df_dados["Data_Incidente"] >= pd.to_datetime(rel_de)) &
        (df_dados["Data_Incidente"] <= pd.to_datetime(rel_ate))
    )
    df_dados = df_dados[_sem_data_rel | _no_periodo_rel].copy()
    if rel_setor != "Todos":
        df_dados = df_dados[df_dados["Setor"] == rel_setor]

    col_per1, col_per2 = st.columns([5, 2])
    with col_per1:
        st.caption(
            f"Período: **{rel_de.strftime('%d/%m/%Y')}** a **{rel_ate.strftime('%d/%m/%Y')}** · "
            f"**{len(df_dados)}** notificações no filtro"
        )
    with col_per2:
        if st.button("Ano corrente até hoje", key="rel_periodo_padrao"):
            st.session_state["_rel_periodo_pendente"] = {
                "de": date(date.today().year, 1, 1), "ate": date.today()
            }
            st.rerun()

    st.markdown("---")

    if tipo_rel == "Resumo Mensal por Categoria":
        df_dados["Mes"] = df_dados["Data_Incidente"].dt.to_period("M").astype(str)
        df_pivot = df_dados.groupby(["Mes", "Categoria_Incidente"]).size().unstack(fill_value=0)
        st.subheader("Notificações por Mês e Categoria")
        if df_pivot.empty:
            st.info("Nenhum registro para este relatório no período selecionado.")
        else:
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
        exibir_tabela_relatorio(df_rank)
        if not df_rank.empty:
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
        exibir_tabela_relatorio(
            df_nm, colunas=["Data_Incidente", "Setor", "Categoria_Incidente", "Fatores_Causadores", "Descricao"]
        )

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
        exibir_tabela_relatorio(df_gr, colunas=[
            "Data_Incidente", "Setor", "Categoria_Incidente", "Gravidade",
            "Nome_Paciente", "Data_Nascimento", "Descricao", "Relator"
        ])

    elif tipo_rel == "Notificações Pendentes de Análise":
        df_pend = df_dados[df_dados["Status"].isin(["Novo", "Investigar", "Pendência", "Em Análise"])].copy()
        st.metric("Pendentes de Análise", len(df_pend))
        exibir_tabela_relatorio(df_pend, colunas=[
            "Data_Registro", "Data_Incidente", "Setor", "Categoria_Incidente", "Gravidade", "Status"
        ])

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
        else:
            st.info("Nenhum registro para este relatório no período selecionado.")

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
        else:
            st.info("Nenhum registro para este relatório no período selecionado.")

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
        exibir_tabela_relatorio(df_med, colunas=[
            "Data_Incidente", "Setor", "Subcategoria", "Medicamento_Envolvido", "Gravidade", "Descricao"
        ])

    elif tipo_rel == "Sugestões de Melhoria Coletadas":
        df_sug = df_dados[df_dados["Sugestao_Melhoria"].notna() &
                          (df_dados["Sugestao_Melhoria"].str.strip() != "")].copy()
        st.metric("Sugestões Recebidas", len(df_sug))
        if df_sug.empty:
            st.info("Nenhum registro para este relatório no período selecionado.")
        for _, r in df_sug.iterrows():
            st.markdown(f"""
            <div style="background:#f3f8ff; border-left:3px solid #1976d2; border-radius:8px;
                        padding:12px 16px; margin-bottom:8px; font-size:0.88rem;">
              <strong>{r.get('Setor','—')}</strong> — {str(r.get('Data_Incidente',''))[:10]}<br>
              {r.get('Sugestao_Melhoria','')}
            </div>
            """, unsafe_allow_html=True)
