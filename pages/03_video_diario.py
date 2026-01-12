import streamlit as st
import json
import time
from groq import Groq
from duckduckgo_search import DDGS

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador Viral (Bridge Technique)", page_icon="🌉")

st.title("🌉 Gerador Viral: Técnica da Ponte")
st.markdown("Conecte assuntos do momento (Trends) ao seu produto, mesmo que não tenham nada a ver.")
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
    st.header("⚙️ Configuração")
    
    nicho_atuacao = st.text_input("Seu Nicho", "Holding Familiar")
    
    publico_alvo = st.text_area(
        "Público Alvo", 
        "Empresários com patrimônio que temem instabilidade política e impostos."
    )
    
    # Adicionamos busca de Trends Gerais
    st.markdown("---")
    st.markdown("**🔍 Estratégia de Busca**")
    buscar_trends = st.checkbox("Buscar Notícias Gerais (Política/Pop/Mundo)?", value=True)
    buscar_nicho = st.checkbox("Buscar Notícias do Nicho?", value=True)
    
    dias_atras = st.selectbox("Janela de Tempo:", ["Últimas 24h", "Últimos 3 dias"], index=1)
    mapa_dias = {"Últimas 24h": "d", "Últimos 3 dias": "d3"}
    timelimit = mapa_dias[dias_atras]

# --- FUNÇÕES ---

def buscar_noticias(termos, tempo, log_container):
    """Varre o DuckDuckGo"""
    todas_noticias = []
    links_vistos = set()
    
    with DDGS() as ddgs:
        for termo in termos:
            log_container.write(f"🔎 Pesquisando: *'{termo}'*...")
            try:
                # Max results 2 por termo para não poluir demais
                results = ddgs.news(
                    keywords=termo, 
                    region="br-pt", 
                    safesearch="off", 
                    timelimit=tempo, 
                    max_results=2 
                )
                
                for news in results:
                    if news['url'] not in links_vistos:
                        # Adiciona tag para saber a origem
                        news['termo_origem'] = termo
                        todas_noticias.append(news)
                        links_vistos.add(news['url'])
                        
            except Exception as e:
                print(f"Erro buscando {termo}: {e}")
            time.sleep(0.3)
            
    return todas_noticias

def selecionar_e_roteirizar_bridge(noticias, nicho, publico):
    """
    A MÁGICA: Usa a IA para fazer a 'Ponte' entre assunto aleatório e o nicho.
    """
    client = Groq(api_key=st.secrets["groq_api_key"])
    
    # Prepara o feed
    feed_noticias = ""
    for i, n in enumerate(noticias):
        feed_noticias += f"[{i+1}] MANCHETE: {n['title']} (Busca: {n['termo_origem']})\nRESUMO: {n['body']}\n\n"

    prompt = f"""
    Você é um gênio do Marketing Viral e Pensamento Lateral.
    
    MEU NICHO: {nicho}
    MEU PÚBLICO: {publico}
    
    NOTÍCIAS RECENTES ENCONTRADAS:
    {feed_noticias}
    
    SUA MISSÃO:
    1. Escolha a notícia mais "Mainstream" (famosa/polêmica) da lista, mesmo que NÃO tenha nada a ver com o nicho. (Ex: Prisão de político, BBB, Famosos, Guerra).
    2. Crie uma "PONTE LÓGICA" (Bridge) entre essa notícia e o meu produto.
    
    EXEMPLOS DE PONTE (Raciocínio):
    - Notícia: "Maduro Preso/Caiu" -> Ponte: "Instabilidade política derruba governos. E se derrubarem seu patrimônio? Holding protege."
    - Notícia: "Larissa Manoela briga com pais" -> Ponte: "Briga familiar destrói fortunas. Holding evita briga."
    - Notícia: "Imposto aumenta na China" -> Ponte: "O governo sempre quer mais. Proteja-se aqui."
    
    AGORA ESCREVA O ROTEIRO (Reels 60s):
    - GANCHO (0-3s): Use a notícia bomba. "Você viu que o [Fulano] foi preso/caiu?"
    - A PONTE (3-15s): Faça a transição. "O que isso tem a ver com o seu dinheiro? TUDO."
    - A LIÇÃO (15-45s): Explique o risco e a solução ({nicho}).
    - CTA (45-60s): Chamada para ação.
    
    Retorne em Markdown. Explique qual foi a "Lógica da Ponte" usada no início.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8 # Criatividade alta para fazer conexões inusitadas
    )
    
    return completion.choices[0].message.content

# --- INTERFACE PRINCIPAL ---

if st.button("🌉 Gerar Roteiro com Ponte Viral", type="primary"):
    
    status_box = st.status("🧠 Iniciando varredura...", expanded=True)
    
    termos_busca = []
    
    # 1. Define termos de busca
    if buscar_nicho:
        termos_busca.extend([f"Polêmica {nicho_atuacao}", f"Lei {nicho_atuacao}", "Impostos Brasil"])
        
    if buscar_trends:
        # Termos genéricos para pegar o hype do dia
        termos_busca.extend([
            "Notícias mais lidas hoje Brasil",
            "Escândalo política hoje",
            "Polêmica famosos Brasil",
            "Prisão urgente hoje",
            "O que está acontecendo no Brasil agora"
        ])
    
    status_box.write(f"🕵️ Buscando por: {', '.join(termos_busca)}")
    
    # 2. Busca Real
    noticias = buscar_noticias(termos_busca, timelimit, status_box)
    
    if not noticias:
        status_box.update(label="❌ Nada encontrado.", state="error")
        st.stop()
        
    status_box.write(f"📦 {len(noticias)} manchetes encontradas. Criando conexão lógica...")
    
    # 3. Geração
    roteiro = selecionar_e_roteirizar_bridge(noticias, nicho_atuacao, publico_alvo)
    
    status_box.update(label="✅ Roteiro Viral Criado!", state="complete", expanded=False)
    
    # Exibição
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("## 📹 Roteiro Viral (The Bridge)")
        st.markdown(roteiro)
    
    with col2:
        st.info("📰 Notícias Usadas para o Contexto")
        for n in noticias:
            with st.expander(f"{n['title']}"):
                st.caption(f"Origem: {n['termo_origem']}")
                st.write(n['body'])
                st.markdown(f"[Link]({n['url']})")