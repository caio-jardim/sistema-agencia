import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador de Hypes - Gemini", page_icon="🔥", layout="wide")

st.title("🔥 Gerador de Pautas Virais: Estilo Primo Rico")
st.markdown("Identifica os hypes do momento e cria conexões lógicas com seu nicho usando IA.")
st.markdown("---")

# --- LOGIN ---
def check_password():
    if "password_correct" in st.session_state and st.session_state["password_correct"]:
        return True
    
    def password_entered():
        if st.session_state["password"] == st.secrets["general"]["team_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    st.text_input("Senha:", type="password", on_change=password_entered, key="password")
    return False

if not check_password():
    st.stop()

# --- CONFIGURAÇÃO GEMINI ---
try:
    genai.configure(api_key=st.secrets["gemini"]["api_marcio"])
except Exception as e:
    st.error("Erro ao configurar API do Gemini. Verifique o secrets.toml")
    st.stop()

# --- INPUTS ---
with st.sidebar:
    st.header("🎯 Configuração do Radar")
    
    nicho = st.text_input("Seu Nicho", "Holding Familiar")
    
    janela_tempo = st.selectbox(
        "Janela de Tempo", 
        ["Hoje (Últimas 24h)", "Última Semana", "Último Mês"],
        index=1
    )

    # --- NOVO CAMPO SOLICITADO ---
    st.markdown("---")
    st.header("🕵️ Persona & Restrições")
    observacoes = st.text_area(
        "Observações Específicas", 
        placeholder="Ex: Advogado para público 40+, patrimônio alto. NÃO falar de sucessão, focar em proteção em vida.",
        height=100
    )
    
    st.info("💡 A IA irá cruzar fatos atuais com o nicho, respeitando suas observações.")

# --- FUNÇÕES ---

def limpar_json(texto):
    """Remove formatações de markdown que a IA às vezes coloca"""
    texto = texto.replace("```json", "").replace("```", "")
    return texto

def gerar_lista_hypes(nicho, janela, obs):
    # Usando o modelo flash para velocidade na geração da lista
    model = genai.GenerativeModel('gemini-2.0-flash') 
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    # Role
    Você é um estrategista de conteúdo Sênior, especializado em Marketing de Influência e "Newsjacking" (técnica de aproveitar notícias quentes para promover marcas). Seu estilo de escrita é inspirado em influenciadores de alta performance como "O Primo Rico" ou "Pablo Marçal": direto, levemente polêmico, focado em oportunidade/medo, e com alta autoridade.

    # Contexto
    - Data Atual: {data_hoje}
    - Janela de Análise: {janela}
    - Nicho do Cliente: {nicho}
    - OBSERVAÇÕES E RESTRIÇÕES DO CLIENTE: "{obs}"
    (ATENÇÃO: Respeite rigorosamente as observações acima. Se pedir para evitar um tema, evite).

    # Tarefa
    Gere 20 ideias de roteiros de vídeos curtos (Reels/TikTok) baseados nos assuntos mais quentes ("Hypes") do momento exato da data atual.

    # Regras de Criação (O Método "Primo Rico")
    1. **Diversidade:** Não fale apenas de economia. Misture:
       - 30% Economia/Dinheiro (Impostos, Bancos, Investimentos).
       - 30% Pop Culture/Fofoca (BBB, Divórcios de famosos, Memes do Twitter/X, Futebol, Filmes).
       - 20% Política/Leis (Novas regras, falas de presidentes, geopolítica).
       - 20% Cotidiano/Medo (Crimes, Doenças, Clima, Preços).
    2. **A Ponte (O Gancho):** O segredo é a conexão. Você deve pegar um assunto que NÃO tem nada a ver com o nicho e criar uma conexão lógica e surpreendente.
       - Exemplo errado: "O dólar subiu, contrate meu estúdio." (Chato).
       - Exemplo certo: "O dólar subiu e seu equipamento ficou 30% mais caro de repor. Se seu estúdio pegar fogo hoje, o seguro cobre o preço antigo ou o novo? Vamos falar de atualização patrimonial."
    3. **Tom de Voz:** Urgência, Oportunidade ou Indignação. Use gatilhos mentais.

    # Formato de Saída (JSON ESTRITO)
    Para que o sistema leia, retorne APENAS um Array JSON válido. Não use Markdown de código (```json).
    Siga estritamente esta estrutura de chaves:
    [
        {{
            "titulo": "Nome do Tema Curto e Chamativo",
            "hype": "Explique em 2 linhas por que isso está sendo falado hoje. Qual é a polêmica ou a dor?",
            "gancho": "Escreva o roteiro falado (speech) que o especialista deve dizer. Comece comentando a notícia e termine vendendo a necessidade do serviço/produto do nicho. Seja persuasivo."
        }},
        ...
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        texto_limpo = limpar_json(response.text)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro ao gerar lista: {e}")
        return []

def expandir_roteiro_final(item, nicho, obs):
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Aja como um Copywriter Sênior (Estilo Primo Rico / Pablo Marçal).
    
    # DADOS
    Nicho: {nicho}
    Observações: {obs}
    Tema Escolhido: {item['titulo']}
    Hype Base: {item['hype']}
    Gancho Inicial: {item['gancho']}

    # TAREFA
    Escreva o roteiro completo para Reels (aprox 60 segundos).
    
    # ESTRUTURA
    1. GANCHO VISUAL/VERBAL (Use o gancho fornecido, mas melhore se puder).
    2. DESENVOLVIMENTO (Retenção): Explique a lógica, gere medo ou oportunidade.
    3. CTA (Chamada para Ação): Venda o serviço de forma elegante.
    
    Formato: Markdown bonito.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- INTERFACE PRINCIPAL ---

col1, col2 = st.columns([2, 1])
with col1:
    st.write(f"Gerando pautas para: **{nicho}**")
with col2:
    btn_gerar = st.button("🚀 Gerar 20 Pautas", type="primary", use_container_width=True)

# Lógica de Estado (Session State) para manter os dados na tela
if btn_gerar:
    if not nicho:
        st.warning("Preencha o nicho.")
    else:
        with st.spinner("🧠 Analisando hypes e cruzando dados..."):
            pautas = gerar_lista_hypes(nicho, janela_tempo, observacoes)
            if pautas:
                st.session_state['pautas_geradas'] = pautas
                st.session_state['roteiro_expandido'] = None # Limpa roteiro anterior
            else:
                st.error("Falha ao gerar JSON. Tente novamente.")

# --- EXIBIÇÃO EM BLOCOS (CARDS) ---
if 'pautas_geradas' in st.session_state:
    st.markdown("---")
    st.subheader(f"📋 20 Ideias Encontradas para: {nicho}")
    
    pautas = st.session_state['pautas_geradas']
    
    # Loop para criar os cartões
    for i, pauta in enumerate(pautas):
        with st.container(border=True):
            col_a, col_b = st.columns([4, 1])
            
            with col_a:
                st.markdown(f"### {i+1}. {pauta['titulo']}")
                st.caption(f"🔥 **Hype:** {pauta['hype']}")
                st.markdown(f"🗣️ **Gancho Sugerido:** *{pauta['gancho']}*")
            
            with col_b:
                st.write("") # Espaçamento
                if st.button("✨ Escrever Roteiro", key=f"btn_rot_{i}"):
                    st.session_state['pauta_ativa'] = pauta
                    # Força rerun para mostrar o roteiro embaixo imediatamente
                    st.rerun()

# --- ÁREA DE ROTEIRO FINAL ---
if 'pauta_ativa' in st.session_state:
    st.markdown("---")
    st.subheader(f"🎬 Roteiro Final: {st.session_state['pauta_ativa']['titulo']}")
    
    with st.spinner("Escrevendo roteiro completo..."):
        # Gera o roteiro apenas se mudou a pauta ou ainda não gerou
        roteiro = expandir_roteiro_final(
            st.session_state['pauta_ativa'], 
            nicho, 
            observacoes
        )
        
        st.success("Roteiro criado!")
        with st.container(border=True):
            st.markdown(roteiro)
            
    # Botão para limpar/fechar
    if st.button("Fechar Roteiro"):
        del st.session_state['pauta_ativa']
        st.rerun()

# --- RODAPÉ ---
st.markdown("---")
st.caption("Powered by Google Gemini 2.0 | Content AI")