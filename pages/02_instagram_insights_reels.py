import streamlit as st
import time
import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from apify_client import ApifyClient # <--- TROCA DE INSTAGRAPI POR APIFY
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Viral Analyzer Pro (Apify)", page_icon="📈")

st.title("📈 Viral Analyzer Pro + IA (Via Apify)")
st.markdown("---")

# --- CONFIGURAÇÕES LATERAIS ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=15)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=1)
    
    st.success("✅ Modo Nuvem Ativo (Sem login/senha)")

# --- FUNÇÕES ---

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        nome_planilha = "Conteudo"
        try:
            sheet = client.open(nome_planilha).sheet1
        except:
            sh = client.create(nome_planilha)
            sheet = sh.sheet1
            sheet.append_row([
                "Data Coleta", "Perfil", "Janela", "Rank", "Data Post", 
                "Views (Play)", "Likes", "Comentários", "Link", 
                "IA: Transcrição", "IA: Ganchos Virais", "IA: Ganchos Visuais"
            ])
        return sheet
    except Exception as e:
        st.error(f"Erro Sheets: {e}")
        return None

def baixar_video_url(url, filename):
    """Baixa o vídeo da URL fornecida pelo Apify com headers de navegador"""
    try:
        # Finge ser um navegador Chrome para o servidor não bloquear o download
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Timeout para não travar se a net estiver lenta
        response = requests.get(url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        # Mostra o erro no terminal do Streamlit para debug
        print(f"❌ Erro download URL {url}: {e}")
        return False

def analisar_video_com_gemini(video_path):
    genai.configure(api_key=st.secrets["gemini_api_key"])
    generation_config = {
      "temperature": 0.4,
      "top_p": 0.95,
      "max_output_tokens": 8192,
      "response_mime_type": "application/json",
    }
    
    try:
        with st.spinner('♊ IA Analisando vídeo...'):
            video_file = genai.upload_file(path=video_path)
            
            while video_file.state.name == "PROCESSING":
                time.sleep(1)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                return {"transcricao": "Erro", "ganchos_verbais": "Falha proc.", "ganchos_visuais": "-"}

            prompt = """
            Você é um especialista em viralização de Reels. Analise este vídeo e retorne um JSON exato:
            {
                "transcricao": "Texto completo do que foi falado",
                "ganchos_verbais": "Quais frases exatas foram usadas no início para prender a atenção?",
                "ganchos_visuais": "O que acontece visualmente nos primeiros 3 segundos que prende o olho?"
            }
            """
            model = genai.GenerativeModel("gemini-2.0-flash", generation_config=generation_config)
            response = model.generate_content([video_file, prompt])
            
            genai.delete_file(video_file.name)
            return json.loads(response.text)
            
    except Exception as e:
        return {"transcricao": "Erro API", "ganchos_verbais": "-", "ganchos_visuais": "-"}

def pegar_dados_apify(perfil, dias, container_log):
    """
    Substitui a lógica manual pela API profissional do Apify.
    Versão Corrigida: User Search + Tratamento de Legenda/Vídeo
    """
    if "apify_token" not in st.secrets:
        st.error("Token da Apify não configurado no secrets.toml")
        return []

    client = ApifyClient(st.secrets["apify_token"])
    items_coletados = []
    
    # Configuração correta que funcionou
    run_input = {
        "directUrls": [f"https://www.instagram.com/{perfil}/"],
        "resultsType": "posts",
        "resultsLimit": 30,
        "searchType": "user",
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"] 
        }
    }

    container_log.info(f"📡 Conectando Apify em: https://www.instagram.com/{perfil}/ ...")

    try:
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        if not run:
            st.error("Erro: O Apify não retornou execução.")
            return []

        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        
        container_log.info(f"📦 Apify retornou {len(dataset_items)} itens. Filtrando...")
        
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
        
        for item in dataset_items:
            # --- 1. Filtro de Tipo ---
            tipo = item.get('type', '')
            # Aceita 'Video', 'Reel', e também casos onde 'is_video' é true
            if tipo not in ['Video', 'Reel', 'Sidecar', 'GraphVideo', 'GraphSidecar']:
                # Checagem extra caso o tipo venha diferente
                if not item.get('is_video', False):
                    continue
                
            # --- 2. Tratamento de Data ---
            ts_str = item.get('timestamp')
            if not ts_str: continue
            
            try:
                if ts_str.endswith('Z'):
                    data_post = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                else:
                    data_post = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            except:
                continue 

            if data_post < data_limite:
                continue

            # --- 3. Busca Robusta da URL do Vídeo ---
            video_url = item.get('videoUrl')
            
            # Se for Carrossel ou se videoUrl veio vazio, tenta achar nos filhos
            if not video_url:
                 # Tenta diferentes nomes que o Apify usa para "filhos"
                 children = item.get('childPosts') or item.get('children') or item.get('images') or []
                 if children:
                     for child in children:
                         # Procura o primeiro filho que seja vídeo
                         if (child.get('type') == 'Video' or child.get('is_video')) and child.get('videoUrl'):
                             video_url = child.get('videoUrl')
                             break

            # Se mesmo assim não achou, pula
            if not video_url: continue

            # --- 4. Tratamento Robusto da Legenda ---
            # Garante que seja string, mesmo se vier None
            legenda_raw = item.get('caption') or item.get('description') or ""
            if legenda_raw is None: legenda_raw = ""
            
            # --- 5. Extração de Métricas (Evita erros de None) ---
            views = item.get('videoViewCount') or item.get('playCount') or item.get('viewCount') or 0
            likes = item.get('likesCount') or item.get('likes') or 0
            comments = item.get('commentsCount') or item.get('comments') or 0
            
            # Monta o objeto final
            items_coletados.append({
                "pk": item.get('id'),
                "data_str": data_post.strftime("%d/%m/%Y"),
                "views": int(views),
                "likes": int(likes),
                "comments": int(comments),
                "link": f"https://www.instagram.com/p/{item.get('shortCode')}/",
                "caption": str(legenda_raw)[:300] + "...", # Força string e corta
                "download_url": video_url
            })
            
    except Exception as e:
        st.error(f"Erro na Apify: {e}")
        return []

    return items_coletados

# --- BOTÃO PRINCIPAL ---
if st.button("🚀 Iniciar Análise (Apify)", type="primary"):
    
    # 1. Sheets
    sheet = conectar_sheets()
    if not sheet: st.stop()

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if not os.path.exists('temp_videos'):
        os.makedirs('temp_videos')

    for perfil in PERFIS_ALVO:
        st.subheader(f"🔍 @{perfil}")
        log_box = st.expander("Logs do Processamento", expanded=True)
        
        with log_box:
            # Chama a nova função do Apify
            videos = pegar_dados_apify(perfil, DIAS_ANALISE, st)
        
        if not videos:
            st.warning("Nenhum vídeo recente encontrado.")
            continue
            
        # Ordenação
        top_final = sorted(videos, key=lambda x: x['views'], reverse=True)[:TOP_VIDEOS]
        st.write(f"🏆 Top {len(top_final)} vídeos identificados.")
        
        rows = []
        barra = st.progress(0)
        
        for i, v in enumerate(top_final):
            rank = i + 1
            ia_data = {"transcricao": "", "ganchos_verbais": "", "ganchos_visuais": ""}
            
            # IA Analysis
            if rank <= TOP_ANALISE_IA:
                st.info(f"⭐ Baixando e analisando Top {rank} ({v['views']} views)...")
                
                caminho_video_temp = os.path.join('temp_videos', f"{v['pk']}.mp4")
                
                # Baixa o vídeo da URL do Apify
                sucesso_download = baixar_video_url(v['download_url'], caminho_video_temp)
                
                if sucesso_download:
                    try:
                        ia_data = analisar_video_com_gemini(caminho_video_temp)
                        time.sleep(2)
                    except Exception as e:
                        st.error(f"Erro IA: {e}")
                    finally:
                        if os.path.exists(caminho_video_temp):
                            os.remove(caminho_video_temp)
                else:
                    st.warning("Falha ao baixar vídeo para análise.")

            # Monta linha
            rows.append([
                timestamp, f"@{perfil}", f"{DIAS_ANALISE}d", f"{rank}º",
                v['data_str'], v['views'], v['likes'], v['comments'], v['link'],
                ia_data.get('transcricao', ''),
                ia_data.get('ganchos_verbais', ''),
                ia_data.get('ganchos_visuais', '')
            ])
            
            barra.progress((i + 1) / len(top_final))

        sheet.append_rows(rows)
        st.success(f"✅ @{perfil} finalizado!")
        time.sleep(2)
    
    # Limpeza
    try:
        os.rmdir('temp_videos')
    except: pass

    st.balloons()
    st.success("🏁 Processo Finalizado!")