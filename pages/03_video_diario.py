import streamlit as st
import json
import time
from groq import Groq
from duckduckgo_search import DDGS

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador Vídeo Notícias", page_icon="🎩")

st.title("🎩 Gerador de Pauta: Estilo Primo Rico")
st.markdown("Monitora portais de elite (Valor, InfoMoney, CNN) e cria roteiros de autoridade.")
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

# --- INPUTS ---
with st.sidebar:
    st.header("🎯 Seu Posicionamento")
    nicho = st.text_input("Nicho", "Holding Familiar")
    publico = st.text_area("Público", "Empresários com patrimônio acima de 1MM")
    
    st.markdown("---")
    st.header("📡 Radar de Notícias")
    temas_interesse = st.multiselect(
        "O que você quer monitorar hoje?",
        ["Impostos/Tributação", "Inflação/Dólar", "Política Econômica", "Mudanças na Lei", "Escândalos/Corrupção"],
        default=["Impostos/Tributação", "Política Econômica"]
    )
    
    tempo_busca = st.selectbox("Janela de Tempo", ["Últimas 24h", "Última Semana"], index=0)

# --- FUNÇÕES ---

def buscar_nos_portais_de_elite(temas, tempo, log_placeholder):
    mapa_tempo = {"Últimas 24h": "d", "Última Semana": "w"}
    timelimit = mapa_tempo[tempo]
    
    portais_elite = [
        "site:infomoney.com.br",
        "site:valor.globo.com",
        "site:cnnbrasil.com.br/economia",
        "site:g1.globo.com/economia",
        "site:uol.com.br/economia"
    ]
    
    noticias_coletadas = []
    urls_vistas = set()
    
    with DDGS() as ddgs:
        for tema in temas:
            for portal in portais_elite:
                query = f"{tema} {portal}"
                # Atualiza o status visualmente
                log_placeholder.text(f"🔎 Lendo {portal} sobre '{tema}'...")
                
                try:
                    results = ddgs.news(keywords=query, region="br-pt", safesearch="off", timelimit=timelimit, max_results=1)
                    for n in results:
                        if n['url'] not in urls_vistas:
                            n['tema_base'] = tema
                            noticias_coletadas.append(n)
                            urls_vistas.add(n['url'])
                except:
                    continue
                time.sleep(0.2)
                
    return noticias_coletadas

def roteirizar_estilo_primo(noticia, nicho, publico):
    client = Groq(api_key=st.secrets["groq_api_key"])
    
    prompt = f"""
    Você é um Copywriter Sênior especialista no estilo "Primo Rico" (Thiago Nigro) ou "Bruno Perini".
    
    CONTEXTO DO CLIENTE:
    Nicho: {nicho}
    Público: {publico}
    
    A NOTÍCIA BOMBA:
    Título: {noticia['title']}
    Fonte: {noticia['source']}
    Resumo: {noticia['body']}
    
    SUA TAREFA:
    Escreva um roteiro de vídeo curto (Reels/Shorts) comentando essa notícia.
    
    ESTRUTURA DO ROTEIRO:
    1. O GRÁFICO/MANCHETE (0-5s): Ex: "Você viu o que saiu no Valor hoje?"
    2. A TRADUÇÃO (5-20s): O que isso significa pro bolso dele.
    3. O MEDO RACIONAL (20-40s): Por que se preocupar.
    4. A SOLUÇÃO ELITIZADA (40-60s): Como a {nicho} resolve.
    
    Gere o roteiro em Markdown.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )
    
    return completion.choices[0].message.content

# --- INTERFACE PRINCIPAL ---

# Botão de Busca
if st.button("🎩 Buscar Pautas de Elite", type="primary"):
    
    # Placeholder para logs em tempo real
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    # Busca
    noticias = buscar_nos_portais_de_elite(temas_interesse, tempo_busca, status_text)
    
    # Limpa status
    status_text.empty()
    progress_bar.empty()
    
    if not noticias:
        st.error("Nenhuma notícia encontrada. Tente ampliar o prazo.")
    else:
        # SALVA NO SESSION STATE (MEMÓRIA)
        st.session_state['noticias_primo'] = noticias
        st.success(f"📦 {len(noticias)} notícias encontradas!")

# --- EXIBIÇÃO PERSISTENTE ---
# Verifica se existem notícias na memória para mostrar
if 'noticias_primo' in st.session_state:
    
    st.markdown("---")
    st.subheader("📰 Escolha uma notícia para gerar o roteiro:")
    
    # Itera sobre as notícias salvas
    for i, news in enumerate(st.session_state['noticias_primo']):
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{news['title']}**")
                st.caption(f"Fonte: {news['source']} | Tema: {news['tema_base']}")
                st.write(news['body'])
            with col_b:
                # O botão agora funciona porque o loop está fora do "if button busca"
                if st.button(f"✨ Gerar Roteiro", key=f"btn_primo_{i}"):
                    
                    # Salva qual notícia está sendo roteirizada para mostrar abaixo
                    st.session_state['roteiro_ativo'] = news

    # --- MOSTRAR ROTEIRO GERADO ---
    if 'roteiro_ativo' in st.session_state:
        st.markdown("---")
        news_ativa = st.session_state['roteiro_ativo']
        
        st.info(f"📝 Gerando roteiro para: **{news_ativa['title']}**")
        
        with st.spinner("Escrevendo roteiro..."):
            roteiro_final = roteirizar_estilo_primo(news_ativa, nicho, publico)
            
            st.success("📹 Roteiro Gerado com Sucesso!")
            st.markdown(roteiro_final)