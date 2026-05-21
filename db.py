"""
db.py — camada de persistência Supabase (PostgreSQL na nuvem)
Usado tanto pelo app.py (notificação) quanto pelo Gestao.py (painel de gestão).

Configuração:
  Crie um projeto gratuito em https://supabase.com
  Vá em Project Settings > API e copie:
    - Project URL  → SUPABASE_URL
    - anon/public key → SUPABASE_KEY
  Adicione essas duas variáveis em .streamlit/secrets.toml:
    SUPABASE_URL = "https://xxxx.supabase.co"
    SUPABASE_KEY = "eyJ..."

Execute o SQL abaixo no Supabase SQL Editor para criar as tabelas:

  CREATE TABLE IF NOT EXISTS incidentes (
    id BIGSERIAL PRIMARY KEY,
    "Data_Registro" TEXT, "Data_Incidente" TEXT, "Hora_Aproximada" TEXT,
    "Turno" TEXT, "Setor" TEXT, "Cama_Leito" TEXT, "Tipo_Geral" TEXT,
    "Categoria_Incidente" TEXT, "Subcategoria" TEXT, "Medicamento_Envolvido" TEXT,
    "Gravidade" TEXT, "Dano_Paciente" TEXT, "Paciente_Foi_Comunicado" TEXT,
    "Familiar_Foi_Comunicado" TEXT, "Medico_Foi_Comunicado" TEXT,
    "Fatores_Causadores" TEXT, "Descricao" TEXT, "Acoes_Imediatas" TEXT,
    "Sugestao_Melhoria" TEXT, "Relator" TEXT, "Funcao_Relator" TEXT, "Status" TEXT
  );

  CREATE TABLE IF NOT EXISTS config_tabelas (
    id BIGSERIAL PRIMARY KEY,
    "Tabela" TEXT, "Opcao" TEXT, "Ativo" BOOLEAN DEFAULT TRUE
  );

  CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    "Usuario" TEXT UNIQUE, "Senha_Hash" TEXT,
    "Permissao" TEXT, "Ativo" BOOLEAN DEFAULT TRUE, "Data_Criacao" TEXT
  );
"""

import streamlit as st
import pandas as pd
from supabase import create_client, Client
import hashlib

# ── Cliente Supabase ──────────────────────────────────────────────────────────
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ── INCIDENTES ────────────────────────────────────────────────────────────────
COLUNAS_DADOS = [
    "Data_Registro", "Data_Incidente", "Hora_Aproximada", "Turno", "Setor",
    "Cama_Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade", "Dano_Paciente",
    "Paciente_Foi_Comunicado", "Familiar_Foi_Comunicado", "Medico_Foi_Comunicado",
    "Fatores_Causadores", "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Relator", "Funcao_Relator", "Status"
]

def load_data() -> pd.DataFrame:
    try:
        sb = get_client()
        res = sb.table("incidentes").select("*").order("id").execute()
        rows = res.data or []
        if not rows:
            return pd.DataFrame(columns=COLUNAS_DADOS)
        df = pd.DataFrame(rows)
        # Remove coluna id interna do Supabase para não conflitar com o código
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        for col in COLUNAS_DADOS:
            if col not in df.columns:
                df[col] = ""
        return df[COLUNAS_DADOS]
    except Exception as e:
        st.error(f"Erro ao carregar incidentes: {e}")
        return pd.DataFrame(columns=COLUNAS_DADOS)


def insert_incidente(novo: dict) -> bool:
    """Insere um único registro na tabela incidentes."""
    try:
        sb = get_client()
        # Garante que todos os campos existam
        row = {col: novo.get(col, "") for col in COLUNAS_DADOS}
        sb.table("incidentes").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar incidente: {e}")
        return False


def update_status(row_id: int, novo_status: str) -> bool:
    """Atualiza somente o campo Status de um registro."""
    try:
        sb = get_client()
        sb.table("incidentes").update({"Status": novo_status}).eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False


def load_data_with_id() -> pd.DataFrame:
    """Versão com coluna 'id' — usada no painel de gestão para atualização de status."""
    try:
        sb = get_client()
        res = sb.table("incidentes").select("*").order("id").execute()
        rows = res.data or []
        if not rows:
            df = pd.DataFrame(columns=["id"] + COLUNAS_DADOS)
            return df
        df = pd.DataFrame(rows)
        for col in COLUNAS_DADOS:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Erro ao carregar incidentes: {e}")
        return pd.DataFrame(columns=["id"] + COLUNAS_DADOS)


# ── CONFIGURAÇÕES DE TABELAS ──────────────────────────────────────────────────
OPCOES_PADRAO = [
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
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio I",         "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio II",        "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio III",       "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Estágio IV",        "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Não Classificável", "Ativo": True},
    {"Tabela": "Subcategoria_LPP", "Opcao": "Tecido Mucoso",     "Ativo": True},
    # Subcategorias Queda
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda da própria altura",     "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda do leito",              "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda durante transferência", "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Queda no banheiro",           "Ativo": True},
    {"Tabela": "Subcategoria_Queda", "Opcao": "Outro",                       "Ativo": True},
    # Subcategorias Medicamento
    {"Tabela": "Subcategoria_Med", "Opcao": "Dose errada",        "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Medicamento errado", "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Via errada",         "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Horário errado",     "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Omissão de dose",    "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Paciente errado",    "Ativo": True},
    {"Tabela": "Subcategoria_Med", "Opcao": "Reação adversa",     "Ativo": True},
    # Gravidade
    {"Tabela": "Gravidade", "Opcao": "Near Miss (Quase Evento - não atingiu o paciente)", "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Sem Dano (atingiu, sem lesão)",                     "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Dano Leve (lesão leve/temporária)",                 "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Dano Moderado (lesão moderada/temporária)",         "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Dano Grave (lesão grave/permanente)",               "Ativo": True},
    {"Tabela": "Gravidade", "Opcao": "Óbito",                                             "Ativo": True},
    # Fatores Causadores
    {"Tabela": "Fator Causador", "Opcao": "Déficit de pessoal / Sobrecarga",        "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falha na comunicação entre equipes",     "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falha na comunicação escrita/verbal",    "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falta de treinamento / capacitação",     "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Equipamento com defeito",                "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falta de material / insumo",             "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Ambiente inadequado / risco físico",     "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falha no processo/protocolo",            "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Distração / interrupção",                "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Erro humano (sem negligência)",          "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Falha no sistema de medicação",          "Ativo": True},
    {"Tabela": "Fator Causador", "Opcao": "Causa ainda não identificada",           "Ativo": True},
]


def load_config() -> pd.DataFrame:
    try:
        sb = get_client()
        res = sb.table("config_tabelas").select("*").execute()
        rows = res.data or []
        if not rows:
            # Popula com os padrões na primeira execução
            sb.table("config_tabelas").insert(OPCOES_PADRAO).execute()
            return pd.DataFrame(OPCOES_PADRAO)
        df = pd.DataFrame(rows)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar config: {e}")
        return pd.DataFrame(OPCOES_PADRAO)


def save_config_opcao(tabela: str, opcao: str, ativo: bool) -> bool:
    """Altera o campo Ativo de uma opção existente."""
    try:
        sb = get_client()
        sb.table("config_tabelas").update({"Ativo": ativo})\
          .eq("Tabela", tabela).eq("Opcao", opcao).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar config: {e}")
        return False


def add_config_opcao(tabela: str, opcao: str) -> bool:
    """Adiciona nova opção de configuração."""
    try:
        sb = get_client()
        sb.table("config_tabelas").insert({"Tabela": tabela, "Opcao": opcao, "Ativo": True}).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar opção: {e}")
        return False


def get_opcoes(df_conf: pd.DataFrame, tabela: str):
    ops = df_conf[(df_conf["Tabela"] == tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return ops if ops else ["Sem opções configuradas"]


# ── USUÁRIOS ──────────────────────────────────────────────────────────────────
def hash_senha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def load_users() -> pd.DataFrame:
    try:
        sb = get_client()
        res = sb.table("usuarios").select("*").execute()
        rows = res.data or []
        if not rows:
            admin = {
                "Usuario": "admin",
                "Senha_Hash": hash_senha("admin123"),
                "Permissao": "Acesso Total",
                "Ativo": True,
                "Data_Criacao": pd.Timestamp.now().strftime("%Y-%m-%d"),
            }
            sb.table("usuarios").insert(admin).execute()
            return pd.DataFrame([admin])
        df = pd.DataFrame(rows)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")
        return pd.DataFrame(columns=["Usuario","Senha_Hash","Permissao","Ativo","Data_Criacao"])


def save_user(usuario: dict) -> bool:
    """Insere ou atualiza usuário (upsert pelo campo Usuario)."""
    try:
        sb = get_client()
        sb.table("usuarios").upsert(usuario, on_conflict="Usuario").execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar usuário: {e}")
        return False


def delete_user(usuario: str) -> bool:
    try:
        sb = get_client()
        sb.table("usuarios").delete().eq("Usuario", usuario).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao remover usuário: {e}")
        return False
