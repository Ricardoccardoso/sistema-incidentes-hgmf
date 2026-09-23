"""
rotinas/constantes.py — Constantes compartilhadas pelo Painel de Gestão.

Colunas de dados, opções de status, definição dos menus/abas, rótulos de
campo (usados em Configurar Menus) e o mapeamento de gravidade → classe CSS
(usado para colorir a borda dos cards de notificação).
"""

COLUNAS_DADOS = [
    "id", "Data_Registro", "Data_Incidente", "Turno", "Setor",
    "Leito", "Tipo_Geral", "Categoria_Incidente", "Subcategoria",
    "Medicamento_Envolvido", "Gravidade",
    "Fatores_Causadores", "Descricao", "Acoes_Imediatas", "Sugestao_Melhoria",
    "Data_Relato", "Hora_Relato", "Nome_Paciente", "Data_Nascimento",
    "Relator", "Funcao_Relator", "Status"
]

STATUS_OPTS  = ["Novo", "Investigar", "Notificar", "Em Análise", "Pendência", "Concluído", "Anulado"]
MENU_OPTIONS = [
    ("📊 Dashboard", "Dashboard"),
    ("📋 Notificações", "Notificações"),
    ("📈 Relatórios", "Relatórios"),
    ("📁 Exportar Dados", "Exportar Dados"),
    ("⚙️ Configurar Menus", "Configurar Menus"),
    ("👥 Usuários", "Usuários"),
]
MENU_LABELS = [label for _, label in MENU_OPTIONS]

CAMPO_LABELS = {
    "Acoes_Imediatas":      "Ações Imediatas",
    "Categoria_Incidente":  "Categoria do Incidente",
    "Data_Incidente":       "Data do Incidente",
    "Data_Nascimento":      "Data de Nascimento",
    "Data_Internacao":      "Data de Internação / Atendimento",
    "Data_Registro":        "Data do Registro",
    "Data_Relato":          "Data do Relato",
    "Descricao":            "Descrição do Incidente",
    "Fatores_Causadores":   "Fatores Causadores",
    "Funcao_Relator":       "Função / Cargo do Relator",
    "Gravidade":            "Gravidade",
    "Hora_Relato":          "Hora do Relato",
    "Leito":                "Leito",
    "Medicamento_Envolvido":"Medicamento Envolvido",
    "Nome_Paciente":        "Nome do Paciente",
    "Raca_Cor":             "Raça / Cor",
    "Relator":              "Nome do Relator",
    "Setor":                "Setor / Unidade",
    "Status":               "Status",
    "Subcategoria":         "Subcategoria",
    "Sugestao_Melhoria":    "Sugestão de Melhoria",
    "Tipo_Geral":           "Tipo Geral",
    "Turno":                "Hora/Turno",
}

GRAVIDADE_CORES = {
    "Near Miss": "near",
    "Sem Dano":  "semDano",
    "Dano Leve": "leve",
    "Dano Moderado": "moderado",
    "Dano Grave": "grave",
    "Óbito":     "grave",
}


def cor_gravidade(g: str) -> str:
    """
    Retorna a classe CSS correspondente ao nível de gravidade do incidente.
    Usada para colorir a borda esquerda dos cards de notificação.

    Parâmetros:
      g — string de gravidade (ex: "Dano Grave (lesão grave/permanente)")

    Retorna uma das classes: "near", "semDano", "leve", "moderado", "grave"
    """
    for k, v in GRAVIDADE_CORES.items():
        if k.lower() in str(g).lower():
            return v
    return "semDano"  # padrão verde quando a gravidade não é reconhecida
