"""
db.py — Camada de acesso ao Supabase para o sistema HGMF
Substitui os arquivos CSV por tabelas PostgreSQL gerenciadas pelo Supabase.

Configuração necessária (uma única vez):
  1. Crie uma conta gratuita em https://supabase.com
  2. Crie um projeto
  3. Execute o SQL de setup em supabase_setup.sql no SQL Editor do painel
  4. Copie a URL e a chave anon do projeto em Configurações → API
  5. Defina as variáveis de ambiente (ou use o arquivo .env):
       SUPABASE_URL=https://xxxx.supabase.co
       SUPABASE_KEY=eyJ...
     No Streamlit Cloud, coloque-as em Settings → Secrets:
       [supabase]
       url = "https://xxxx.supabase.co"
       key = "eyJ..."
"""

from __future__ import annotations

import os
import hashlib
import pandas as pd
import streamlit as st
from datetime import datetime, date
from supabase import create_client, Client


# ─── Conexão ─────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    """Retorna o cliente Supabase, lendo credenciais dos Secrets do Streamlit
    ou das variáveis de ambiente."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except (KeyError, FileNotFoundError):
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        st.error(
            "⚠️ Credenciais do Supabase não encontradas. "
            "Configure SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit "
            "ou como variáveis de ambiente."
        )
        st.stop()

    return create_client(url, key)


# ─── Utilitários ─────────────────────────────────────────────────────────────

def hash_senha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _rows_to_df(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    """Converte lista de dicts (resposta Supabase) em DataFrame com colunas garantidas."""
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


# ─── Colunas esperadas ────────────────────────────────────────────────────────

COLUNAS_INCIDENTES = [
    "id", "Data_Registro", "Data_Incidente", "Turno", "Setor",
    "Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade",
    "Fatores_Causadores", "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Data_Relato", "Hora_Relato", "Nome_Paciente", "Data_Nascimento",
    "Relator", "Funcao_Relator", "Status",
]

COLUNAS_CONFIG = ["id", "Tabela", "Opcao", "Ativo"]

COLUNAS_USUARIOS = ["id", "Usuario", "Senha_Hash", "Permissao", "Ativo", "Data_Criacao"]


# ══════════════════════════════════════════════════════════════════════════════
# INCIDENTES
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> pd.DataFrame:
    sb = get_client()
    res = sb.table("incidentes").select("*").order("Data_Registro", desc=True).execute()
    return _rows_to_df(res.data or [], COLUNAS_INCIDENTES)


def save_incidente(novo: dict) -> None:
    """Insere um novo registro de incidente."""
    sb = get_client()
    # Remove 'id' caso esteja presente (auto-gerado pelo banco)
    novo.pop("id", None)
    sb.table("incidentes").insert(novo).execute()


def update_incidente(row_id: int | str, campos: dict) -> None:
    """Atualiza campos de um incidente existente pelo id."""
    sb = get_client()
    campos.pop("id", None)
    sb.table("incidentes").update(campos).eq("id", row_id).execute()


def delete_incidente(row_id: int | str) -> None:
    sb = get_client()
    sb.table("incidentes").delete().eq("id", row_id).execute()


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES (menus/opções)
# ══════════════════════════════════════════════════════════════════════════════

_OPCOES_PADRAO = [
    # Turno
    {"Tabela": "Turno", "Opcao": "Manhã (07h–13h)",   "Ativo": True},
    {"Tabela": "Turno", "Opcao": "Tarde (13h–19h)",   "Ativo": True},
    {"Tabela": "Turno", "Opcao": "Noite (19h–07h)",   "Ativo": True},
    # Tipo Geral
    {"Tabela": "Tipo Geral", "Opcao": "Assistencial",   "Ativo": True},
    {"Tabela": "Tipo Geral", "Opcao": "Administrativa", "Ativo": True},
    {"Tabela": "Tipo Geral", "Opcao": "Infraestrutura", "Ativo": True},
    # Setores
    {"Tabela": "Setor", "Opcao": "Emergência (REA)",       "Ativo": True},
    {"Tabela": "Setor", "Opcao": "UTI Adulto",             "Ativo": True},
    {"Tabela": "Setor", "Opcao": "UTI Neonatal",           "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Enfermaria Clínica",     "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Enfermaria Cirúrgica",   "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Centro Cirúrgico",       "Ativo": True},
    {"Tabela": "Setor", "Opcao": "CME",                    "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Farmácia",               "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Laboratório",            "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Radiologia/Imagem",      "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Ambulatório",            "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Recepção/Admissão",      "Ativo": True},
    {"Tabela": "Setor", "Opcao": "Outro",                  "Ativo": True},
    # Categorias
    {"Tabela": "Categoria", "Opcao": "Lesão por Pressão (LPP)",              "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Queda do Paciente",                    "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Falha na Segurança Medicamentosa",     "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Falha de Identificação do Paciente",   "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Infecção Relacionada à Assistência",   "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Falha em Procedimento/Cirurgia",       "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Falha em Equipamento/Dispositivo",     "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Reação Transfusional",                 "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Evento de Comunicação/Informação",     "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Violência / Agressão",                 "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Extubação não Planejada",              "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Saída não Autorizada do Paciente",     "Ativo": True},
    {"Tabela": "Categoria", "Opcao": "Outro Incidente Assistencial",         "Ativo": True},
    # Subcategorias LPP
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio I",          "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio II",         "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio III",        "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio IV",         "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Não Classificável",  "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Tecido Mucoso",      "Ativo": True},
    # Subcategorias Queda
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda da própria altura",     "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda do leito",              "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda durante transferência", "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda no banheiro",           "Ativo": True},
    # Subcategorias Medicamento
    {"Tabela": "Subcategoria_Med", "Opcao": "Dose incorreta",      "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Medicamento errado",  "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Via errada",          "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Horário errado",      "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Omissão de dose",     "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Paciente errado",     "Ativo": True},
    # Gravidade
    {"Tabela": "Gravidade", "Opcao": "Near Miss (Quase Evento - não atingiu o paciente)", "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Sem Dano (atingiu, sem lesão)",                     "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Dano Leve (lesão leve/temporária)",                 "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Dano Moderado (lesão moderada/temporária)",         "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Dano Grave (lesão grave/permanente)",               "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Óbito",                                             "Ativo": True},
    # Fatores Causadores
    {"Tabela": "Fator Causador", "Opcao": "Comunicação inadequada",          "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falha de processo/protocolo",     "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Sobrecarga de trabalho",          "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Equipamento inadequado/ausente",  "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falta de treinamento",            "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Ambiente/infraestrutura",         "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Fator humano/distração",          "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Paciente não colaborativo",       "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Outro",                           "Ativo": True},
]


def load_config() -> pd.DataFrame:
    sb = get_client()
    res = sb.table("config_tabelas").select("*").order("Tabela").execute()
    rows = res.data or []
    if not rows:
        # Primeira execução: semeia opções padrão
        sb.table("config_tabelas").insert(_OPCOES_PADRAO).execute()
        res = sb.table("config_tabelas").select("*").order("Tabela").execute()
        rows = res.data or []
    return _rows_to_df(rows, COLUNAS_CONFIG)


# ══════════════════════════════════════════════════════════════════════════════
# FLAGS DE CAMPOS (obrigatoriedade)
# Tabela esperada: config_campos (Campo TEXT, Obrigatorio BOOLEAN)
# ══════════════════════════════════════════════════════════════════════════════

def load_field_flags() -> pd.DataFrame:
    sb = get_client()
    res = sb.table("config_campos").select("*").order("Campo").execute()
    rows = res.data or []
    if not rows:
        # semeia flags padrão (todos False) — ajuste conforme necessário
        default_campos = [
            {"Campo": c, "Obrigatorio": False} for c in [
                "Data_Registro","Data_Incidente","Turno","Setor","Leito",
                "Tipo_Geral","Categoria_Incidente","Subcategoria","Medicamento_Envolvido",
                "Gravidade","Fatores_Causadores","Descricao","Acoes_Imediatas","Sugestao_Melhoria",
                "Data_Relato","Hora_Relato","Nome_Paciente","Data_Nascimento",
                "Relator","Funcao_Relator","Status"
            ]
        ]
        sb.table("config_campos").insert(default_campos).execute()
        res = sb.table("config_campos").select("*").order("Campo").execute()
        rows = res.data or []
    df = _rows_to_df(rows, ["id", "Campo", "Obrigatorio"])
    if "Obrigatorio" in df.columns:
        df["Obrigatorio"] = df["Obrigatorio"].apply(_to_bool)
    return df


def save_field_flag(row_id: int | str, obrigatorio: bool | str) -> None:
    sb = get_client()
    sb.table("config_campos").update({"Obrigatorio": _to_bool(obrigatorio)}).eq("id", row_id).execute()


def save_config_opcao(row_id: int | str, opcao: str, ativo: bool) -> None:
    """Atualiza o texto e/ou o status de uma opção de configuração."""
    sb = get_client()
    sb.table("config_tabelas").update({"Opcao": opcao, "Ativo": ativo}).eq("id", row_id).execute()


def delete_config_opcao(row_id: int | str) -> None:
    """Remove uma opção de configuração."""
    sb = get_client()
    sb.table("config_tabelas").delete().eq("id", row_id).execute()


def add_config_opcao(tabela: str, opcao: str) -> None:
    sb = get_client()
    sb.table("config_tabelas").insert({"Tabela": tabela, "Opcao": opcao, "Ativo": True}).execute()


def get_opcoes(df_conf: pd.DataFrame, tabela: str) -> list[str]:
    ops = df_conf[(df_conf["Tabela"] == tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return ops if ops else ["Sem opções configuradas"]


# ══════════════════════════════════════════════════════════════════════════════
# USUÁRIOS
# ══════════════════════════════════════════════════════════════════════════════

def load_users() -> pd.DataFrame:
    sb = get_client()
    res = sb.table("usuarios").select("*").execute()
    rows = res.data or []
    if not rows:
        # Cria usuário admin padrão na primeira execução
        admin = {
            "Usuario":      "admin",
            "Senha_Hash":   hash_senha("admin123"),
            "Permissao":    "Acesso Total",
            "Ativo":        True,
            "Data_Criacao": date.today().isoformat(),
        }
        sb.table("usuarios").insert(admin).execute()
        res = sb.table("usuarios").select("*").execute()
        rows = res.data or []
    return _rows_to_df(rows, COLUNAS_USUARIOS)


def save_user(novo: dict) -> None:
    sb = get_client()
    novo.pop("id", None)
    sb.table("usuarios").insert(novo).execute()


def update_user(row_id: int | str, campos: dict) -> None:
    sb = get_client()
    campos.pop("id", None)
    sb.table("usuarios").update(campos).eq("id", row_id).execute()


def delete_user(row_id: int | str) -> None:
    sb = get_client()
    sb.table("usuarios").delete().eq("id", row_id).execute()
