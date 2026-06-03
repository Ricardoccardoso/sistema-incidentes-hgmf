"""
db.py — Camada de acesso ao banco de dados (Supabase/PostgreSQL) para o sistema HGMF.

Responsabilidades deste módulo:
  - Criar e reutilizar o cliente Supabase (conexão única via cache)
  - Carregar, salvar, atualizar e excluir registros de incidentes
  - Gerenciar tabelas de configuração (menus/opções dos formulários)
  - Gerenciar usuários e suas permissões
  - Gerenciar flags de obrigatoriedade dos campos do formulário
  - Gerenciar registros de ação da equipe de segurança

Configuração necessária (uma única vez):
  1. Crie um projeto no Supabase (supabase.com)
  2. Execute o SQL de setup em supabase_setup.sql
  3. Nos Secrets do Streamlit Cloud adicione:
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
    """
    Cria e retorna o cliente Supabase, reutilizando a mesma instância
    em todas as sessões graças ao @st.cache_resource.

    Lê as credenciais na seguinte ordem de prioridade:
      1. st.secrets["supabase"] (Streamlit Cloud / secrets.toml local)
      2. Variáveis de ambiente SUPABASE_URL e SUPABASE_KEY

    Interrompe o app com mensagem de erro se as credenciais não forem encontradas.
    """
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


# ─── Utilitários internos ─────────────────────────────────────────────────────

def hash_senha(s: str) -> str:
    """
    Retorna o hash SHA-256 da senha em formato hexadecimal.
    Usado para armazenar e comparar senhas sem guardar o texto original.

    ATENÇÃO: SHA-256 sem sal é mais fraco que bcrypt. Recomenda-se migrar
    para hashlib.pbkdf2_hmac em versão futura.
    """
    return hashlib.sha256(s.encode()).hexdigest()


def _rows_to_df(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    """
    Converte a lista de dicts retornada pelo Supabase em um DataFrame pandas
    garantindo que todas as colunas esperadas existam (preenche com "" se ausente).

    Parâmetros:
      rows    — lista de dicionários vindos de res.data
      columns — lista de colunas que o DataFrame deve ter
    """
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def _to_bool(value) -> bool:
    """
    Converte qualquer representação de verdadeiro/falso para bool Python.
    Aceita True/False nativos, strings ("1", "true", "sim", "s", "t", "yes", "y")
    e None (retorna False).
    Necessário porque o Supabase pode retornar booleanos como strings em alguns contextos.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "t", "yes", "y", "sim", "s")


# ─── Definição das colunas esperadas por tabela ───────────────────────────────

# Colunas completas da tabela de incidentes — usadas para garantir estrutura do DataFrame
COLUNAS_INCIDENTES = [
    "id", "Data_Registro", "Data_Incidente", "Turno", "Setor",
    "Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade",
    "Fatores_Causadores", "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Data_Relato", "Hora_Relato", "Nome_Paciente", "Data_Nascimento", "Raca_Cor",
    "Relator", "Funcao_Relator", "Status",
]

# Colunas da tabela de configuração de menus
COLUNAS_CONFIG = ["id", "Tabela", "Opcao", "Ativo"]

# Colunas da tabela de usuários
COLUNAS_USUARIOS = ["id", "Usuario", "Senha_Hash", "Permissao", "Ativo", "Data_Criacao"]

# Mapeamento: nome lógico do menu → nome real da tabela no Supabase
CONFIG_TABLES = {
    "Turno":              "config_turno",
    "Tipo Geral":         "config_tipo_geral",
    "Setor":              "config_setor",
    "Categoria":          "config_categoria",
    "Subcategoria_LPP":   "config_subcategoria_lpp",
    "Subcategoria_Queda": "config_subcategoria_queda",
    "Subcategoria_Med":   "config_subcategoria_med",
    "Gravidade":          "config_gravidade",
    "Fator Causador":     "config_fator_causador",
}

# Valores padrão que são inseridos automaticamente quando a tabela está vazia
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


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE MENUS (opções dos selectboxes do formulário)
# ══════════════════════════════════════════════════════════════════════════════

def load_config_table(tabela: str) -> pd.DataFrame:
    """
    Carrega as opções de uma tabela de configuração específica do Supabase.

    Se a tabela estiver vazia, insere os valores padrão definidos em DEFAULT_CONFIG_OPCOES.
    Se a inserção falhar (ex: RLS bloqueado), usa os padrões apenas em memória.

    Parâmetros:
      tabela — chave do dicionário CONFIG_TABLES (ex: "Turno", "Setor")

    Retorna DataFrame com colunas: id, Tabela, Opcao, Ativo
    """
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        return pd.DataFrame(columns=COLUNAS_CONFIG)

    sb = get_client()
    try:
        res = sb.table(table_name).select("*").order("Opcao").execute()
        rows = res.data or []
    except Exception:
        rows = []  # silencia erros de RLS ou tabela inexistente

    # Se não há dados, tenta semear com os valores padrão
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
                # Fallback em memória caso o banco bloqueie a inserção
                rows = [{"id": None, "Opcao": opcao, "Ativo": True} for opcao in defaults]

    df = _rows_to_df(rows, ["id", "Opcao", "Ativo"])
    df["Tabela"] = tabela
    return df[["id", "Tabela", "Opcao", "Ativo"]]


def load_config() -> pd.DataFrame:
    """
    Carrega todas as tabelas de configuração e retorna um DataFrame unificado,
    ordenado por Tabela e Opcao.
    Usado para popular os selectboxes e outros campos de seleção do formulário.
    """
    tables = []
    for tabela in CONFIG_TABLES:
        tables.append(load_config_table(tabela))
    if not tables:
        return pd.DataFrame(columns=COLUNAS_CONFIG)
    df = pd.concat(tables, ignore_index=True)
    return df.sort_values(["Tabela", "Opcao"]).reset_index(drop=True)


def save_config_opcao(row_id: int | str, tabela: str, opcao: str, ativo: bool) -> None:
    """
    Atualiza o nome e o status (ativo/inativo) de uma opção de configuração existente.

    Parâmetros:
      row_id — id da linha no banco
      tabela — nome lógico da tabela (ex: "Turno")
      opcao  — novo texto da opção
      ativo  — se a opção deve aparecer nos menus (True = visível)
    """
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        raise ValueError(f"Tabela de configuração desconhecida: {tabela}")
    sb = get_client()
    sb.table(table_name).update({"Opcao": opcao, "Ativo": ativo}).eq("id", row_id).execute()


def delete_config_opcao(row_id: int | str, tabela: str) -> None:
    """
    Remove permanentemente uma opção de configuração pelo seu id.

    Parâmetros:
      row_id — id da linha a ser removida
      tabela — nome lógico da tabela (ex: "Setor")
    """
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        raise ValueError(f"Tabela de configuração desconhecida: {tabela}")
    sb = get_client()
    sb.table(table_name).delete().eq("id", row_id).execute()


def add_config_opcao(tabela: str, opcao: str) -> None:
    """
    Insere uma nova opção em uma tabela de configuração, já marcada como ativa.

    Parâmetros:
      tabela — nome lógico da tabela (ex: "Categoria")
      opcao  — texto da nova opção a ser adicionada
    """
    table_name = CONFIG_TABLES.get(tabela)
    if not table_name:
        raise ValueError(f"Tabela de configuração desconhecida: {tabela}")
    sb = get_client()
    sb.table(table_name).insert({"Opcao": opcao, "Ativo": True}).execute()


# ══════════════════════════════════════════════════════════════════════════════
# INCIDENTES — operações CRUD na tabela principal
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> pd.DataFrame:
    """
    Carrega todos os registros de incidentes do banco, ordenados do mais
    recente para o mais antigo (Data_Registro desc).
    Retorna um DataFrame com todas as colunas definidas em COLUNAS_INCIDENTES.
    """
    sb = get_client()
    res = sb.table("incidentes").select("*").order("Data_Registro", desc=True).execute()
    return _rows_to_df(res.data or [], COLUNAS_INCIDENTES)


def save_incidente(novo: dict) -> None:
    """
    Insere um novo registro de incidente no banco.
    Remove a chave 'id' do dicionário antes de inserir, pois ela é auto-gerada
    pelo banco (BIGSERIAL).

    Parâmetros:
      novo — dicionário com todos os campos do incidente
    """
    sb = get_client()
    novo.pop("id", None)
    sb.table("incidentes").insert(novo).execute()


def update_incidente(row_id: int | str, campos: dict) -> None:
    """
    Atualiza campos específicos de um incidente existente.
    Remove 'id' do dicionário de campos para evitar conflito na query.

    Parâmetros:
      row_id — id do incidente a ser atualizado
      campos — dicionário com os campos e novos valores
    """
    sb = get_client()
    campos.pop("id", None)
    sb.table("incidentes").update(campos).eq("id", row_id).execute()


def delete_incidente(row_id: int | str) -> None:
    """
    Remove permanentemente um incidente pelo seu id.

    Parâmetros:
      row_id — id do incidente a ser excluído
    """
    sb = get_client()
    sb.table("incidentes").delete().eq("id", row_id).execute()


# ══════════════════════════════════════════════════════════════════════════════
# REGISTROS DE AÇÃO — acompanhamento pela equipe de segurança do paciente
# ══════════════════════════════════════════════════════════════════════════════

def load_registros_acao(incidente_id) -> pd.DataFrame:
    """
    Carrega todos os registros de ação vinculados a um incidente específico,
    ordenados do mais antigo para o mais recente (para exibir como linha do tempo).

    Parâmetros:
      incidente_id — id do incidente pai

    Retorna DataFrame com colunas: id, Incidente_Id, Data_Registro, Descricao, Usuario
    """
    sb = get_client()
    try:
        res = (sb.table("registro_acoes")
               .select("*")
               .eq("Incidente_Id", incidente_id)
               .order("Data_Registro", desc=False)
               .execute())
        rows = res.data or []
    except Exception:
        rows = []  # silencia erro se a tabela ainda não existe
    return _rows_to_df(rows, ["id", "Incidente_Id", "Data_Registro", "Descricao", "Usuario"])


def save_registro_acao(incidente_id, descricao: str, usuario: str) -> None:
    """
    Insere um novo registro de ação para um incidente, com timestamp automático.

    Parâmetros:
      incidente_id — id do incidente ao qual o registro pertence
      descricao    — texto descrevendo a ação realizada pela equipe
      usuario      — login do usuário que inseriu o registro
    """
    sb = get_client()
    sb.table("registro_acoes").insert({
        "Incidente_Id": incidente_id,
        "Data_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Descricao": descricao.strip(),
        "Usuario": usuario,
    }).execute()


def delete_registro_acao(row_id) -> None:
    """
    Remove um registro de ação específico pelo seu id.

    Parâmetros:
      row_id — id do registro a ser excluído
    """
    sb = get_client()
    sb.table("registro_acoes").delete().eq("id", row_id).execute()


# ══════════════════════════════════════════════════════════════════════════════
# FLAGS DE OBRIGATORIEDADE DOS CAMPOS
# Tabela: config_campos (Campo TEXT, Obrigatorio BOOLEAN)
# Controla quais campos do formulário são exibidos com asterisco e validados
# ══════════════════════════════════════════════════════════════════════════════

# Lista de todos os campos configuráveis — usada para semear a tabela se vazia
_DEFAULT_CAMPOS = [
    "Acoes_Imediatas", "Categoria_Incidente", "Data_Incidente", "Data_Nascimento",
    "Data_Registro", "Data_Relato", "Descricao", "Fatores_Causadores", "Funcao_Relator",
    "Gravidade", "Hora_Relato", "Leito", "Medicamento_Envolvido", "Nome_Paciente",
    "Raca_Cor", "Relator", "Setor", "Status", "Subcategoria", "Sugestao_Melhoria",
    "Tipo_Geral", "Turno",
]


def load_field_flags() -> pd.DataFrame:
    """
    Carrega a configuração de obrigatoriedade de cada campo do formulário.

    Se a tabela estiver vazia, insere todos os campos com Obrigatorio=False.
    Garante que a coluna Obrigatorio seja sempre booleana Python (via _to_bool).

    Retorna DataFrame com colunas: id, Campo, Obrigatorio
    """
    sb = get_client()
    try:
        res = sb.table("config_campos").select("*").order("Campo").execute()
        rows = res.data or []
    except Exception:
        rows = []

    # Semeia a tabela com todos os campos (não obrigatórios) se estiver vazia
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
    """
    Atualiza o flag de obrigatoriedade de um campo específico.

    Parâmetros:
      row_id      — id da linha em config_campos
      obrigatorio — novo valor booleano (ou string conversível)
    """
    sb = get_client()
    sb.table("config_campos").update({"Obrigatorio": _to_bool(obrigatorio)}).eq("id", row_id).execute()


def get_opcoes(df_conf: pd.DataFrame, tabela: str) -> list[str]:
    """
    Filtra o DataFrame de configuração para retornar apenas as opções
    ativas de uma determinada tabela/menu.

    Parâmetros:
      df_conf — DataFrame retornado por load_config()
      tabela  — nome lógico da tabela (ex: "Turno", "Setor")

    Retorna lista de strings com as opções ativas, ou ["Sem opções configuradas"]
    se não houver nenhuma.
    """
    ops = df_conf[(df_conf["Tabela"] == tabela) & (df_conf["Ativo"] == True)]["Opcao"].tolist()
    return ops if ops else ["Sem opções configuradas"]


# ══════════════════════════════════════════════════════════════════════════════
# USUÁRIOS — autenticação e gerenciamento de acesso
# ══════════════════════════════════════════════════════════════════════════════

def load_users() -> pd.DataFrame:
    """
    Carrega todos os usuários cadastrados no banco.

    Se a tabela estiver vazia (primeira execução), cria automaticamente
    um usuário 'admin' com senha 'admin123' e permissão 'Acesso Total'.

    Retorna DataFrame com colunas: id, Usuario, Senha_Hash, Permissao, Ativo, Data_Criacao
    """
    sb = get_client()
    res = sb.table("usuarios").select("*").execute()
    rows = res.data or []
    if not rows:
        # Cria usuário admin padrão na primeira execução do sistema
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
    """
    Cria um novo usuário no banco.
    Remove 'id' do dicionário antes de inserir (auto-gerado pelo banco).

    Parâmetros:
      novo — dicionário com Usuario, Senha_Hash, Permissao, Ativo, Data_Criacao
    """
    sb = get_client()
    novo.pop("id", None)
    sb.table("usuarios").insert(novo).execute()


def update_user(row_id: int | str, campos: dict) -> None:
    """
    Atualiza dados de um usuário existente (ex: senha, permissão, ativo).
    Remove 'id' do dicionário de campos para evitar conflito.

    Parâmetros:
      row_id — id do usuário a ser atualizado
      campos — dicionário com os campos e novos valores
    """
    sb = get_client()
    campos.pop("id", None)
    sb.table("usuarios").update(campos).eq("id", row_id).execute()


def delete_user(row_id: int | str) -> None:
    """
    Remove permanentemente um usuário pelo seu id.
    Não pode ser desfeito — use update_user com Ativo=False para desativar.

    Parâmetros:
      row_id — id do usuário a ser excluído
    """
    sb = get_client()
    sb.table("usuarios").delete().eq("id", row_id).execute()
