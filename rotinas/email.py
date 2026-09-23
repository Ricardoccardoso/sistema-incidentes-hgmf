"""
rotinas/email.py — Encaminhamento de notificação por e-mail via API da SendGrid.

Usa um remetente único verificado (Single Sender Verification — não exige
domínio próprio). Configurar em Secrets do Streamlit:
  [sendgrid]
  api_key = "SG.xxxxx"
  from_email = "notificacoes@seudominio.com"   # remetente verificado na SendGrid
"""

import html as html_mod
import json as _json_mod
import os
import re
import urllib.error
import urllib.request
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    SENDGRID_API_KEY = st.secrets["sendgrid"]["api_key"]
except (KeyError, FileNotFoundError, AttributeError):
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
try:
    SENDGRID_FROM_EMAIL = st.secrets["sendgrid"]["from_email"]
except (KeyError, FileNotFoundError, AttributeError):
    SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "")
SENDGRID_CONFIGURADO = bool(SENDGRID_API_KEY and SENDGRID_FROM_EMAIL)


def emails_validos(texto: str) -> list[str]:
    """
    Extrai endereços de e-mail separados por vírgula de um campo de texto,
    descartando entradas com formato inválido.
    """
    if not texto:
        return []
    candidatos = [e.strip() for e in texto.split(",") if e.strip()]
    padrao = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    return [e for e in candidatos if padrao.match(e)]


def gerar_html_email_notificacao(row: dict, numero: int, df_registros: pd.DataFrame | None,
                                  mensagem: str, usuario_atual: str) -> tuple[str, str]:
    """
    Monta o assunto e o corpo HTML (modelo de e-mail) do encaminhamento de uma
    notificação — inclui todos os dados do incidente, descrição, ações
    imediatas e o histórico completo de registros da equipe de segurança do
    paciente. Usado tanto na pré-visualização em tela quanto no envio real.

    Retorna (assunto, html_corpo).
    """
    def esc(v):
        return html_mod.escape(str(v or "—"))

    assunto = (
        f"[HGMF · NSP] Notificação #{numero} — "
        f"{row.get('Categoria_Incidente','—')} · {row.get('Gravidade','—')} · {row.get('Setor','—')}"
    )

    bloco_msg = ""
    if mensagem and mensagem.strip():
        bloco_msg = (
            '<div style="background:#f4f8fd;border:1px solid #dbe7f6;border-radius:8px;'
            'padding:13px 15px;margin:0 0 16px;font-size:13.5px;line-height:1.6;color:#2b3a4d">'
            f'{esc(mensagem.strip())}</div>'
        )

    if df_registros is not None and not df_registros.empty:
        linhas_reg = ""
        for _, reg in df_registros.iterrows():
            data_hora = str(reg.get("Data_Registro", ""))[:16]
            linhas_reg += f"""
            <tr>
              <td style="padding:6px 8px;border:1px solid #dde;white-space:nowrap">{esc(data_hora)}</td>
              <td style="padding:6px 8px;border:1px solid #dde;white-space:nowrap">{esc(reg.get("Usuario"))}</td>
              <td style="padding:6px 8px;border:1px solid #dde">{esc(reg.get("Descricao"))}</td>
            </tr>"""
        bloco_registros = f"""
        <div style="margin:18px 0 6px">
          <div style="font-size:10.5px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#0d47a1;margin-bottom:6px">
            Registros da equipe de segurança do paciente
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:#e8f0fe;color:#0d47a1">
                <th style="padding:6px 8px;border:1px solid #c8d8f0;text-align:left;font-size:10px;text-transform:uppercase">Data / Hora</th>
                <th style="padding:6px 8px;border:1px solid #c8d8f0;text-align:left;font-size:10px;text-transform:uppercase">Usuário</th>
                <th style="padding:6px 8px;border:1px solid #c8d8f0;text-align:left;font-size:10px;text-transform:uppercase">Descrição da ação</th>
              </tr>
            </thead>
            <tbody>{linhas_reg}</tbody>
          </table>
        </div>"""
    else:
        bloco_registros = (
            '<div style="margin:18px 0 6px;font-size:12.5px;color:#5f7086">'
            'Nenhum registro de ação até o momento.</div>'
        )

    acoes = str(row.get("Acoes_Imediatas", "") or "").strip()
    bloco_acoes = ""
    if acoes and acoes.lower() != "nan":
        bloco_acoes = f"""
        <div style="margin:14px 0">
          <div style="font-size:10.5px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#0d47a1;margin-bottom:5px">Ações imediatas realizadas</div>
          <div style="font-size:13.5px;line-height:1.6;color:#2b3a4d">{esc(acoes)}</div>
        </div>"""

    def _campo(rotulo, valor):
        return f"""
        <div>
          <div style="font-size:10px;font-weight:700;letter-spacing:0.6px;text-transform:uppercase;color:#5f7086">{rotulo}</div>
          <div style="font-size:13px;color:#16202e;margin-top:2px">{valor}</div>
        </div>"""

    categoria_html = esc(row.get("Categoria_Incidente"))
    if row.get("Subcategoria"):
        categoria_html += f" — {esc(row.get('Subcategoria'))}"

    campos_html = "".join([
        _campo("Data do incidente", esc(str(row.get("Data_Incidente", ""))[:10])),
        _campo("Hora / turno", esc(row.get("Turno"))),
        _campo("Setor / leito", f"{esc(row.get('Setor'))} · {esc(row.get('Leito'))}"),
        _campo("Tipo geral", esc(row.get("Tipo_Geral"))),
        _campo("Categoria", categoria_html),
        _campo("Gravidade", esc(row.get("Gravidade"))),
        _campo("Paciente", esc(row.get("Nome_Paciente")) if row.get("Nome_Paciente") else "Não informado"),
        _campo("Nascimento", esc(str(row.get("Data_Nascimento", ""))[:10])),
        _campo("Fatores causadores", esc(row.get("Fatores_Causadores"))),
        _campo("Relator / função", f"{esc(row.get('Relator')) if row.get('Relator') else 'Anônimo'} — {esc(row.get('Funcao_Relator'))}"),
    ])

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    html_corpo = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:680px;margin:0 auto;color:#16202e">
      <div style="background:linear-gradient(135deg,#082f66 0%,#0d47a1 60%,#1565c0 100%);color:#fff;border-radius:10px 10px 0 0;padding:16px 20px">
        <div style="font-size:11px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;opacity:0.85">
          Hospital Geral Menandro de Faria — Núcleo de Segurança do Paciente
        </div>
        <div style="font-size:17px;font-weight:700;margin-top:4px">Notificação de incidente #{numero}</div>
      </div>
      <div style="border:1px solid #e7edf5;border-top:none;border-radius:0 0 10px 10px;padding:18px 20px">
        {bloco_msg}
        <div style="font-size:10.5px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#0d47a1;margin-bottom:8px">Dados da notificação</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px 16px">
          {campos_html}
        </div>
        <div style="margin:16px 0">
          <div style="font-size:10.5px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#0d47a1;margin-bottom:5px">Descrição do incidente</div>
          <div style="font-size:13.5px;line-height:1.6;color:#2b3a4d">{esc(row.get("Descricao"))}</div>
        </div>
        {bloco_acoes}
        {bloco_registros}
        <div style="font-size:11px;color:#8a97a8;margin-top:18px;padding-top:12px;border-top:1px solid #e7edf5;line-height:1.6">
          Documento sigiloso. O conteúdo desta notificação é de uso restrito do Núcleo de Segurança do Paciente
          e das áreas envolvidas na apuração. Encaminhado por {esc(usuario_atual)} em {agora}.
        </div>
      </div>
    </div>
    """
    # Remove a indentação de cada linha: st.markdown (usado na pré-visualização)
    # trata blocos indentados com 4+ espaços como código Markdown, o que faria
    # o HTML aparecer como texto cru em vez de ser renderizado.
    html_corpo = "\n".join(linha.strip() for linha in html_corpo.strip().splitlines())
    return assunto, html_corpo


def enviar_email_sendgrid(destinatarios: list[str], cc: list[str], assunto: str, html_corpo: str) -> tuple[bool, str]:
    """
    Envia o e-mail de encaminhamento via API da SendGrid (https://sendgrid.com),
    usando um remetente único verificado (Single Sender Verification — não
    exige domínio próprio). Requer SENDGRID_API_KEY e SENDGRID_FROM_EMAIL
    configurados nos Secrets do Streamlit (seção [sendgrid]).
    Retorna (sucesso, mensagem).
    """
    if not SENDGRID_CONFIGURADO:
        return False, (
            "Envio de e-mail não configurado. Peça ao administrador do sistema para "
            "configurar sendgrid.api_key e sendgrid.from_email nos Secrets do Streamlit."
        )
    personalizacao = {"to": [{"email": d} for d in destinatarios]}
    if cc:
        personalizacao["cc"] = [{"email": c} for c in cc]
    payload = {
        "personalizations": [personalizacao],
        "from": {"email": SENDGRID_FROM_EMAIL, "name": "Painel de Gestão HGMF"},
        "subject": assunto,
        "content": [{"type": "text/html", "value": html_corpo}],
    }
    try:
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=_json_mod.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
                # Sem um User-Agent "normal", APIs atrás de Cloudflare/WAF podem
                # bloquear a requisição por reconhecer a assinatura padrão do
                # urllib como tráfego automatizado.
                "User-Agent": "PainelGestaoHGMF/1.0 (+https://streamlit.io)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if 200 <= resp.status < 300:
                return True, "E-mail enviado com sucesso."
            return False, f"Falha ao enviar e-mail (HTTP {resp.status})."
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="ignore")
        return False, f"Falha ao enviar e-mail (HTTP {e.code}): {detalhe[:300]}"
    except Exception as e:
        return False, f"Falha ao enviar e-mail: {e}"
