import streamlit as st
import google.generativeai as genai
from datetime import datetime
import time

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
    
    st.info("💡 A IA irá cruzar fatos atuais de economia, cultura pop e política com o seu nicho.")

# --- FUNÇÃO GERADORA ---
def gerar_pautas_gemini(nicho, janela):
    # Modelo recomendado: gemini-1.5-flash (rápido e atualizado) ou gemini-1.5-pro
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    # Role
    Você é um estrategista de conteúdo Sênior, especializado em Marketing de Influência e "Newsjacking". Seu estilo de escrita é inspirado em influenciadores de alta performance como "O Primo Rico" ou "Pablo Marçal": direto, levemente polêmico, focado em oportunidade/medo, e com alta autoridade.

    # Contexto
    - Data Atual de referência: {data_hoje}
    - Janela de Análise: {janela}
    - Nicho do Cliente: {nicho}
    - Público-Alvo: Pessoas que precisam desse serviço, mas talvez não saibam que precisam agora.

    # Tarefa
    Gere 20 ideias de roteiros de vídeos curtos (Reels/TikTok) baseados nos assuntos mais quentes ("Hypes") do momento.

    # Regras de Criação (O Método "Primo Rico")
    1. **Diversidade:** Não fale apenas de economia. Misture:
       - 30% Economia/Dinheiro (Impostos, Bancos, Investimentos).
       - 30% Pop Culture/Fofoca (BBB, Divórcios de famosos, Memes do Twitter/X, Futebol).
       - 20% Política/Leis (Novas regras, falas de presidentes, geopolítica).
       - 20% Cotidiano/Medo (Crimes, Doenças, Clima, Preços).
    2. **A Ponte (O Gancho):** O segredo é a conexão. Você deve pegar um assunto que NÃO tem nada a ver com o nicho e criar uma conexão lógica e surpreendente.
       - Exemplo errado: "O dólar subiu, contrate meu estúdio." (Chato).
       - Exemplo certo: "O dólar subiu e seu equipamento ficou 30% mais caro de repor. Se seu estúdio pegar fogo hoje, o seguro cobre o preço antigo ou o novo? Vamos falar de atualização patrimonial."
    3. **Tom de Voz:** Urgência, Oportunidade ou Indignação.

    # Formato de Saída (Estrito)
    Para cada um dos 20 temas, use EXATAMENTE esta estrutura (use Markdown):

    ### 1. [Nome do Tema Curto e Chamativo]
    * **Tema:** [Resumo de 1 linha sobre o que é o assunto]
    * **O Hype:** [Explique em 2 linhas por que isso está sendo falado hoje. Qual é a polêmica ou a dor?]
    * **Gancho para o nicho:** [Escreva o roteiro falado (speech) que o especialista deve dizer. Comece comentando a notícia e termine vendendo a necessidade do serviço/produto do {nicho}. Seja persuasivo.]

    ---
    (Repita para os 20 itens)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro na geração: {e}"

# --- INTERFACE PRINCIPAL ---

col1, col2 = st.columns([2, 1])
with col1:
    st.write(f"Gerando pautas para: **{nicho}**")
with col2:
    btn_gerar = st.button("🚀 Gerar 20 Pautas Virais", type="primary", use_container_width=True)

if btn_gerar:
    if not nicho:
        st.warning("Por favor, preencha o nicho.")
    else:
        with st.spinner("🧠 O Gemini está analisando os hypes do momento..."):
            # Chama a função
            resultado = gerar_pautas_gemini(nicho, janela_tempo)
            
            st.success("Pautas geradas com sucesso!")
            st.markdown("---")
            st.markdown(resultado)

# --- RODAPÉ ---
st.markdown("---")
st.caption("Powered by Google Gemini Pro | Desenvolvido pela Equipe de Conteúdo")