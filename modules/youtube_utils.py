import streamlit as st
from apify_client import ApifyClient

def pegar_dados_youtube_apify(url):
    """
    Função MODULAR: Usa o Actor 'streamers/youtube-scraper'
    para pegar metadados e legendas sem bloqueio.
    """
    # 1. Verifica Token
    if "apify_token" not in st.secrets:
        st.error("❌ Erro: Token 'apify_token' não encontrado no secrets.toml")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # 2. Configura o Robô (streamers/youtube-scraper)
    run_input = {
        "startUrls": [{"url": url}],  # Formato exigido: Lista de objetos
        "maxResults": 1,
        "downloadSubtitles": True,    # Pede legendas
        "saveSubsToKVS": False        # Traz no JSON (mais rápido) ao invés de salvar arquivo
    }
    
    try:
        status_msg = st.empty()
        status_msg.info("🔄 Módulo YouTube: Acessando Apify (streamers/youtube-scraper)...")
        
        # 3. Executa o Robô
        run = client.actor("streamers/youtube-scraper").call(run_input=run_input)
        
        if not run:
            status_msg.error("❌ Apify não retornou execução.")
            return None
        
        # 4. Pega os resultados
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        status_msg.empty() 
        
        if dataset_items:
            item = dataset_items[0]
            
            # 5. Processa a Transcrição
            transcricao_texto = ""
            subtitles = item.get('subtitles', [])
            
            # O 'streamers' geralmente retorna uma lista de dicts com 'url' e 'name' (lang)
            # ou o conteúdo direto se configurado. Vamos tentar extrair de várias formas.
            
            # Se vier o texto direto nas linhas (formato comum)
            if isinstance(subtitles, list):
                for sub in subtitles:
                    # Tenta pegar linhas de texto
                    if 'lines' in sub:
                        for line in sub['lines']:
                            transcricao_texto += line.get('text', '') + " "
                    # Ou se vier texto direto
                    elif 'text' in sub:
                        transcricao_texto += sub['text'] + " "
            
            # Fallback: Se não achou legenda, pega a descrição
            if not transcricao_texto:
                transcricao_texto = item.get('description', '')

            # 6. Retorna Dicionário Limpo
            return {
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
            
        else:
            st.warning("⚠️ Apify rodou mas não retornou dados (Vídeo privado?).")
            return None

    except Exception as e:
        st.error(f"❌ Erro Crítico no Módulo YouTube: {e}")
        return None