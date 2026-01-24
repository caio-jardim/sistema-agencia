import streamlit as st
import requests
import os
import time
from apify_client import ApifyClient
from groq import Groq

# --- FUNÇÃO AUXILIAR 1: WHISPER (Transcreve Áudio) ---
def transcrever_com_whisper_groq(caminho_arquivo):
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

# --- FUNÇÃO AUXILIAR 2: COBALT (Faz o Download do Áudio) ---
def baixar_audio_via_cobalt(url_youtube):
    """
    Usa a API do Cobalt (similar ao SaveFrom) para gerar um link de áudio
    e baixar o arquivo, contornando 100% dos bloqueios do YouTube.
    """
    output_filename = "temp_cobalt_audio.mp3"
    
    # Instâncias públicas do Cobalt (Alternativas caso uma falhe)
    api_instances = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.api.kwiatekmiki.pl/api/json",
        "https://api.fnky.app/api/json"
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    payload = {
        "url": url_youtube,
        "isAudioOnly": True,
        "aFormat": "mp3"
    }

    for api_url in api_instances:
        try:
            # 1. Pede o link
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                download_link = data.get('url')
                
                if download_link:
                    st.info(f"⬇️ Baixando áudio do servidor intermediário...")
                    
                    # 2. Baixa o arquivo
                    with requests.get(download_link, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        with open(output_filename, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    if os.path.exists(output_filename):
                        return output_filename
        except:
            continue # Tenta o próximo servidor se falhar
            
    return None

# --- FUNÇÃO PRINCIPAL ---
def pegar_dados_youtube_apify(url):
    """
    Lógica Híbrida:
    1. Tenta Apify para Legendas (Texto).
    2. Se falhar, usa Cobalt para baixar MP3 + Whisper.
    """
    if "apify_token" not in st.secrets:
        st.error("❌ Token 'apify_token' não encontrado.")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # --- FASE 1: METADADOS E LEGENDA (APIFY) ---
    st.info("1️⃣ Apify: Buscando dados e legendas...")
    
    dados_finais = {}
    
    try:
        run_input = {
            "startUrls": [{"url": url}],
            "maxResults": 1,
            "downloadSubtitles": True,
            "saveSubsToKVS": False
        }
        
        # Usa 'streamers/youtube-scraper' (Ótimo para metadados/texto)
        run = client.actor("streamers/youtube-scraper").call(run_input=run_input)
        
        if run:
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            if dataset_items:
                item = dataset_items[0]
                
                # Monta transcrição das legendas
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

    # --- FASE 2: PLANO B (DOWNLOAD + WHISPER) ---
    # Se a transcrição veio vazia (vídeo sem legenda), ativamos o Cobalt
    if not dados_finais.get("transcricao") or len(dados_finais["transcricao"]) < 50:
        st.warning("⚠️ Legenda não encontrada. Iniciando Plano B: Download (Cobalt) + Whisper...")
        
        caminho_audio = baixar_audio_via_cobalt(url)
        
        if caminho_audio:
            st.info("🧠 Processando no Whisper (Groq)...")
            texto_whisper = transcrever_com_whisper_groq(caminho_audio)
            
            # Salva a nova transcrição
            dados_finais["transcricao"] = texto_whisper
            
            # Limpa o arquivo
            if os.path.exists(caminho_audio): os.remove(caminho_audio)
        else:
            st.error("❌ Falha: Não foi possível baixar o áudio do vídeo.")
            # Último recurso: usa a descrição
            dados_finais["transcricao"] = "Sem áudio. Descrição: " + dados_finais.get('description', '')

    return dados_finais