import streamlit as st
import json
import time
from groq import Groq
from duckduckgo_search import DDGS

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador Primo Rico", page_icon="🎩")

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
    # Focamos em termos que geram o tipo de notícia que o Primo Rico comenta
    temas_interesse = st.multiselect(
        "O que você quer monitorar hoje?",
        ["Impostos/Tributação", "Inflação/Dólar", "Política Econômica", "Mudanças na Lei", "Escândalos/Corrupção"],
        default=["Impostos/Tributação", "Política Econômica"]
    )
    
    tempo_busca = st.selectbox("Janela de Tempo", ["Últimas 24h", "Última Semana"], index=0)

# --- FUNÇÕES ---

def buscar_nos_portais_de_elite(temas, tempo, log):
    """
    Em vez de buscar na web inteira, busca especificamente dentro dos sites
    que formam a opinião do mercado financeiro/político.
    """
    mapa_tempo = {"Últimas 24h": "d", "Última Semana": "w"}
    timelimit = mapa_tempo[tempo]
    
    # Lista dos sites que o Primo Rico/Bruno Perini leem
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
                log.write(f"🔎 Lendo {portal} sobre '{tema}'...")
                
                try:
                    # Busca restrita
                    results = ddgs.news(keywords=query, region="br-pt", safesearch="off", timelimit=timelimit, max_results=1)
                    for n in results:
                        if n['url'] not in urls_vistas:
                            n['tema_base'] = tema
                            noticias_coletadas.append(n)
                            urls_vistas.add(n['url'])
                except:
                    continue
                time.sleep(0.2) # Delay para não ser bloqueado
                
    return noticias_coletadas

def roteirizar_estilo_primo(noticia, nicho, publico):
    client = Groq(api_key=st.secrets["groq_api_key"])
    
    prompt = f"""
    Você é um Copywriter Sênior especialista no estilo "Primo Rico" (Thiago Nigro) ou "Bruno Perini".
    
    O QUE É ESSE ESTILO:
    1. Analítico e Sóbero: Não é dancinha. É análise de cenário.
    2. "Skin in the Game": Mostra que isso afeta o bolso de todos.
    3. Estrutura: Fato Chocante -> Contexto Econômico -> O Perigo Invisível -> A Solução (Meu Produto).
    
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
    
    1. O GRÁFICO/MANCHETE (0-5s): 
       Comece citando a notícia. Ex: "Você viu o que saiu no Valor hoje?", "Isso aqui [aponta pra cima] vai destruir a classe média."
    
    2. A TRADUÇÃO (5-20s): 
       Traduza o "economês" para a realidade. "O que isso significa na prática? Significa que o governo vai morder mais 15% do que é seu."
    
    3. O MEDO RACIONAL (20-40s): 
       Por que o público alvo deve se preocupar AGORA? "Se você tem imóveis no seu CPF, essa lei pode levar metade da sua herança."
    
    4. A SOLUÇÃO ELITIZADA (40-60s): 
       Como os ricos resolvem isso. "Os grandes empresários não pagam isso porque usam {nicho}. E você também pode."
       CTA: "Me segue para blindar seu patrimônio."
    
    Gere o roteiro em Markdown.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6 # Mais preciso, menos alucinação
    )
    
    return completion.choices[0].message.content

# --- INTERFACE ---

if st.button("🎩 Buscar Pautas de Elite", type="primary"):
    
    status = st.status("🕵️ Monitorando portais financeiros...", expanded=True)
    
    # 1. Busca Direcionada
    noticias = buscar_nos_portais_de_elite(temas_interesse, tempo_busca, status)
    
    if not noticias:
        status.update(label="❌ Nenhuma notícia relevante encontrada.", state="error")
        st.error("Tente ampliar a janela de tempo ou selecionar mais temas.")
        st.stop()
        
    status.write(f"📦 {len(noticias)} notícias de alta relevância encontradas.")
    status.update(label="✅ Monitoramento Concluído!", state="complete", expanded=False)
    
    # 2. Seleção e Geração
    st.subheader("📰 Escolha uma notícia para gerar o roteiro:")
    
    for i, news in enumerate(noticias):
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{news['title']}**")
                st.caption(f"Fonte: {news['source']} | Tema: {news['tema_base']}")
                st.write(news['body'])
            with col_b:
                # Botão único para cada notícia
                if st.button(f"✨ Gerar Roteiro", key=f"btn_{i}"):
                    with st.spinner("Escrevendo roteiro estilo Primo Rico..."):
                        roteiro = roteirizar_estilo_primo(news, nicho, publico)
                        
                        # Mostra o resultado em um modal ou abaixo
                        st.markdown("---")
                        st.success("📹 Roteiro Gerado:")
                        st.markdown(roteiro)