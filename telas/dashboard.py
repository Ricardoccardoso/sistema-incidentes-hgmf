"""
telas/dashboard.py — Aba Dashboard do Painel de Gestão.

Exibe indicadores agregados e gráficos para o período selecionado. Permite
filtrar por data e setor, e exibe KPIs + 6 gráficos Altair: Gravidade
(donut), Categoria (barras), Evolução temporal (linha), Setor (barras),
Turno (barras), Fatores causadores (barras).

Clicar num alerta ou numa célula da matriz categoria×gravidade navega para
a aba Notificações já filtrada: grava st.session_state["_ir_para_menu"],
["_nav_filtro"] e (no caso dos alertas) ["_force_open_id"] — consumidos por
pages/Gestao.py e por telas/notificacoes.py, respectivamente.
"""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from rotinas.constantes import STATUS_OPTS, PALETA_CATEGORICA


def render(df_dados: pd.DataFrame) -> None:
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
    # Fica lado a lado com o gráfico de gravidade para aproveitar a largura.
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

    col_matriz, col_donut = st.columns([3, 1.1], gap="medium")

    with col_matriz:
        if _cats_presentes:
            st.markdown("""
            <style>
            .st-key-incid-matrix div[data-testid="stHorizontalBlock"] {
                gap: 0.35rem;
                margin-bottom: -0.9rem;
            }
            .st-key-incid-matrix div[data-testid="stButton"] button {
                min-height: 1.6rem !important;
                padding: 0 4px !important;
                font-size: 0.72rem !important;
                font-family: 'IBM Plex Mono', monospace;
            }
            .st-key-incid-matrix div[data-testid="stMarkdownContainer"] p { margin: 0 !important; }
            </style>
            """, unsafe_allow_html=True)

            with st.container(key="incid-matrix"):
                _grid_ratio = [2.8] + [0.7] * len(_GRAV_BUCKETS) + [0.7]
                _hcols = st.columns(_grid_ratio, gap="small")
                _hcols[0].markdown("**Categoria**")
                for _i, (_nome_curto, _) in enumerate(_GRAV_BUCKETS):
                    _hcols[_i + 1].markdown(
                        f"<div style='text-align:center;font-size:0.66rem;font-weight:700;color:#0d47a1'>{_nome_curto}</div>",
                        unsafe_allow_html=True
                    )
                _hcols[-1].markdown(
                    "<div style='text-align:center;font-size:0.66rem;font-weight:700;color:#0d47a1'>Total</div>",
                    unsafe_allow_html=True
                )

                for _cat in _cats_presentes:
                    _df_cat_row = df_f[df_f["Categoria_Incidente"] == _cat]
                    _rcols = st.columns(_grid_ratio, gap="small")
                    _rcols[0].markdown(f"<div style='font-size:0.78rem;padding-top:5px'>{_cat}</div>", unsafe_allow_html=True)
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
                                st.markdown("<div style='text-align:center;color:#c2ccd7;padding-top:5px'>—</div>", unsafe_allow_html=True)
                    with _rcols[-1]:
                        _total_cat = len(_df_cat_row)
                        if st.button(str(_total_cat), key=f"mtx_total_{_cat}", use_container_width=True):
                            st.session_state["_ir_para_menu"] = "📋 Notificações"
                            st.session_state["_nav_filtro"] = {"categoria": _cat, "gravidade": "Todas", "status": "Todos"}
                            st.rerun()

    with col_donut:
        st.markdown("**Incidentes por Gravidade**")
        df_grav = df_f["Gravidade"].value_counts().reset_index()
        df_grav.columns = ["Gravidade", "Qtd"]
        chart_grav = alt.Chart(df_grav).mark_arc(innerRadius=45, outerRadius=90).encode(
            theta=alt.Theta("Qtd:Q"),
            color=alt.Color("Gravidade:N", scale=alt.Scale(
                domain=["Near Miss (Quase Evento - não atingiu o paciente)",
                        "Sem Dano (atingiu, sem lesão)",
                        "Dano Leve (lesão leve/temporária)",
                        "Dano Moderado (lesão moderada/temporária)",
                        "Dano Grave (lesão grave/permanente)", "Óbito"],
                range=["#7b1fa2", "#43a047", "#fdd835", "#ff8f00", "#e53935", "#b71c1c"]
            ), legend=alt.Legend(title=None, orient="bottom", symbolLimit=0, labelFontSize=9)),
            tooltip=["Gravidade", "Qtd"]
        ).properties(height=260)
        st.altair_chart(chart_grav, use_container_width=True)

    st.markdown("---")

    # ── Gráficos linha 1 ──────────────────────────────────────────────────
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Incidentes por Categoria")
        df_cat = df_f["Categoria_Incidente"].value_counts().reset_index()
        df_cat.columns = ["Categoria", "Qtd"]
        chart_cat = alt.Chart(df_cat).mark_bar(cornerRadiusTopRight=5, cornerRadiusTopLeft=5).encode(
            x=alt.X("Categoria:N", sort="-y", title="", axis=alt.Axis(labelAngle=-35, labelLimit=140)),
            y=alt.Y("Qtd:Q", title="Quantidade"),
            color=alt.Color("Categoria:N", scale=alt.Scale(range=PALETA_CATEGORICA), legend=None),
            tooltip=["Categoria", "Qtd"]
        ).properties(height=320)
        st.altair_chart(chart_cat, use_container_width=True)

    with g2:
        st.subheader("Evolução Temporal (por semana)")
        df_tmp = df_f.copy()
        df_tmp["Semana"] = df_tmp["Data_Incidente"].dt.to_period("W").apply(lambda r: str(r.start_time.date()))
        df_sem = df_tmp.groupby("Semana").size().reset_index(name="Qtd")
        chart_sem = alt.Chart(df_sem).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#1565c0").encode(
            x=alt.X("Semana:O", title="Semana"),
            y=alt.Y("Qtd:Q",   title="Notificações"),
            tooltip=["Semana", "Qtd"]
        ).properties(height=280)
        st.altair_chart(chart_sem, use_container_width=True)

    # ── Gráficos linha 2 ──────────────────────────────────────────────────
    g3, g4 = st.columns(2)

    with g3:
        st.subheader("Incidentes por Setor")
        df_set = df_f["Setor"].value_counts().reset_index()
        df_set.columns = ["Setor", "Qtd"]
        chart_set = alt.Chart(df_set).mark_bar(cornerRadiusTopRight=5, cornerRadiusTopLeft=5).encode(
            x=alt.X("Setor:N", sort="-y", title="", axis=alt.Axis(labelAngle=-35, labelLimit=140)),
            y=alt.Y("Qtd:Q", title="Quantidade"),
            color=alt.Color("Setor:N", scale=alt.Scale(range=PALETA_CATEGORICA), legend=None),
            tooltip=["Setor", "Qtd"]
        ).properties(height=290)
        st.altair_chart(chart_set, use_container_width=True)

    with g4:
        st.subheader("Distribuição por Turno")
        df_turno = df_f["Turno"].value_counts().reset_index()
        df_turno.columns = ["Turno", "Qtd"]
        chart_turno = alt.Chart(df_turno).mark_bar(cornerRadiusTopRight=5, cornerRadiusTopLeft=5).encode(
            x=alt.X("Turno:N", title="", axis=alt.Axis(labelAngle=-35, labelLimit=140)),
            y=alt.Y("Qtd:Q",   title="Qtd"),
            color=alt.Color("Turno:N", scale=alt.Scale(range=PALETA_CATEGORICA), legend=None),
            tooltip=["Turno", "Qtd"]
        ).properties(height=290)
        st.altair_chart(chart_turno, use_container_width=True)

    # ── Gráfico: fatores causadores ─────────────────────────────────────────
    st.subheader("Fatores Causadores Mais Frequentes")
    if df_f["Fatores_Causadores"].notna().any():
        fatores_todos = df_f["Fatores_Causadores"].dropna().str.split(", ").explode()
        df_fat = fatores_todos.value_counts().head(8).reset_index()
        df_fat.columns = ["Fator", "Qtd"]
        chart_fat = alt.Chart(df_fat).mark_bar(cornerRadiusTopRight=4, cornerRadiusTopLeft=4).encode(
            x=alt.X("Fator:N", sort="-y", title="", axis=alt.Axis(labelAngle=-35, labelLimit=140)),
            y=alt.Y("Qtd:Q", title="Quantidade"),
            color=alt.Color("Fator:N", scale=alt.Scale(range=PALETA_CATEGORICA), legend=None),
            tooltip=["Fator", "Qtd"]
        ).properties(height=280)
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
