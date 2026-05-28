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
    "Data_Relato", "Hora_Relato", "Nome_Paciente", "Data_Nascimento", "Raca_Cor",
    "Relator", "Funcao_Relator", "Status",
]

COLUNAS_CONFIG = ["id", "Tabela", "Opcao", "Ativo"]

COLUNAS_USUARIOS = ["id", "Usuario", "Senha_Hash", "Permissao", "Ativo", "Data_Criacao"]

CONFIG_TABLES = {
    "Turno":           "config_turno",
    "Tipo Geral":      "config_tipo_geral",
    "Setor":           "config_setor",
    "Categoria":       "config_categoria",
    "Subcategoria_LPP": "config_subcategoria_lpp",
    "Subcategoria_Queda": "config_subcategoria_queda",
    "Subcategoria_Med": "config_subcategoria_med",
    "Gravidade":       "config_gravidade",
    "Fator Causador":  "config_fator_causador",
}

DEFAULT_CONFIG_OPCOES = {
    "Turno": [
        "Manhã (07h–13h)",
        "Tarde (13h–19h)",
        "Noite (19h–07h)",
    ],
    "Tipo Geral": [
        "Assistencial",
        "Administrativa",
        "Infraestrutura",
    ],
    "Setor": [
        "Emergência (REA)",
        "UTI Adulto",
        "UTI Neonatal",
        "Enfermaria Clínica",
        "Enfermaria Cirúrgica",
        "Centro Cirúrgico",
        "CME",
        "Farmácia",
        "Laboratório",
        "Radiologia/Imagem",
        "Ambulatório",
        "Recepção/Admissão",
        "Outro",
    ],
    "Categoria": [
        "Lesão por Pressão (LPP)",
        "Queda do Paciente",
        "Falha na Segurança Medicamentosa",
        "Falha de Identificação do Paciente",
        "Infecção Relacionada à Assistência",
        "Falha em Procedimento/Cirurgia",
        "Falha em Equipamento/Dispositivo",
        "Reação Transfusional",
        "Evento de Comunicação/Informação",
        "Violência / Agressão",
        "Extubação não Planejada",
        "Saída não Autorizada do Paciente",
        "Outro Incidente Assistencial",
    ],
    "Subcategoria_LPP": [
        "Estágio I",
        "Estágio II",
        "Estágio III",
        "Estágio IV",
        "Não Classificável",
        "Tecido Mucoso",
    ],
    "Subcategoria_Queda": [
        "Queda da própria altura",
        "Queda do leito",
        "Queda durante transferência",
        "Queda no banheiro",
    ],
    "Subcategoria_Med": [
        "Dose incorreta",
        "Medicamento errado",
        "Via errada",
        "Horário errado",
        "Omissão de dose",
        "Paciente errado",
    ],
    "Gravidade": [
        "Near Miss (Quase Evento - não atingiu o paciente)",
        "Sem Dano (atingiu, sem lesão)",
        "Dano Leve (lesão leve/temporária)",
        "Dano Moderado (lesão moderada/temporária)",
        "Dano Grave (lesão grave/permanente)",
        "Óbito",
    ],
    "Fator Causador": [
        "Comunicação inadequada",
        "Falha de processo/protocolo",
        "Sobrecarga de trabalho",
        "Equipamento inadequado/ausente",
        "Falta de treinamento",
        "Ambiente/infraestrutura",
        "Fator humano/distração",
        "Paciente não colaborativo",
        "Outro",
    ],
}


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "t", "yes", "y", "sim", "s")


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES (menus/opções)
# ══════════════════════════════════════════════════════════════════════════════


def load_config_table(tabela: str) -> pd.DataFrame:
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        return pd.DataFrame(columns=COLUNAS_CONFIG)

    sb = get_client()
    try:
        res = sb.table(table_name).select("*").order("Opcao").execute()
        rows = res.data or []
    except Exception:
        rows = []

    if not rows:
        defaults = DEFAULT_CONFIG_OPCOES.get(tabela, [])
        if defaults:
            try:
                sb.table(table_name).insert(
                    [{"Opcao": opcao, "Ativo": True} for opcao in defaults]
                ).execute()
                res = sb.table(table_name).select("*").order("Opcao").execute()
                rows = res.data or []
            except Exception:
                rows = [{"id": None, "Opcao": opcao, "Ativo": True} for opcao in defaults]

    df = _rows_to_df(rows, ["id", "Opcao", "Ativo"])
    df["Tabela"] = tabela
    return df[["id", "Tabela", "Opcao", "Ativo"]]


def load_config() -> pd.DataFrame:
    tables = []
    for tabela in CONFIG_TABLES:
        tables.append(load_config_table(tabela))
    if not tables:
        return pd.DataFrame(columns=COLUNAS_CONFIG)
    df = pd.concat(tables, ignore_index=True)
    return df.sort_values(["Tabela", "Opcao"]).reset_index(drop=True)


def save_config_opcao(row_id: int | str, tabela: str, opcao: str, ativo: bool) -> None:
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        raise ValueError(f"Tabela de configuração desconhecida: {tabela}")
    sb = get_client()
    sb.table(table_name).update({"Opcao": opcao, "Ativo": ativo}).eq("id", row_id).execute()


def delete_config_opcao(row_id: int | str, tabela: str) -> None:
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        raise ValueError(f"Tabela de configuração desconhecida: {tabela}")
    sb = get_client()
    sb.table(table_name).delete().eq("id", row_id).execute()


def add_config_opcao(tabela: str, opcao: str) -> None:
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        raise ValueError(f"Tabela de configuração desconhecida: {tabela}")
    sb = get_client()
    sb.table(table_name).insert({"Opcao": opcao, "Ativo": True}).execute()


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
# FLAGS DE CAMPOS (obrigatoriedade)
# Tabela esperada: config_campos (Campo TEXT, Obrigatorio BOOLEAN)
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_CAMPOS = [
    "Acoes_Imediatas","Categoria_Incidente","Data_Incidente","Data_Nascimento",
    "Data_Registro","Data_Relato","Descricao","Fatores_Causadores","Funcao_Relator",
    "Gravidade","Hora_Relato","Leito","Medicamento_Envolvido","Nome_Paciente",
    "Raca_Cor","Relator","Setor","Status","Subcategoria","Sugestao_Melhoria","Tipo_Geral","Turno",
]

def load_field_flags() -> pd.DataFrame:
    sb = get_client()
    try:
        res = sb.table("config_campos").select("*").order("Campo").execute()
        rows = res.data or []
    except Exception:
        rows = []
    if not rows:
        default_campos = [{"Campo": c, "Obrigatorio": False} for c in _DEFAULT_CAMPOS]
        try:
            sb.table("config_campos").insert(default_campos).execute()
            res = sb.table("config_campos").select("*").order("Campo").execute()
            rows = res.data or []
        except Exception:
            rows = [{"id": None, "Campo": c, "Obrigatorio": False} for c in _DEFAULT_CAMPOS]
    df = _rows_to_df(rows, ["id", "Campo", "Obrigatorio"])
    if "Obrigatorio" in df.columns:
        df["Obrigatorio"] = df["Obrigatorio"].apply(_to_bool)
    return df


def save_field_flag(row_id: int | str, obrigatorio: bool | str) -> None:
    sb = get_client()
    sb.table("config_campos").update({"Obrigatorio": _to_bool(obrigatorio)}).eq("id", row_id).execute()


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
