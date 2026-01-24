import streamlit as st
import requests
import os
from apify_client import ApifyClient
from groq import Groq

# --- FUNÇÃO AUXILIAR: WHISPER ---
def transcrever_com_whisper_groq(caminho_arquivo):
    """Lê o arquivo de áudio e manda para a Groq"""
    if "groq" not in st.secrets:
        return "Erro: Chave Groq não configurada."
    
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    
    try:
        with open(caminho_arquivo, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(caminho_arquivo, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        return str(transcription)
    except Exception as e:
        return f"Erro na Transcrição Groq: {e}"

# --- FUNÇÃO PRINCIPAL: APIFY ---
def pegar_dados_youtube_apify(url):
    """
    1. Tenta pegar metadados e legendas com 'streamers/youtube-scraper'.
    2. Se não tiver legenda, usa 'wudizhang/youtube-downloader' para baixar áudio e usar Whisper.
    """
    if "apify_token" not in st.secrets:
        st.error("❌ Token 'apify_token' não encontrado.")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # ---------------------------------------------------------
    # PASSO 1: TENTAR PEGAR DADOS E LEGENDA (RÁPIDO)
    # ---------------------------------------------------------
    st.info("1️⃣ Apify: Buscando dados e legendas...")
    
    run_input = {
        "startUrls": [{"url": url}],
        "maxResults": 1,
        "downloadSubtitles": True,
        "saveSubsToKVS": False
    }
    
    dados_finais = {}
    
    try:
        # Usa o 'streamers/youtube-scraper' para metadados
        run = client.actor("streamers/youtube-scraper").call(run_input=run_input)
        if not run: return None
        
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        if not dataset_items: return None
        
        item = dataset_items[0]
        
        # Tenta montar a transcrição das legendas
        transcricao_texto = ""
        subtitles = item.get('subtitles', [])
        
        if isinstance(subtitles, list):
            for sub in subtitles:
                if 'lines' in sub:
                    for line in sub['lines']:
                        transcricao_texto += line.get('text', '') + " "
                elif 'text' in sub:
                    transcricao_texto += sub['text'] + " "
        
        # Preenche os dados iniciais
        dados_finais = {
            "sucesso": True,
            "id_unico": item.get('id', ''),
            "titulo": item.get('title', 'Sem Título'),
            "canal": item.get('channelName', 'Desconhecido'),
            "views": item.get('viewCount', 0),
            "likes": item.get('likes', 0),
            "data_post": item.get('date', ''),
            "transcricao": transcricao_texto,
            "url": url
        }

    except Exception as e:
        st.error(f"Erro na fase de metadados: {e}")
        return None

    # ---------------------------------------------------------
    # PASSO 2: SE A LEGENDA VEIO VAZIA -> USAR WHISPER
    # ---------------------------------------------------------
    if not dados_finais.get("transcricao") or len(dados_finais["transcricao"]) < 50:
        st.warning("⚠️ Legenda não encontrada. Iniciando Plano B: Download + Whisper...")
        
        # Usa outro Actor especializado em DOWNLOAD direto (wudizhang/youtube-downloader)
        # Ele retorna o link direto do áudio/vídeo sem bloqueio 403
        run_input_down = {
            "url": url,
            "audioOnly": True # Pede só áudio para ser leve
        }
        
        try:
            # Chama o downloader
            run_down = client.actor("wudizhang/youtube-downloader").call(run_input=run_input_down)
            if run_down:
                dataset_down = client.dataset(run_down["defaultDatasetId"]).list_items().items
                
                if dataset_down:
                    # Pega o link de download gerado pela Apify
                    # Geralmente vem em 'downloadUrl' ou 'url'
                    audio_url = dataset_down[0].get('downloadUrl') or dataset_down[0].get('url')
                    
                    if audio_url:
                        st.info("⬇️ Baixando áudio temporário...")
                        # Baixa o arquivo para o Streamlit
                        caminho_audio = "temp_apify_audio.mp3"
                        
                        # Headers para evitar bloqueio no download do link gerado
                        headers = {"User-Agent": "Mozilla/5.0"}
                        with requests.get(audio_url, headers=headers, stream=True) as r:
                            r.raise_for_status()
                            with open(caminho_audio, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        
                        # Manda pro Whisper
                        st.info("🧠 Processando no Whisper (Groq)...")
                        texto_whisper = transcrever_com_whisper_groq(caminho_audio)
                        
                        # Atualiza a transcrição
                        dados_finais["transcricao"] = texto_whisper
                        
                        # Limpa
                        if os.path.exists(caminho_audio): os.remove(caminho_audio)
                        
                    else:
                        st.error("Apify não retornou link de download direto.")
                        # Fallback final: descrição
                        dados_finais["transcricao"] = "Sem áudio. Descrição: " + item.get('description', '')
                else:
                    st.error("Downloader rodou mas não achou links.")
        except Exception as e:
            st.error(f"Erro no processo de download/whisper: {e}")
            dados_finais["transcricao"] = item.get('description', '')

    return dados_finais