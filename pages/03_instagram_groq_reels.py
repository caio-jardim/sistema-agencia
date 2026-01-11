import streamlit as st
import time
import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from apify_client import ApifyClient
from datetime import datetime, timedelta, timezone
from groq import Groq
from moviepy.editor import VideoFileClip

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Viral Analyzer (Apify + Groq)", page_icon="⚡")

st.title("⚡ Viral Analyzer: Apify + Groq Whisper")
st.markdown("---")

# --- CONFIGURAÇÕES LATERAIS ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=60)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=1)
    
    st.success("✅ Infraestrutura: Apify (Nuvem)\n✅ Inteligência: Groq (Whisper + Llama)")

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
            # Cabeçalho adaptado para a saída da Groq
            sheet.append_row([
                "Data Coleta", "Perfil", "Janela", "Rank", "Data Post", 
                "Views (Play)", "Likes", "Comentários", "Link", "Legenda Original",
                "Transcrição (Whisper)", "Gancho Verbal (IA)"
            ])
        return sheet
    except Exception as e:
        st.error(f"Erro Sheets: {e}")
        return None

def baixar_video_url(url, filename):
    """Baixa o vídeo da URL fornecida pelo Apify com headers de navegador"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Erro download URL {url}: {e}")
        return False

def analisar_video_groq(video_path, status_box):
    """
    Extrai áudio e usa Whisper + Llama 3 via Groq
    """
    client_groq = Groq(api_key=st.secrets["groq_api_key"])
    
    # Define caminho do audio temporário
    audio_path = video_path.replace(".mp4", ".mp3")

    try:
        # 1. Extração de Áudio
        status_box.write("🔊 Extraindo áudio (MoviePy)...")
        try:
            video_clip = VideoFileClip(video_path)
            video_clip.audio.write_audiofile(
                audio_path, 
                bitrate="32k", 
                verbose=False, 
                logger=None
            )
            video_clip.close()
        except Exception as e:
            return {"transcricao": f"Erro MoviePy: {e}", "ganchos_verbais": "-"}

        # 2. Transcrição (Whisper)
        status_box.write("📝 Transcrevendo com Whisper Large v3...")
        with open(audio_path, "rb") as file:
            transcription = client_groq.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3", 
                response_format="text"
            )
        texto_transcrito = str(transcription)

        # 3. Análise de Gancho (Llama 3)
        status_box.write("🧠 Identificando Gancho com Llama 3...")
        prompt = f"""
        Abaixo está o começo da transcrição de um vídeo:
        "{texto_transcrito[:4000]}"

        Tarefa: Identifique a frase exata usada no início (gancho) para prender a atenção.
        Retorne APENAS um JSON: {{ "ganchos_verbais": "A frase do gancho aqui" }}
        """
        
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, 
            response_format={"type": "json_object"}
        )

        resultado_ia = json.loads(completion.choices[0].message.content)

        # Limpeza do áudio (o vídeo será limpo no loop principal)
        if os.path.exists(audio_path): 
            os.remove(audio_path)

        return {
            "transcricao": texto_transcrito,
            "ganchos_verbais": resultado_ia.get("ganchos_verbais", "-")
        }

    except Exception as e:
        status_box.error(f"Erro Groq: {e}")
        if os.path.exists(audio_path): os.remove(audio_path)
        return {"transcricao": "Erro API", "ganchos_verbais": "-"}

def pegar_dados_apify(perfil, dias, container_log):
    """
    Busca dados via Apify (Sem login local)
    """
    if "apify_token" not in st.secrets:
        st.error("Token da Apify não configurado no secrets.toml")
        return []

    client = ApifyClient(st.secrets["apify_token"])
    items_coletados = []
    
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
            # Filtros e tratamento de dados (Idêntico ao anterior que funcionou)
            tipo = item.get('type', '')
            if tipo not in ['Video', 'Reel', 'Sidecar', 'GraphVideo', 'GraphSidecar']:
                if not item.get('is_video', False): continue
            
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
                 children = item.get('childPosts') or item.get('children') or item.get('images') or []
                 if children:
                     for child in children:
                         if (child.get('type') == 'Video' or child.get('is_video')) and child.get('videoUrl'):
                             video_url = child.get('videoUrl')
                             break
            if not video_url: continue

            legenda_raw = item.get('caption') or item.get('description') or ""
            if legenda_raw is None: legenda_raw = ""
            
            views = item.get('videoViewCount') or item.get('playCount') or item.get('viewCount') or 0
            
            items_coletados.append({
                "pk": item.get('id'),
                "data_str": data_post.strftime("%d/%m/%Y"),
                "views": int(views),
                "likes": int(item.get('likesCount') or 0),
                "comments": int(item.get('commentsCount') or 0),
                "link": f"https://www.instagram.com/p/{item.get('shortCode')}/",
                "caption": str(legenda_raw)[:300] + "...",
                "download_url": video_url
            })
            
    except Exception as e:
        st.error(f"Erro na Apify: {e}")
        return []

    return items_coletados

# --- BOTÃO PRINCIPAL ---
if st.button("🚀 Iniciar Análise (Apify + Groq)", type="primary"):
    
    sheet = conectar_sheets()
    if not sheet: st.stop()

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if not os.path.exists('temp_videos_groq'):
        os.makedirs('temp_videos_groq')

    for perfil in PERFIS_ALVO:
        st.subheader(f"🔍 @{perfil}")
        log_box = st.expander("Logs do Processamento", expanded=True)
        
        with log_box:
            videos = pegar_dados_apify(perfil, DIAS_ANALISE, st)
        
        if not videos:
            st.warning("Nenhum vídeo recente encontrado.")
            continue
            
        top_final = sorted(videos, key=lambda x: x['views'], reverse=True)[:TOP_VIDEOS]
        st.write(f"🏆 Top {len(top_final)} vídeos identificados.")
        
        rows = []
        barra = st.progress(0)
        
        for i, v in enumerate(top_final):
            rank = i + 1
            ia_data = {"transcricao": "", "ganchos_verbais": ""}
            
            if rank <= TOP_ANALISE_IA:
                # Container de Status Expandido
                with st.status(f"⭐ [Top {rank}] Processando Vídeo ({v['views']} views)...", expanded=True) as status:
                    
                    caminho_video_temp = os.path.join('temp_videos_groq', f"{v['pk']}.mp4")
                    
                    # 1. Baixar
                    status.write("⬇️ Baixando arquivo...")
                    sucesso_download = baixar_video_url(v['download_url'], caminho_video_temp)
                    
                    if sucesso_download:
                        # 2. Analisar com Groq
                        ia_data = analisar_video_groq(caminho_video_temp, status)
                        
                        # Limpa vídeo
                        if os.path.exists(caminho_video_temp):
                            os.remove(caminho_video_temp)
                        
                        status.update(label="✅ Análise Groq Completa!", state="complete", expanded=False)
                    else:
                        status.update(label="❌ Falha no Download", state="error")

            rows.append([
                timestamp, f"@{perfil}", f"{DIAS_ANALISE}d", f"{rank}º",
                v['data_str'], v['views'], v['likes'], v['comments'], v['link'],
                v['caption'],
                ia_data.get('transcricao', ''),
                ia_data.get('ganchos_verbais', '')
            ])
            
            barra.progress((i + 1) / len(top_final))

        sheet.append_rows(rows)
        st.toast(f"@{perfil} Salvo!", icon="💾")
        time.sleep(2)
    
    try:
        if os.path.exists('temp_videos_groq'):
            for f in os.listdir('temp_videos_groq'):
                os.remove(os.path.join('temp_videos_groq', f))
            os.rmdir('temp_videos_groq')
    except: pass

    st.balloons()
    st.success("🏁 Análise Finalizada com Sucesso!")