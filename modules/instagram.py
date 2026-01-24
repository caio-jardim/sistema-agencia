# modules/instagram.py
import streamlit as st
import time
import requests
from apify_client import ApifyClient
from datetime import datetime, timedelta, timezone
from moviepy.editor import VideoFileClip
import os

def pegar_dados_apify(perfil, dias, container_log):
    if "apify_token" not in st.secrets:
        st.error("Token da Apify não configurado.")
        return []

    client = ApifyClient(st.secrets["apify_token"])
    items_coletados = []
    
    run_input = {
        "directUrls": [f"https://www.instagram.com/{perfil}/"],
        "resultsType": "posts",
        "resultsLimit": 30, 
        "searchType": "user",
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
    }

    container_log.info(f"📡 Apify: Lendo @{perfil}...")

    try:
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        if not run: return []

        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        container_log.info(f"📦 {len(dataset_items)} itens encontrados. Filtrando...")
        
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
        
        for item in dataset_items:
            tipo = item.get('type', '')
            if tipo not in ['Video', 'Reel', 'Sidecar', 'GraphVideo'] and not item.get('is_video', False):
                continue
            
            ts_str = item.get('timestamp')
            if not ts_str: continue
            
            try:
                if ts_str.endswith('Z'):
                    data_post = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                else:
                    data_post = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            except: continue 

            if data_post < data_limite: continue

            video_url = item.get('videoUrl')
            if not video_url:
                 children = item.get('childPosts') or item.get('children') or []
                 for child in children:
                     if (child.get('type') == 'Video' or child.get('is_video')) and child.get('videoUrl'):
                         video_url = child.get('videoUrl')
                         break
            if not video_url: continue

            legenda_raw = item.get('caption') or item.get('description') or ""
            views = item.get('videoViewCount') or item.get('playCount') or item.get('viewCount') or 0
            
            items_coletados.append({
                "pk": str(item.get('id')),
                "data_str": data_post.strftime("%d/%m/%Y"),
                "views": int(views),
                "likes": int(item.get('likesCount') or 0),
                "comments": int(item.get('commentsCount') or 0),
                "link": f"https://www.instagram.com/p/{item.get('shortCode')}/",
                "caption": str(legenda_raw),
                "download_url": video_url
            })
            
    except Exception as e:
        st.error(f"Erro na Apify: {e}")
        return []

    return items_coletados

def baixar_video_with_retry(url, filename, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.instagram.com/"
    }
    for i in range(retries):
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            return True
        except Exception as e:
            time.sleep(2 + i)
            if i == retries - 1:
                try:
                    import urllib.request
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-Agent', headers['User-Agent'])]
                    urllib.request.install_opener(opener)
                    urllib.request.urlretrieve(url, filename)
                    return True
                except: return False
    return False

def download_file(url, filename):
    """Baixa arquivo genérico via requests"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e:
        st.error(f"Erro download arquivo: {e}")
        return False

def get_instagram_data_apify(url):
    """Pega dados de um post específico do Instagram"""
    if "apify_token" not in st.secrets: return None
    client = ApifyClient(st.secrets["apify_token"])
    
    run_input = {
        "directUrls": [url],
        "resultsType": "posts",
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
    }
    try:
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        if not run: return None
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        if dataset_items: return dataset_items[0]
        return None
    except Exception as e:
        st.error(f"Erro na Apify Insta: {e}")
        return None