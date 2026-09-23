"""
telas/exportar.py — Aba Exportar Dados do Painel de Gestão.

Permite baixar a base de incidentes filtrada por período em formato Excel
(.xlsx), via openpyxl/pandas ExcelWriter. Exibe pré-visualização dos
primeiros 50 registros.
"""

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st


def render(df_dados: pd.DataFrame) -> None:
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
