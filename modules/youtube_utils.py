import streamlit as st
import requests
import os
import json
from apify_client import ApifyClient
from groq import Groq

# --- WHISPER (Mantido) ---
def transcrever_com_whisper_groq(caminho_arquivo):
    if "groq" not in st.secrets: return "Erro: Chave Groq não configurada."
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    try:
        with open(caminho_arquivo, "rb") as file:
            return str(client.audio.transcriptions.create(
                file=(caminho_arquivo, file.read()),
                model="whisper-large-v3",
                response_format="text"
            ))
    except Exception as e: return f"Erro Transcrição: {e}"

# --- NOVO: COBALT MULTI-SERVER (Grátis) ---
def baixar_audio_cobalt_gratis(url_youtube):
    """
    Tenta baixar usando várias instâncias públicas do Cobalt.
    É gratuito e roda fora do servidor da Apify.
    """
    output_filename = "temp_cobalt_audio.mp3"
    
    # Lista de servidores alternativos (se um falhar, tenta o outro)
    instances = [
        "https://api.cobalt.tools/api/json",        # Oficial (muito tráfego)
        "https://cobalt.api.kwiatekmiki.pl/api/json", # Polônia
        "https://api.fnky.app/api/json",            # Alternativo
        "https://cobalt.q1.si/api/json"             # Eslovênia
    ]
    
    payload = {
        "url": url_youtube,
        "isAudioOnly": True,
        "aFormat": "mp3"
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    st.info("🔄 Tentando servidores gratuitos de download (Cobalt)...")
    
    for i, api_url in enumerate(instances):
        try:
            # status_msg = st.toast(f"Tentando servidor {i+1}...", icon="📡")
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'url' in data:
                    download_link = data['url']
                    
                    # Baixa o arquivo
                    with requests.get(download_link, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        with open(output_filename, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    if os.path.exists(output_filename):
                        return output_filename
        except:
            continue # Silenciosamente tenta o próximo

    return None

# --- FUNÇÃO PRINCIPAL ---
def pegar_dados_youtube_apify(url):
    client = ApifyClient(st.secrets["apify_token"])
    
    st.info("1️⃣ Buscando Legenda (Texto)...")
    dados_finais = {}
    
    # 1. TENTA PEGAR LEGENDA (Rápido e Barato)
    try:
        run = client.actor("streamers/youtube-scraper").call(run_input={
            "startUrls": [{"url": url}], "maxResults": 1, "downloadSubtitles": True, "saveSubsToKVS": False
        })
        if run:
            items = client.dataset(run["defaultDatasetId"]).list_items().items
            if items:
                item = items[0]
                txt = ""
                # Lógica simplificada de extração
                subs = item.get('subtitles', [])
                if isinstance(subs, list):
                    for s in subs:
                        if 'lines' in s: 
                            for l in s['lines']: txt += l.get('text', '') + " "
                        elif 'text' in s: txt += s['text'] + " "
                
                dados_finais = {
                    "sucesso": True, "transcricao": txt, 
                    "titulo": item.get('title', 'YouTube Video'),
                    "id_unico": item.get('id', ''),
                    "description": item.get('description', '')
                }
    except: pass

    # 2. SE NÃO TEM LEGENDA -> COBALT (GRÁTIS) + WHISPER
    if not dados_finais.get("transcricao") or len(dados_finais["transcricao"]) < 50:
        st.warning("⚠️ Sem legenda. Tentando download gratuito...")
        
        audio_path = baixar_audio_cobalt_gratis(url)
        
        if audio_path:
            st.success("⬇️ Download concluído! Transcrevendo...")
            texto = transcrever_com_whisper_groq(audio_path)
            dados_finais["transcricao"] = texto
            if os.path.exists(audio_path): os.remove(audio_path)
            
            # Preenche dados faltantes se o passo 1 falhou totalmente
            if not dados_finais.get("titulo"):
                dados_finais.update({"titulo": "Vídeo Transcrito", "id_unico": url, "description": ""})
        else:
            st.error("❌ Não foi possível baixar o vídeo automaticamente.")
            return {"sucesso": False, "erro": "download_failed"}

    return dados_finais