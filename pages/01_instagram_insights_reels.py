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

# --- SISTEMA DE LOGIN ---
def check_password():
    """Retorna True se o usuário tiver a senha correta."""
    def password_entered():
        if st.session_state["password"] == st.secrets["general"]["team_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" in st.session_state:
        if st.session_state["password_correct"]:
            return True

    st.markdown("### 🔒 Acesso Restrito - Equipe E21")
    st.text_input(
        "Digite a senha de acesso:", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if "password_correct" in st.session_state:
        if not st.session_state["password_correct"]:
            st.error("😕 Senha incorreta. Tente novamente.")
            
    return False

if not check_password():
    st.stop()

# --- CONFIGURAÇÕES LATERAIS ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=60)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=1)
    

# --- FUNÇÕES ---

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        nome_planilha = "Conteudo"
        nome_aba = "1M1D"
        
        sh = client.open(nome_planilha)
        try:
            sheet = sh.worksheet(nome_aba)
        except:
            st.warning(f"Aba '{nome_aba}' não encontrada. Usando a primeira aba.")
            sheet = sh.sheet1
            
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        return None

def carregar_historico_links(sheet):
    """
    Lê a planilha inteira e cria um dicionário para verificação rápida.
    Retorna: {'https://instagram...': {'transcricao': '...', 'gancho': '...'}, ...}
    """
    try:
        st.toast("Lendo histórico da planilha...", icon="📂")
        records = sheet.get_all_records()
        historico = {}
        for row in records:
            link = row.get('Link')
            if link:
                historico[link] = {
                    'transcricao': row.get('Transcrição (Whisper)', ''),
                    'ganchos_verbais': row.get('Gancho Verbal (IA)', '')
                }
        return historico
    except Exception as e:
        print(f"Erro ao ler histórico (pode ser planilha vazia): {e}")
        return {}

def baixar_video_with_retry(url, filename, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            if i < retries - 1:
                time.sleep(2)
                continue
            else:
                print(f"❌ Erro download final: {e}")
                return False

def analisar_video_groq(video_path, status_box):
    client_groq = Groq(api_key=st.secrets["groq_api_key"])
    audio_path = video_path.replace(".mp4", ".mp3")

    try:
        status_box.write("🔊 Extraindo áudio...")
        try:
            video_clip = VideoFileClip(video_path)
            video_clip.audio.write_audiofile(audio_path, bitrate="32k", verbose=False, logger=None)
            video_clip.close()
        except Exception as e:
            return {"transcricao": f"Erro MoviePy: {e}", "ganchos_verbais": "-"}

        status_box.write("📝 Transcrevendo (Whisper)...")
        with open(audio_path, "rb") as file:
            transcription = client_groq.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3", 
                response_format="text"
            )
        texto_transcrito = str(transcription)

        status_box.write("🧠 Analisando com Llama 3...")
        prompt = f"""
        Analise a transcrição deste vídeo curto:
        "{texto_transcrito[:4000]}"

        Identifique:
        1. O Gancho Verbal (Frase exata do início).
        2. O Gancho Visual (O que descreve a cena inicial, se houver pistas no texto, senão deixe vazio).
        
        Retorne JSON: {{ "ganchos_verbais": "...", "ganchos_visuais": "..." }}
        """
        
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, 
            response_format={"type": "json_object"}
        )

        resultado_ia = json.loads(completion.choices[0].message.content)

        if os.path.exists(audio_path): os.remove(audio_path)

        return {
            "transcricao": texto_transcrito,
            "ganchos_verbais": resultado_ia.get("ganchos_verbais", "-"),
            "ganchos_visuais": resultado_ia.get("ganchos_visuais", "-")
        }

    except Exception as e:
        status_box.error(f"Erro Groq: {e}")
        if os.path.exists(audio_path): os.remove(audio_path)
        return {"transcricao": "Erro API", "ganchos_verbais": "-"}

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
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"] 
        }
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
    
    # 1. Conecta Planilha e Carrega Histórico (CACHE)
    sheet = conectar_sheets()
    if not sheet: st.stop()
    
    # MAPA DOS VÍDEOS JÁ ANALISADOS
    historico_analises = carregar_historico_links(sheet)

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
        
        barra = st.progress(0)
        
        for i, v in enumerate(top_final):
            rank = i + 1
            ia_data = {"transcricao": "", "ganchos_verbais": ""}
            link_atual = v['link']
            
            # Se for vídeo Top, decide se analisa ou recupera
            if rank <= TOP_ANALISE_IA:
                
                # --- VERIFICAÇÃO DE CACHE (ECONOMIA) ---
                if link_atual in historico_analises:
                    # Se já existe, copia os dados antigos
                    st.toast(f"Top {rank}: Recuperado do Cache ♻️", icon="⚡")
                    ia_data['transcricao'] = historico_analises[link_atual]['transcricao']
                    ia_data['ganchos_verbais'] = historico_analises[link_atual]['ganchos_verbais']
                    
                    # Log visual para o usuário saber que foi rápido
                    with st.status(f"♻️ [Top {rank}] Vídeo já analisado anteriormente!", expanded=False, state="complete") as status:
                        status.write("Dados recuperados da planilha para economizar créditos.")
                
                else:
                    # Se é novo, faz o processo completo (Download + Groq)
                    with st.status(f"⭐ [Top {rank}] Processando Novo Vídeo ({v['views']} views)...", expanded=True) as status:
                        
                        caminho_video_temp = os.path.join('temp_videos_groq', f"{v['pk']}.mp4")
                        
                        status.write("⬇️ Baixando arquivo...")
                        sucesso_download = baixar_video_with_retry(v['download_url'], caminho_video_temp)
                        
                        if sucesso_download:
                            ia_data = analisar_video_groq(caminho_video_temp, status)
                            
                            if os.path.exists(caminho_video_temp):
                                os.remove(caminho_video_temp)
                            
                            status.update(label="✅ Análise Groq Completa!", state="complete", expanded=False)
                        else:
                            status.update(label="❌ Falha no Download", state="error")
                            ia_data["transcricao"] = "Erro Download"

            # --- SALVA NO SHEETS ---
            nova_linha = [
                timestamp, f"@{perfil}", f"{DIAS_ANALISE}d", f"{rank}º",
                v['data_str'], v['views'], v['likes'], v['comments'], v['link'],
                v['caption'],
                ia_data.get('transcricao', ''),
                ia_data.get('ganchos_verbais', '')
            ]
            
            try:
                sheet.append_row(nova_linha)
                # Atualiza o cache localmente para o próximo loop (opcional, mas boa prática)
                historico_analises[link_atual] = {
                    'transcricao': ia_data.get('transcricao', ''),
                    'ganchos_verbais': ia_data.get('ganchos_verbais', '')
                }
                st.toast(f"Top {rank} de @{perfil} salvo!", icon="💾")
            except Exception as e:
                st.error(f"Erro ao salvar linha no Excel: {e}")

            barra.progress((i + 1) / len(top_final))
        
        time.sleep(1)

    # Limpeza Final
    try:
        if os.path.exists('temp_videos_groq'):
            for f in os.listdir('temp_videos_groq'):
                os.remove(os.path.join('temp_videos_groq', f))
            os.rmdir('temp_videos_groq')
    except: pass

    st.balloons()
    st.success("🏁 Análise Finalizada!")