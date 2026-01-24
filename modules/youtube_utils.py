import streamlit as st
from apify_client import ApifyClient

def pegar_dados_youtube_apify(url):
    """
    Função MODULAR: Recebe URL do YouTube, chama Apify (Streampot)
    e retorna metadados + transcrição limpa.
    """
    # 1. Verifica Token
    if "apify_token" not in st.secrets:
        st.error("❌ Erro: Token 'apify_token' não encontrado no secrets.toml")
        return None
        
    client = ApifyClient(st.secrets["apify_token"])

    # 2. Configura o Robô (Actor: streampot/youtube-scraper)
    # Docs: https://apify.com/streampot/youtube-scraper
    run_input = {
        "urls": [url],
        "downloads": ["subtitles"], # O PULO DO GATO: Pede só a legenda
        "maxResults": 1
    }
    
    try:
        status_msg = st.empty()
        status_msg.info("🔄 Módulo YouTube: Acessando Apify (Isso evita bloqueio de IP)...")
        
        # 3. Executa o Robô
        run = client.actor("streampot/youtube-scraper").call(run_input=run_input)
        
        if not run:
            status_msg.error("❌ Apify não retornou execução.")
            return None
        
        # 4. Pega os resultados
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        status_msg.empty() # Limpa a mensagem
        
        if dataset_items:
            item = dataset_items[0]
            
            # 5. Processa a Transcrição (Junta os pedaços)
            transcricao_texto = ""
            subtitles = item.get('subtitles', [])
            
            if subtitles:
                for sub in subtitles:
                    # Tenta pegar o texto (as vezes vem como 'text', as vezes 'content')
                    texto = sub.get('text') or sub.get('content') or ""
                    transcricao_texto += texto + " "
            
            # Fallback: Se não tem legenda, usa descrição
            if not transcricao_texto:
                transcricao_texto = item.get('description', '')

            # 6. Retorna Dicionário Limpo
            return {
                "sucesso": True,
                "id_unico": item.get('id', ''),
                "titulo": item.get('title', 'Sem Título'),
                "canal": item.get('channel', {}).get('name', 'Desconhecido'),
                "views": item.get('viewCount', 0),
                "likes": item.get('likeCount', 0),
                "data_post": item.get('uploadDate', ''),
                "transcricao": transcricao_texto,
                "url": url
            }
            
        else:
            st.warning("⚠️ Apify rodou, mas não achou o vídeo (pode ser privado ou deletado).")
            return None

    except Exception as e:
        st.error(f"❌ Erro Crítico no Módulo YouTube: {e}")
        return None