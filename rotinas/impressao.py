"""
rotinas/impressao.py — Geração do documento HTML de impressão de notificações.
"""

import html as html_mod
from datetime import datetime

import pandas as pd


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
