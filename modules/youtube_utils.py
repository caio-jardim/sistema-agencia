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
    1. Tenta pegar metadados e legendas (streamers/youtube-scraper).
    2. Se falhar, baixa o áudio (daibolo/youtube-downloader) e usa Whisper.
    """
    if "apify_token" not in st.secrets:
        st.error("❌ Token 'apify_token' não encontrado.")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # ---------------------------------------------------------
    # PASSO 1: TENTAR PEGAR DADOS E LEGENDA (RÁPIDO)
    # ---------------------------------------------------------
    st.info("1️⃣ Apify: Buscando dados e legendas...")
    
    run_input_meta = {
        "startUrls": [{"url": url}],
        "maxResults": 1,
        "downloadSubtitles": True,
        "saveSubsToKVS": False
    }
    
    dados_finais = {}
    
    try:
        # Usa o 'streamers/youtube-scraper' para metadados
        run = client.actor("streamers/youtube-scraper").call(run_input=run_input_meta)
        
        if run:
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            if dataset_items:
                item = dataset_items[0]
                
                # Monta a transcrição das legendas
                transcricao_texto = ""
                subtitles = item.get('subtitles', [])
                
                if isinstance(subtitles, list):
                    for sub in subtitles:
                        if 'lines' in sub:
                            for line in sub['lines']:
                                transcricao_texto += line.get('text', '') + " "
                        elif 'text' in sub:
                            transcricao_texto += sub['text'] + " "
                
                dados_finais = {
                    "sucesso": True,
                    "id_unico": item.get('id', ''),
                    "titulo": item.get('title', 'Sem Título'),
                    "canal": item.get('channelName', 'Desconhecido'),
                    "views": item.get('viewCount', 0),
                    "likes": item.get('likes', 0),
                    "data_post": item.get('date', ''),
                    "transcricao": transcricao_texto,
                    "url": url,
                    "description": item.get('description', '')
                }
    except Exception as e:
        st.error(f"Erro na fase de metadados: {e}")
        # Não retorna None aqui, tenta continuar para o download se possível

    # ---------------------------------------------------------
    # PASSO 2: SE A LEGENDA VEIO VAZIA -> USAR WHISPER
    # ---------------------------------------------------------
    if not dados_finais.get("transcricao") or len(dados_finais["transcricao"]) < 50:
        st.warning("⚠️ Legenda não encontrada. Iniciando Plano B: Download + Whisper...")
        
        # Usa 'daibolo/youtube-downloader' (Estável)
        run_input_down = {
            "urls": [{"url": url}],
            "maxVideoDuration": 1200, # Limite de 20 min para economizar
        }
        
        try:
            run_down = client.actor("daibolo/youtube-downloader").call(run_input=run_input_down)
            
            if run_down:
                dataset_down = client.dataset(run_down["defaultDatasetId"]).list_items().items
                
                audio_url = None
                
                if dataset_down:
                    # O daibolo retorna várias streams. Vamos procurar a de áudio (m4a)
                    # Primeiro, tenta pegar 'downloadUrl' direto se existir
                    item_down = dataset_down[0]
                    
                    # Procura nos formatos
                    formats = item_down.get('formats', [])
                    for fmt in formats:
                        # Prioriza m4a (audio)
                        if fmt.get('extension') == 'm4a' or 'audio' in fmt.get('mimeType', ''):
                            audio_url = fmt.get('url')
                            break
                    
                    # Se não achou m4a, pega o primeiro mp4
                    if not audio_url and formats:
                        audio_url = formats[0].get('url')

                    if audio_url:
                        st.info("⬇️ Baixando stream de áudio...")
                        caminho_audio = "temp_apify_audio.mp3"
                        
                        # Headers para evitar 403 no download
                        headers = {
                            "User-Agent": "Mozilla/5.0",
                            "Referer": "https://www.youtube.com/"
                        }
                        
                        with requests.get(audio_url, headers=headers, stream=True) as r:
                            r.raise_for_status()
                            with open(caminho_audio, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        
                        st.info("🧠 Processando no Whisper (Groq)...")
                        texto_whisper = transcrever_com_whisper_groq(caminho_audio)
                        
                        # Atualiza a transcrição
                        dados_finais["transcricao"] = texto_whisper
                        
                        if os.path.exists(caminho_audio): os.remove(caminho_audio)
                        
                    else:
                        st.error("Não foi possível extrair link de áudio do vídeo.")
                        dados_finais["transcricao"] = "Sem áudio. Descrição: " + dados_finais.get('description', '')
                else:
                    st.error("Downloader rodou mas não retornou streams.")
        except Exception as e:
            st.error(f"Erro no processo de download/whisper: {e}")
            dados_finais["transcricao"] = dados_finais.get('description', '')

    return dados_finais