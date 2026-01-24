import streamlit as st
import requests
import os
from apify_client import ApifyClient
from groq import Groq

# --- FUNÇÃO AUXILIAR: WHISPER ---
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

# --- FUNÇÃO PRINCIPAL: APIFY ---
def pegar_dados_youtube_apify(url):
    if "apify_token" not in st.secrets:
        st.error("❌ Token 'apify_token' não encontrado.")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # ---------------------------------------------------------
    # PASSO 1: TENTAR PEGAR LEGENDA (Sem baixar vídeo)
    # Actor: streamers/youtube-scraper
    # ---------------------------------------------------------
    st.info("1️⃣ Apify: Verificando legendas (Método Rápido)...")
    
    dados_finais = {}
    
    try:
        run_meta = client.actor("streamers/youtube-scraper").call(run_input={
            "startUrls": [{"url": url}],
            "maxResults": 1,
            "downloadSubtitles": True,
            "saveSubsToKVS": False
        })
        
        if run_meta:
            items = client.dataset(run_meta["defaultDatasetId"]).list_items().items
            if items:
                item = items[0]
                
                # Extração de Legendas
                txt = ""
                subs = item.get('subtitles', [])
                if isinstance(subs, list):
                    for sub in subs:
                        if 'lines' in sub:
                            for l in sub['lines']: txt += l.get('text', '') + " "
                        elif 'text' in sub: txt += sub['text'] + " "
                
                dados_finais = {
                    "sucesso": True,
                    "id_unico": item.get('id', ''),
                    "titulo": item.get('title', 'Sem Título'),
                    "canal": item.get('channelName', 'Desconhecido'),
                    "views": item.get('viewCount', 0),
                    "likes": item.get('likes', 0),
                    "data_post": item.get('date', ''),
                    "transcricao": txt,
                    "description": item.get('description', ''),
                    "url": url
                }
    except Exception as e:
        st.warning(f"Erro ao buscar metadados (Ignorando): {e}")

    # ---------------------------------------------------------
    # PASSO 2: SE NÃO TEM LEGENDA -> USAR EPCTEX + WHISPER
    # Actor: epctex/youtube-video-downloader
    # ---------------------------------------------------------
    if not dados_finais.get("transcricao") or len(dados_finais["transcricao"]) < 50:
        st.warning("⚠️ Sem legenda. Iniciando Plano B: Download via Apify (epctex)...")
        
        run_input_down = {
            "videoUrls": [{"url": url}],
            "quality": "low", # Baixa qualidade para ser rápido (o Whisper entende)
            "maxVideoDuration": 20 # Limite de 20 minutos para segurança
        }
        
        try:
            # Chama o EPCTEX
            run_down = client.actor("epctex/youtube-video-downloader").call(run_input=run_input_down)
            
            if run_down:
                items_down = client.dataset(run_down["defaultDatasetId"]).list_items().items
                
                if items_down:
                    # O epctex retorna um link direto para o vídeo
                    video_url = items_down[0].get('downloadUrl')
                    
                    if video_url:
                        st.info("⬇️ Link gerado! Baixando arquivo...")
                        
                        caminho_temp = "temp_apify.mp4"
                        
                        # Baixa o arquivo do link da Apify
                        with requests.get(video_url, stream=True) as r:
                            r.raise_for_status()
                            with open(caminho_temp, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        
                        st.info("🧠 Transcrevendo áudio (Groq Whisper)...")
                        texto_whisper = transcrever_com_whisper_groq(caminho_temp)
                        
                        # Atualiza os dados
                        dados_finais["transcricao"] = texto_whisper
                        
                        # Se não tinha metadados antes (falha no passo 1), preenche básico
                        if not dados_finais.get("titulo"):
                            dados_finais["titulo"] = items_down[0].get('title', 'Vídeo YouTube')
                            dados_finais["id_unico"] = url # Fallback
                            
                        # Limpa
                        if os.path.exists(caminho_temp): os.remove(caminho_temp)
                        
                    else:
                        st.error("Apify não retornou URL de download.")
                else:
                    st.error("Apify finalizou mas sem resultados (Dataset vazio).")
            else:
                st.error("Falha ao iniciar o Actor epctex.")
                
        except Exception as e:
            st.error(f"Erro fatal no download: {e}")
            dados_finais["transcricao"] = dados_finais.get('description', '')

    return dados_finais