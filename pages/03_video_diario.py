import streamlit as st
import json
import time
from groq import Groq
from duckduckgo_search import DDGS

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Caçador de Notícias Virais", page_icon="🦈")

st.title("🦈 Caçador de Notícias Virais")
st.markdown("Dê o seu nicho e a IA varre a internet buscando polêmicas úteis para você.")
st.markdown("---")

# --- SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["general"]["team_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" in st.session_state:
        if st.session_state["password_correct"]:
            return True

    st.markdown("### 🔒 Acesso Restrito")
    st.text_input("Senha:", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state:
        if not st.session_state["password_correct"]:
            st.error("Senha incorreta.")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("⚙️ Configuração do Caçador")
    
    nicho_atuacao = st.text_input("Qual seu Nicho/Produto?", "Holding Familiar e Proteção Patrimonial")
    
    publico_alvo = st.text_area(
        "Quem é o público alvo?", 
        "Empresários e famílias ricas que têm medo de perder dinheiro para o governo ou briga de filhos."
    )
    
    tom_voz = st.selectbox("Tom do Vídeo", ["Polêmico/Alerta", "Educativo/Técnico", "Indignado"], index=0)
    
    dias_atras = st.selectbox("Janela de Busca:", ["Últimas 24h", "Últimos 3 dias", "Última Semana"], index=1)
    
    mapa_dias = {"Últimas 24h": "d", "Últimos 3 dias": "d3", "Última Semana": "w"}
    timelimit = mapa_dias[dias_atras]

# --- FUNÇÕES INTELIGENTES ---

def gerar_termos_de_busca(nicho, publico):
    """
    Usa a IA para 'adivinhar' o que devemos pesquisar no Google News
    para achar ouro para esse nicho.
    """
    client = Groq(api_key=st.secrets["groq_api_key"])
    
    prompt = f"""
    Aja como um estrategista de conteúdo viral.
    Meu Nicho: "{nicho}"
    Meu Público: "{publico}"
    
    Sua missão: Liste 3 termos de busca curtos e específicos para encontrar notícias RECENTES que afetam esse público e geram medo, ganância ou curiosidade.
    Pense em: Leis novas, escândalos, mudanças econômicas, polêmicas atuais.
    
    Exemplo para Holding: "Reforma Tributária herança", "Aumento ITCMD", "Briga herança famosos".
    
    Retorne APENAS um JSON puro (sem markdown) no formato:
    {{ "termos": ["termo 1", "termo 2", "termo 3"] }}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content).get("termos", [])
    except Exception as e:
        st.error(f"Erro ao gerar termos: {e}")
        return [nicho] # Fallback

def buscar_noticias_reais(lista_termos, tempo, log_container):
    """Varre o DuckDuckGo com os termos sugeridos pela IA"""
    todas_noticias = []
    links_vistos = set()
    
    with DDGS() as ddgs:
        for termo in lista_termos:
            log_container.write(f"🔎 Pesquisando sobre: *'{termo}'*...")
            try:
                results = ddgs.news(
                    keywords=termo, 
                    region="br-pt", 
                    safesearch="off", 
                    timelimit=tempo, 
                    max_results=3 # Pega top 3 de cada termo
                )
                
                for news in results:
                    # Evita duplicatas
                    if news['url'] not in links_vistos:
                        todas_noticias.append(news)
                        links_vistos.add(news['url'])
                        
            except Exception as e:
                print(f"Erro buscando {termo}: {e}")
            
            time.sleep(0.5) # Respeita o servidor
            
    return todas_noticias

def selecionar_e_roteirizar(noticias, nicho, publico, tom):
    """
    A IA lê as notícias encontradas e escolhe a melhor.
    """
    client = Groq(api_key=st.secrets["groq_api_key"])
    
    # Prepara o texto para a IA ler
    feed_noticias = ""
    for i, n in enumerate(noticias):
        feed_noticias += f"[{i+1}] MANCHETE: {n['title']} | FONTE: {n['source']} | DATA: {n['date']}\nRESUMO: {n['body']}\nLINK: {n['url']}\n\n"

    prompt = f"""
    Você é um roteirista de vídeos virais sensacionalistas (mas verdadeiros).
    
    CONTEXTO:
    Nicho: {nicho}
    Público: {publico}
    Tom de Voz: {tom}
    
    Abaixo estão notícias reais que acabamos de coletar na internet:
    -----------------------------------
    {feed_noticias}
    -----------------------------------
    
    SUA TAREFA:
    1. Escolha a notícia mais "bomba", urgente ou polêmica dessa lista. Aquela que fará o cliente parar de rolar o feed.
    2. Ignore notícias irrelevantes ou muito antigas se houver opções melhores.
    3. Escreva um Roteiro de Vídeo (Reels/TikTok).
    
    ESTRUTURA OBRIGATÓRIA:
    - NOTÍCIA ESCOLHIDA: (Cite qual título você escolheu)
    - HEADLINE (Texto na tela): Algo curto e chocante.
    - GANCHO (0-5s): Comece com a notícia bomba. Use gatilhos de medo ou urgência.
    - CORPO: Explique a notícia rapidamente e conecte com o problema do cliente.
    - VIRADA (Venda): Explique como o {nicho} salva ele disso.
    - CTA: Mande comentar ou clicar no link.
    
    Use formatação Markdown bonita.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return completion.choices[0].message.content

# --- INTERFACE PRINCIPAL ---

if st.button("🦈 Iniciar Caçada Viral", type="primary"):
    
    status_box = st.status("🧠 IA Iniciando estratégia...", expanded=True)
    
    # 1. Brainstorming
    status_box.write("🤔 Definindo o que pesquisar...")
    termos = gerar_termos_de_busca(nicho_atuacao, publico_alvo)
    
    if not termos:
        status_box.update(label="❌ Erro ao gerar termos.", state="error")
        st.stop()
        
    status_box.write(f"🎯 Termos definidos: {', '.join(termos)}")
    
    # 2. Busca Real
    status_box.write("🌐 Varrendo portais de notícias...")
    noticias_encontradas = buscar_noticias_reais(termos, timelimit, status_box)
    
    if not noticias_encontradas:
        status_box.update(label="❌ Nada encontrado.", state="error")
        st.error("Nenhuma notícia relevante encontrada nesses termos. Tente aumentar a janela de dias.")
        st.stop()
        
    status_box.write(f"📦 {len(noticias_encontradas)} notícias coletadas. Analisando a melhor...")
    
    # 3. Geração do Roteiro
    roteiro_final = selecionar_e_roteirizar(noticias_encontradas, nicho_atuacao, publico_alvo, tom_voz)
    
    status_box.update(label="✅ Vídeo Viral Gerado!", state="complete", expanded=False)
    
    # Exibição
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("## 📹 Seu Roteiro")
        st.markdown(roteiro_final)
    
    with col2:
        st.info("🔍 Notícias Analisadas pela IA")
        for n in noticias_encontradas:
            with st.expander(n['title']):
                st.caption(f"{n['source']} - {n['date']}")
                st.write(n['body'])
                st.markdown(f"[Ler completa]({n['url']})")