import streamlit as st
import os
import time
import json
import requests
import yt_dlp
from groq import Groq
from apify_client import ApifyClient
from moviepy.editor import VideoFileClip

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador de Carrosséis", page_icon="🎠", layout="wide")

st.title("🎠 Gerador de Carrosséis: Método Tempestade")
st.markdown("Transforme qualquer conteúdo (YouTube, Reels ou Post) em 3 estruturas validadas psicologicamente.")
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

# --- CONFIGURAÇÕES DE API ---
try:
    # Ajuste para ler do bloco [groq] conforme seu secrets.toml
    if "groq" in st.secrets and "api_key" in st.secrets["groq"]:
        client_groq = Groq(api_key=st.secrets["groq"]["api_key"])
    else:
        st.error("Chave Groq não encontrada em [groq] api_key.")
        st.stop()
        
    if "apify_token" in st.secrets:
        client_apify = ApifyClient(st.secrets["apify_token"])
    else:
        st.error("Token Apify não encontrado.")
        st.stop()

except Exception as e:
    st.error(f"Erro de configuração de chaves: {e}")
    st.stop()

# --- PROMPT DO AGENTE TEMPESTADE ---
SYSTEM_PROMPT_TEMPESTADE = """
VOCÊ É: Um Estrategista de Conteúdo Viral e Analista de Atenção (Focado 100% em Ideias e Conceitos).

SUA MISSÃO: Gerar estruturas de conteúdo validadas psicologicamente baseadas no CONTEÚDO BASE fornecido.
O QUE VOCÊ NÃO FAZ: Você NÃO escreve roteiros, NÃO escreve legendas, NÃO escreve copy final. Você entrega a ESTRUTURA.

TOM DE VOZ:
- Analítico, cirúrgico e "Sênior".
- Foco em: "Por que isso funciona?" (Psicologia do consumidor).
- Zero "encher linguiça". Vá direto à estrutura.

FORMATO DE RESPOSTA OBRIGATÓRIO (Siga estritamente):
1. "Título do Conceito"
   Estrutura: [Nome técnico da estrutura]
   Por que funciona: [Explicação estratégica de como isso muda a percepção ou ataca uma crença]

EXEMPLOS DE TREINAMENTO (FEW-SHOT):

Usuário: Ideias para Padaria Artesanal.
Você:
1. “O pão que você compra não é pão”
Estrutura: Confrontação de realidade + quebra de senso comum
Por que funciona: Ataca uma crença automática do público e reposiciona a padaria como referência técnica. A ideia não é ensinar receita, e sim mudar o critério de julgamento.

2. “Por que essa fornada nunca fica igual à outra”
Estrutura: Bastidores + dinâmica invisível do processo
Por que funciona: Revela que a imperfeição controlada é sinal de qualidade artesanal. Educa o público a valorizar variáveis como fermentação natural. Transforma "defeito" em prova de excelência.

3. “O erro que faz a maioria desistir do pão artesanal”
Estrutura: Combate ao inimigo + posicionamento claro
Por que funciona: Define um vilão (pressa/atalhos) e posiciona a marca como quem escolheu o caminho difícil. Filtra curiosos de compradores reais.
(Gere exatamente 3 opções distintas baseadas no tema do input).
"""

# --- FUNÇÕES AUXILIARES ---

def download_youtube_audio(url):
    """
    Baixa áudio do YouTube usando yt-dlp simulando um CLIENTE ANDROID.
    Isso ajuda a evitar o erro 403 em servidores de nuvem sem usar Proxy.
    """
    output_filename = "temp_yt_audio"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_filename,
        # O SEGREDO: Força o yt-dlp a agir como um App Android
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'noplaylist': True,
    }

    try:
        # Tenta modo Android
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        final_filename = f"{output_filename}.mp3"
        if os.path.exists(final_filename):
            return final_filename
        if os.path.exists(output_filename):
            return output_filename
            
        return None

    except Exception as e:
        st.warning(f"Método Android falhou ({e}). Tentando método Web Creator...")
        try:
            # Tenta modo Web Creator como fallback
            ydl_opts['extractor_args']['youtube']['player_client'] = ['web_creator']
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return f"{output_filename}.mp3"
        except Exception as e2:
            st.error(f"❌ Falha no download do YouTube: {e2}")
            return None

def get_instagram_data_apify(url):
    """
    Usa Apify para pegar dados do post (Reels ou Carrossel).
    CORREÇÃO: Removido 'searchType' que estava causando erro de validação.
    """
    # Configuração correta para Links Diretos (Direct URLs)
    run_input = {
        "directUrls": [url],
        "resultsType": "posts",
        # "searchType": "url",  <-- REMOVIDO (Isso causava o erro)
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"]
        }
    }
    
    # Ajuste de Proxy para contas Free (Se der erro 407, descomente a linha abaixo)
    # run_input["proxy"] = {"useApifyProxy": True, "apifyProxyGroups": []} 
    
    try:
        # Chama o Actor "instagram-scraper"
        run = client_apify.actor("apify/instagram-scraper").call(run_input=run_input)
        
        if not run: 
            return None
        
        # Pega os resultados do dataset
        dataset_items = client_apify.dataset(run["defaultDatasetId"]).list_items().items
        
        if dataset_items:
            return dataset_items[0]
            
        return None
    except Exception as e:
        st.error(f"Erro na Apify: {e}")
        return None

def download_file(url, filename):
    """Baixa arquivo de uma URL genérica (para vídeo do Instagram)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        st.error(f"Erro ao baixar arquivo: {e}")
        return False

def transcrever_audio_groq(filepath):
    """Transcreve usando Whisper V3 na Groq"""
    try:
        with open(filepath, "rb") as file:
            transcription = client_groq.audio.transcriptions.create(
                file=(filepath, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        return str(transcription)
    except Exception as e:
        st.error(f"Erro na Transcrição: {e}")
        return None

def agente_tempestade(conteudo_base):
    """Envia o conteúdo para o Llama 3 gerar as estruturas"""
    try:
        prompt_user = f"Analise este conteúdo e gere 3 estruturas de carrossel:\n\nCONTEÚDO BASE:\n{conteudo_base[:6000]}"
        
        completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPESTADE},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile", # Ajustado para modelo disponível
            temperature=0.5,
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"Erro na IA Tempestade: {e}")
        return None

# --- INTERFACE PRINCIPAL ---

tipo_conteudo = st.radio(
    "Qual a origem da ideia?",
    ["YouTube", "Reels (Instagram)", "Carrossel (Instagram)"],
    horizontal=True
)

url_input = st.text_input(f"Cole o link do {tipo_conteudo}:", placeholder="https://...")

if st.button("⚡ Gerar Tempestade de Ideias", type="primary"):
    if not url_input:
        st.warning("Por favor, insira um link.")
    else:
        texto_para_analise = ""
        status = st.status("Processando...", expanded=True)
        
        # --- FLUXO 1: YOUTUBE ---
        if tipo_conteudo == "YouTube":
            status.write("⬇️ Baixando áudio do YouTube...")
            audio_file = download_youtube_audio(url_input)
            
            if audio_file:
                status.write("👂 Transcrevendo áudio...")
                texto_para_analise = transcrever_audio_groq(audio_file)
                
                # Limpeza
                if os.path.exists(audio_file): os.remove(audio_file)

        # --- FLUXO 2: REELS ---
        elif tipo_conteudo == "Reels (Instagram)":
            status.write("🕵️ Acessando Instagram via Apify...")
            # AQUI ESTAVA O ERRO: Chamando a função agora definida
            post_data = get_instagram_data_apify(url_input)
            
            if post_data and (post_data.get('videoUrl') or post_data.get('video_url')):
                video_url = post_data.get('videoUrl') or post_data.get('video_url')
                
                status.write("⬇️ Baixando vídeo...")
                if download_file(video_url, "temp_reel.mp4"):
                    
                    status.write("🔊 Extraindo áudio...")
                    try:
                        video_clip = VideoFileClip("temp_reel.mp4")
                        video_clip.audio.write_audiofile("temp_reel.mp3", verbose=False, logger=None)
                        video_clip.close()
                        
                        status.write("👂 Transcrevendo...")
                        texto_para_analise = transcrever_audio_groq("temp_reel.mp3")
                        
                        # Cleanup
                        if os.path.exists("temp_reel.mp4"): os.remove("temp_reel.mp4")
                        if os.path.exists("temp_reel.mp3"): os.remove("temp_reel.mp3")
                        
                    except Exception as e:
                        st.error(f"Erro processando vídeo: {e}")
            else:
                st.error("Não foi possível encontrar o vídeo neste link ou erro na Apify.")

        # --- FLUXO 3: CARROSSEL ---
        elif tipo_conteudo == "Carrossel (Instagram)":
            status.write("🕵️ Acessando Carrossel via Apify...")
            post_data = get_instagram_data_apify(url_input)
            
            if post_data:
                # Estratégia: Pegar a legenda e textos alternativos (se houver)
                caption = post_data.get('caption') or post_data.get('description') or ""
                
                # Tenta pegar alt text das imagens filhas
                alt_texts = []
                children = post_data.get('childPosts') or post_data.get('children') or []
                for child in children:
                    if child.get('alt'):
                        alt_texts.append(child.get('alt'))
                
                texto_para_analise = f"LEGENDA DO POST:\n{caption}\n\nCONTEXTO VISUAL (Alt Text):\n{' '.join(alt_texts)}"
                
                status.write("✅ Texto extraído da legenda e metadados.")
            else:
                st.error("Não foi possível ler o carrossel.")

        # --- GERAÇÃO FINAL ---
        if texto_para_analise:
            status.write("🧠 Agente Tempestade trabalhando...")
            resultado = agente_tempestade(texto_para_analise)
            
            status.update(label="Concluído!", state="complete", expanded=False)
            
            if resultado:
                st.subheader("⛈️ Estruturas Geradas")
                st.markdown(resultado)
                st.code(resultado, language="markdown")
        else:
            status.update(label="Falha no processamento", state="error")
            st.error("Não foi possível extrair conteúdo suficiente para análise.")