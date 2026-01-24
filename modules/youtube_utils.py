import streamlit as st
from apify_client import ApifyClient

def pegar_dados_youtube_apify(url):
    """
    Função MODULAR: Recebe URL do YouTube, chama Apify (Actor Oficial)
    e retorna metadados + transcrição.
    """
    # 1. Verifica Token
    if "apify_token" not in st.secrets:
        st.error("❌ Erro: Token 'apify_token' não encontrado no secrets.toml")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # 2. Configura o Robô OFICIAL (apify/youtube-scraper)
    # Docs: https://apify.com/apify/youtube-scraper
    run_input = {
        "startUrls": [{"url": url}], # O formato oficial exige lista de objetos
        "downloadSubtitles": True,   # Pede legendas
        "maxResults": 1,
        "resultsType": "details"     # Pega detalhes e legendas, não comentários
    }
    
    try:
        status_msg = st.empty()
        status_msg.info("🔄 Módulo YouTube: Acessando Apify Oficial (Bypassing IP Block)...")
        
        # 3. Executa o Robô Oficial
        # Substituímos o 'streampot' pelo 'apify/youtube-scraper'
        run = client.actor("apify/youtube-scraper").call(run_input=run_input)
        
        if not run:
            status_msg.error("❌ Apify não retornou execução.")
            return None
        
        # 4. Pega os resultados
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        status_msg.empty() 
        
        if dataset_items:
            item = dataset_items[0]
            
            # 5. Processa a Transcrição
            # O formato do apify/youtube-scraper retorna 'subtitles' como lista de dicts
            transcricao_texto = ""
            subtitles = item.get('subtitles', [])
            
            # Procura legenda em Português ou Inglês (prioridade automática do scraper)
            if subtitles:
                for sub in subtitles:
                    # Tenta pegar o texto das linhas
                    lines = sub.get('lines', [])
                    for line in lines:
                        transcricao_texto += line.get('text', '') + " "
            
            # Fallback: Se a estrutura for diferente (texto corrido)
            if not transcricao_texto and isinstance(subtitles, str):
                transcricao_texto = subtitles

            # Último Fallback: Descrição
            if not transcricao_texto:
                transcricao_texto = item.get('description', '')

            # 6. Retorna Dicionário Limpo
            return {
                "sucesso": True,
                "id_unico": item.get('id', ''),
                "titulo": item.get('title', 'Sem Título'),
                "canal": item.get('channelName', item.get('channel', {}).get('name', 'Desconhecido')),
                "views": item.get('viewCount', 0),
                "likes": item.get('likes', 0), # As vezes vem como likeCount
                "data_post": item.get('date', ''),
                "transcricao": transcricao_texto,
                "url": url
            }
            
        else:
            st.warning("⚠️ Apify rodou, mas não retornou dados (Vídeo privado ou erro interno).")
            return None

    except Exception as e:
        st.error(f"❌ Erro Crítico no Módulo YouTube: {e}")
        return None