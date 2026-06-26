"""
app.py — Formulário público de notificação de incidentes — HGMF

Esta é a página principal do sistema, acessível sem login.
Permite que qualquer profissional do hospital registre um incidente
de forma sigilosa, preenchendo dados do evento, paciente e relato.

Fluxo:
  1. Carrega configurações de menus (opções de selectbox) do Supabase
  2. Carrega flags de obrigatoriedade dos campos
  3. Exibe o formulário de notificação
  4. Ao enviar, valida campos obrigatórios e salva no banco
  5. Script JS injeta cálculo de idade em tempo real via polling DOM
"""

import streamlit as st
import streamlit.components.v1 as components  # necessário para injetar JS no DOM
import pandas as pd
import os
import base64
from datetime import datetime, date
import db  # camada de acesso ao Supabase
from version import __version__

# ─── Configuração da página ───────────────────────────────────────────────────
# layout="centered" limita a largura para melhor legibilidade do formulário
st.set_page_config(
    page_title="Notificação de Incidente - HGMF",
    page_icon="🏥",
    layout="centered"
)

# ─── CSS global ───────────────────────────────────────────────────────────────
# Oculta elementos padrão do Streamlit (sidebar, header, footer, deploy button)
# e aplica identidade visual do HGMF (fonte Inter, cores azuis, cards, badges)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

[data-testid="stSidebar"]          {display:none !important;}
[data-testid="stAppDeployButton"]  {display:none !important;}
[data-testid="stHeader"]           {display:none !important; visibility:hidden !important;}
header                             {display:none !important; visibility:hidden !important;}
[data-testid="stDecoration"]       {display:none !important;}
footer                             {display:none !important;}
[data-testid="stSidebarNav"]       {display:none !important;}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Largura máxima do conteúdo — melhor para formulários em tela cheia */
.block-container { padding-top: 1.5rem !important; max-width: 780px; }

/* Cabeçalho com gradiente azul do hospital */
.cabecalho {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%);
    border-radius: 4px;
    padding: 28px 32px 22px 32px;
    margin-bottom: 24px;
    box-shadow: 0 4px 24px rgba(13,71,161,0.18);
    text-align: center;
}
.cabecalho h1 { color: #fff; font-size: 1.45rem; font-weight: 700; margin:0 0 4px 0; letter-spacing:-0.3px; }
.cabecalho p  { color: #bbdefb; font-size: 0.88rem; margin:0; }

/* Banner de sigilo exibido abaixo do cabeçalho */
.aviso-sigilo {
    background: #e3f2fd;
    border-left: 4px solid #1976d2;
    border-radius: 2px;
    padding: 12px 18px;
    margin-bottom: 20px;
    color: #0d47a1;
    font-size: 0.88rem;
    font-weight: 500;
}

/* Títulos de seção dentro do formulário (ex: "Dados do Evento") */
.secao-titulo {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #1565c0;
    margin: 22px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 2px solid #e3f2fd;
}

/* Botão de envio do formulário — estilo primário azul */
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #0d47a1, #1976d2) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 14px !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 4px 14px rgba(13,71,161,0.3) !important;
    transition: all 0.2s !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(13,71,161,0.4) !important;
}

/* Tamanho de fonte uniforme para labels dos campos */
div[data-testid="stRadio"] > label          { font-size: 0.9rem; }
div[data-testid="stSelectbox"] > label      { font-size: 0.9rem; font-weight:500; }
div[data-testid="stTextInput"] > label      { font-size: 0.9rem; font-weight:500; }
div[data-testid="stTextArea"] > label       { font-size: 0.9rem; font-weight:500; }
div[data-testid="stMultiSelect"] > label    { font-size: 0.9rem; font-weight:500; }
div[data-testid="stDateInput"] > label      { font-size: 0.9rem; font-weight:500; }
div[data-testid="stSelectSlider"] > label   { font-size: 0.9rem; font-weight:500; }
div[data-testid="stCheckbox"] > label       { font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)

# ─── Aliases para funções do módulo db ───────────────────────────────────────
# Mantém o código do formulário mais legível sem prefixo "db."
load_data   = db.load_data
load_config = db.load_config
# getattr com fallback caso a função não exista em versões antigas do módulo
load_field_flags = getattr(db, "load_field_flags", lambda: pd.DataFrame())


def get_opcoes(df_conf, tabela):
    """Retorna lista de opções ativas de um menu de configuração."""
    return db.get_opcoes(df_conf, tabela)


# ─── Ordem canônica de gravidade para o select_slider ────────────────────────
# Define a sequência lógica de crescente para decrescente do nível de dano
GRAVIDADE_ORDEM = [
    "Near Miss (Quase Evento - não atingiu o paciente)",
    "Sem Dano (atingiu, sem lesão)",
    "Dano Leve (lesão leve/temporária)",
    "Dano Moderado (lesão moderada/temporária)",
    "Dano Grave (lesão grave/permanente)",
    "Óbito",
]


def ordenar_gravidade(opcoes):
    """
    Ordena as opções de gravidade conforme a sequência clínica definida em GRAVIDADE_ORDEM.
    Opções não reconhecidas são colocadas ao final.
    """
    ordem = {valor: indice for indice, valor in enumerate(GRAVIDADE_ORDEM)}
    return sorted(opcoes, key=lambda x: ordem.get(x, len(opcoes)))


# ─── Cabeçalho com logo ───────────────────────────────────────────────────────
# Tenta carregar o logo.png do diretório do script; se não encontrar, exibe
# apenas texto. Isso evita erros em ambientes de deploy que alteram o cwd.
logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
if not os.path.exists(logo_path):
    logo_path = "logo.png"

if os.path.exists(logo_path):
    try:
        with open(logo_path, "rb") as f:
            b = f.read()
        b64 = base64.b64encode(b).decode()
        img_tag = f'<img src="data:image/png;base64,{b64}" style="height:76px; display:block; margin:0 auto 8px;" />'
        st.markdown(f"""
        <div class="cabecalho">
            {img_tag}
            <h1 style="margin:6px 0 0; font-size:1.25rem">Hospital Geral Menandro de Faria</h1>
            <p style="margin:0; color:#bbdefb">Núcleo de Segurança do Paciente — Notificação de Incidente</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        # Fallback sem imagem caso a leitura do arquivo falhe
        st.markdown("""
        <div class="cabecalho">
            <h1>🏥 Hospital Geral Menandro de Faria</h1>
            <p>Núcleo de Segurança do Paciente — Notificação de Incidente</p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="cabecalho">
        <h1>🏥 Hospital Geral Menandro de Faria</h1>
        <p>Núcleo de Segurança do Paciente — Notificação de Incidente</p>
    </div>
    """, unsafe_allow_html=True)

# Banner de sigilo e versão do sistema
st.markdown(f"""
<div class="aviso-sigilo">
    🔒 <strong>Notificação sigilosa, a identificação do notificador é opcional.</strong>
</div>
<div style="text-align: right; font-size: 0.75rem; color: #999; margin-bottom: 12px;">v{__version__}</div>
""", unsafe_allow_html=True)

# ─── Carregamento de dados de configuração ────────────────────────────────────
# Carregado fora do formulário para não recarregar a cada interação interna
df_config = load_config()   # opções dos selectboxes (turnos, setores, categorias, etc.)
df_dados  = load_data()     # incidentes já registrados (usado apenas como referência)

# Carrega flags de obrigatoriedade — define quais campos são marcados com *
try:
    fflags = load_field_flags()
except Exception:
    fflags = pd.DataFrame()  # fallback vazio se tabela não existir


def label(campo, texto):
    """
    Retorna o texto do label com asterisco (*) se o campo estiver marcado
    como obrigatório na tabela config_campos. Caso contrário, retorna o texto puro.

    Parâmetros:
      campo — nome interno do campo (ex: "Descricao", "Setor")
      texto — texto a ser exibido ao usuário
    """
    try:
        req = bool(fflags[fflags["Campo"] == campo]["Obrigatorio"].iloc[0])
    except Exception:
        req = False
    return texto + (" *" if req else "")


# ─── Formulário principal de notificação ─────────────────────────────────────
# clear_on_submit=True limpa automaticamente todos os campos após envio bem-sucedido
with st.form("form_notificacao", clear_on_submit=True):

    # ── BLOCO 1: Dados do Evento ──────────────────────────────────────────────
    # Informações sobre quando e onde o incidente ocorreu
    st.markdown('<div class="secao-titulo">📅 Dados do Evento</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        data_incidente = st.date_input(
            label("Data_Incidente", "Data do Incidente"),
            value=date.today(),
            max_value=date.today(),  # impede datas futuras
            format="DD/MM/YYYY"
        )
    with c2:
        turno = st.selectbox(label("Turno", "Hora/Turno do Incidente"), get_opcoes(df_config, "Turno"))
    with c3:
        # Data do registro é gerada automaticamente — campo apenas leitura
        st.date_input(
            label("Data_Registro", "Data do Registro"),
            value=date.today(),
            format="DD/MM/YYYY",
            disabled=True
        )

    c4, c5 = st.columns([3, 1])
    with c4:
        setor = st.selectbox(label("Setor", "Setor / Unidade de Ocorrência"), get_opcoes(df_config, "Setor"))
    with c5:
        cama = st.text_input(label("Leito", "Leito"), placeholder="Ex: 12A")

    # ── BLOCO 2: Dados do Relato e do Paciente ────────────────────────────────
    # Identifica quando o relato foi feito e dados básicos do paciente envolvido
    st.markdown('<div class="secao-titulo">📝 Dados do Relato / Paciente</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1.5, 1.5, 4])
    with r1:
        data_relato = st.date_input(
            label("Data_Relato", "Data do Relato"),
            value=date.today(),
            format="DD/MM/YYYY"
        )
    with r2:
        hora_relato = st.time_input(label("Hora_Relato", "Hora do Relato"))
    with r3:
        nome_paciente = st.text_input(label("Nome_Paciente", "Nome do Paciente"), placeholder="Ex: João da Silva")

    s1, s2, s3 = st.columns([2, 1, 2])
    with s1:
        # value=None exibe o campo vazio — a idade só é calculada quando preenchido
        data_nasc = st.date_input(
            label("Data_Nascimento", "Data de Nascimento do Paciente"),
            value=None,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )
    with s2:
        # Cálculo de idade baseado na data de nascimento selecionada
        # O campo é desabilitado (somente leitura) — atualizado também via JS externo
        if data_nasc:
            hoje = date.today()
            idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
            idade_txt = f"{idade} anos"
        else:
            idade_txt = "—"
        st.text_input("Idade", value=idade_txt, disabled=True)
    with s3:
        raca_cor = st.selectbox(
            label("Raca_Cor", "Raça / Cor"),
            ["Não informado", "Branca", "Preta", "Parda", "Amarela", "Indígena"]
        )

    t1, t2 = st.columns([2, 4])
    with t1:
        data_internacao = st.date_input(
            label("Data_Internacao", "Data de Internação / Atendimento"),
            value=None,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )

    # ── BLOCO 3: Tipo do Incidente ────────────────────────────────────────────
    # Classifica o incidente por tipo, categoria e subcategoria
    st.markdown('<div class="secao-titulo">📋 Tipo do Incidente</div>', unsafe_allow_html=True)
    tipo_geral = st.radio(
        label("Tipo_Geral", "Natureza do incidente"),
        get_opcoes(df_config, "Tipo Geral"),
        horizontal=True
    )

    categoria = st.selectbox(label("Categoria_Incidente", "Categoria do Incidente"), get_opcoes(df_config, "Categoria"))

    # Subcategorias e campos adicionais aparecem dinamicamente conforme a categoria
    subcategoria = ""
    medicamento  = ""

    if categoria == "Lesão por Pressão (LPP)":
        subcategoria = st.selectbox("Estágio da LPP", get_opcoes(df_config, "Subcategoria_LPP"))
        local_lpp = st.text_input("Região anatômica afetada", placeholder="Ex: sacral, calcâneo direito")
        subcategoria = subcategoria + (f" — {local_lpp}" if local_lpp else "")

    elif categoria == "Queda do Paciente":
        subcategoria = st.selectbox("Tipo de Queda", get_opcoes(df_config, "Subcategoria_Queda"))

    elif categoria == "Falha na Segurança Medicamentosa":
        subcategoria = st.selectbox("Tipo de Falha Medicamentosa", get_opcoes(df_config, "Subcategoria_Med"))
        medicamento  = st.text_input("Medicamento(s) envolvido(s)", placeholder="Ex: Heparina 5000 UI")

    descricao = st.text_area(
        label("Descricao", "Descreva o que aconteceu (O quê? Como? Onde? Sequência dos fatos)"),
        height=130,
        placeholder="Relate os fatos de forma objetiva. Ex: Paciente em pós-op imediato foi encontrado no chão ao lado do leito às 14h30..."
    )

    # ── BLOCO 4: Gravidade e Dano ─────────────────────────────────────────────
    # Escala de severidade do dano causado ao paciente
    st.markdown('<div class="secao-titulo">⚠️ Gravidade e Dano</div>', unsafe_allow_html=True)
    # A ordem das opções vem diretamente do banco (coluna Ordem da tabela config_gravidade)
    # O slider exibe apenas o nome curto (antes do parêntese); a descrição completa aparece abaixo.
    gravidade_ops = get_opcoes(df_config, "Gravidade")
    gravidade_labels = [op.split("(")[0].strip() for op in gravidade_ops]
    gravidade_full   = dict(zip(gravidade_labels, gravidade_ops))
    gravidade_label  = st.select_slider(label("Gravidade", "Nível de Gravidade / Classificação do Dano"), options=gravidade_labels)
    gravidade_descr  = gravidade_full.get(gravidade_label, gravidade_label)
    if "(" in gravidade_descr:
        st.caption(gravidade_descr)
    gravidade = gravidade_descr  # valor completo salvo no banco

    # ── BLOCO 5: Fatores Causadores ───────────────────────────────────────────
    # Permite selecionar múltiplos fatores que contribuíram para o incidente
    st.markdown('<div class="secao-titulo">🔍 Fatores Causadores</div>', unsafe_allow_html=True)
    fatores = st.multiselect(
        label("Fatores_Causadores", "Fatores que contribuíram para o incidente (selecione todos os itens aplicáveis)"),
        get_opcoes(df_config, "Fator Causador")
    )

    acoes_imediatas = st.text_area(
        label("Acoes_Imediatas", "Ações imediatas realizadas (o que foi feito logo após o incidente?)"),
        height=80,
        placeholder="Ex: Comunicado ao médico, feita gestão da lesão…"
    )

    # ── BLOCO 6: Identificação Opcional do Relator ────────────────────────────
    # Dados do profissional que está notificando — totalmente opcional
    st.markdown('<div class="secao-titulo">👤 Sua Identificação</div>', unsafe_allow_html=True)
    st.caption("Sua identidade nunca será vinculada ao relato de forma pública. É opcional e serve apenas para contato em caso de dúvida pelo Núcleo.")
    c9, c10 = st.columns(2)
    with c9:
        relator = st.text_input(label("Relator", "Seu Nome"), placeholder="Opcional")
    with c10:
        funcao  = st.text_input(label("Funcao_Relator", "Sua Função / Cargo"), placeholder="Ex: Técnico de Enfermagem")

    st.markdown("---")
    enviar = st.form_submit_button("📤 Enviar Notificação ao Núcleo de Segurança", use_container_width=True)

    # ── Lógica de envio ───────────────────────────────────────────────────────
    if enviar:
        # Lê quais campos estão marcados como obrigatórios no banco
        missing = []
        try:
            reqs = {row['Campo']: bool(row['Obrigatorio']) for _, row in fflags.iterrows()}
        except Exception:
            reqs = {}

        # Verifica cada campo obrigatório — adiciona ao lista de faltantes se vazio
        for campo, label_txt, vazio in [
            ('Leito',              'Leito',              lambda: not cama.strip()),
            ('Nome_Paciente',      'Nome do Paciente',   lambda: not nome_paciente.strip()),
            ('Data_Relato',        'Data do Relato',     lambda: not data_relato),
            ('Hora_Relato',        'Hora do Relato',     lambda: not hora_relato),
            ('Data_Nascimento',    'Data de Nascimento', lambda: not data_nasc),
            ('Descricao',          'Descrição',          lambda: not descricao.strip()),
            ('Fatores_Causadores', 'Fatores Causadores', lambda: not fatores),
            ('Acoes_Imediatas',    'Ações Imediatas',    lambda: not acoes_imediatas.strip()),
            ('Relator',            'Relator',            lambda: not relator.strip()),
            ('Funcao_Relator',     'Função / Cargo',     lambda: not funcao.strip()),
        ]:
            if reqs.get(campo, False) and vazio():
                missing.append(label_txt)

        if missing:
            st.warning(f"⚠️ Preencha os campos obrigatórios: {', '.join(missing)}")
        elif not reqs.get('Descricao', False) and not descricao.strip():
            # Descrição sempre exigida mesmo sem flag — é o campo central do relato
            st.warning("⚠️ Por favor, descreva o incidente antes de enviar.")
        else:
            # Monta o dicionário com todos os campos para inserção no banco
            # Campos de data usam str(x) if x else None para evitar inserir "None" como string
            novo = {
                "Data_Registro":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Data_Incidente":        str(data_incidente),
                "Turno":                 turno,
                "Setor":                 setor,
                "Leito":                 cama,
                "Tipo_Geral":            tipo_geral,
                "Categoria_Incidente":   categoria,
                "Subcategoria":          subcategoria,
                "Medicamento_Envolvido": medicamento,
                "Gravidade":             gravidade,
                "Data_Relato":           str(data_relato) if data_relato else None,
                "Hora_Relato":           str(hora_relato) if hora_relato else None,
                "Nome_Paciente":         nome_paciente,
                "Data_Nascimento":       str(data_nasc) if data_nasc else None,
                "Data_Internacao":       str(data_internacao) if data_internacao else None,
                "Raca_Cor":              raca_cor,
                "Fatores_Causadores":    ", ".join(fatores),
                "Descricao":             descricao,
                "Acoes_Imediatas":       acoes_imediatas,
                "Relator":               relator,
                "Funcao_Relator":        funcao,
                "Status":                "Novo"
            }
            db.save_incidente(novo)
            st.success("✅ Notificação enviada com sucesso! Obrigado por contribuir com a segurança do nosso hospital.")
            st.balloons()

# ─── Cálculo de idade em tempo real (JavaScript) ─────────────────────────────
# Injeta um script via iframe same-origin que faz polling a cada 300ms no DOM.
# Detecta mudanças no campo "Data de Nascimento", calcula a idade em JS e
# atualiza o campo "Idade" diretamente no DOM — sem rerun do Python.
# Necessário porque widgets dentro de st.form não disparam reruns individualmente.
components.html("""
<script>
(function(){
  // Calcula a idade em anos a partir de uma data no formato DD/MM/YYYY
  function calcAge(s){
    var p=s.split('/');
    if(p.length!==3)return null;
    var d=+p[0],m=+p[1],y=+p[2];
    if(!d||!m||!y||y<1900||y>2100)return null;
    var t=new Date(),a=t.getFullYear()-y;
    if(t.getMonth()+1<m||(t.getMonth()+1===m&&t.getDate()<d))a--;
    return(a>=0&&a<=130)?a:null;
  }
  var prevVal='',lastAge='—';
  // Polling: verifica a cada 300ms se o valor do campo mudou
  setInterval(function(){
    try{
      var doc=window.parent.document;
      var nascEl=null,idadeEl=null;
      // Localiza o input de data pelo texto do label ("Nascimento")
      doc.querySelectorAll('[data-testid="stDateInput"]').forEach(function(el){
        var l=el.querySelector('label');
        if(l&&l.textContent.indexOf('Nascimento')>=0)nascEl=el.querySelector('input');
      });
      // Localiza o input de idade pelo texto exato do label
      doc.querySelectorAll('[data-testid="stTextInput"]').forEach(function(el){
        var l=el.querySelector('label');
        if(l&&l.textContent.trim()==='Idade')idadeEl=el.querySelector('input');
      });
      if(!nascEl||!idadeEl)return;
      // Só recalcula se o valor mudou desde o último poll
      if(nascEl.value!==prevVal){
        prevVal=nascEl.value;
        var age=calcAge(prevVal);
        lastAge=age!==null?age+' anos':'—';
      }
      // Reaplica o valor calculado (React pode sobrescrever após re-render)
      if(lastAge!=='—')idadeEl.value=lastAge;
    }catch(e){}
  },300);
})();
</script>
""", height=0, scrolling=False)
