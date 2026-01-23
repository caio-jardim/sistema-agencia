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
        
        # NOME ATUALIZADO
        nome_planilha = "DB_E21_Conteudos"
        nome_aba = "instagram"
        
        try:
            sh = client.open(nome_planilha)
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Planilha '{nome_planilha}' não encontrada. Verifique o nome ou compartilhamento.")
            return None

        try:
            sheet = sh.worksheet(nome_aba)
        except:
            # Cria a aba se não existir com os cabeçalhos corretos
            sheet = sh.add_worksheet(title=nome_aba, rows="1000", cols="15")
            sheet.append_row([
                "ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", 
                "URL_Original", "Views", "Likes", "Comments", 
                "Transcricao_Whisper", "Gancho_Verbal", "Legenda"
            ])
            
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        return None

def carregar_ids_existentes(sheet):
    """
    Lê a coluna ID_Unico (Coluna 1) para evitar duplicidade.
    Retorna um SET de IDs para busca rápida.
    """
    try:
        # Pega todos os valores da primeira coluna (ID_Unico)
        ids = sheet.col_values(1)
        # Remove o cabeçalho se existir e converte para set para busca O(1)
        if ids and ids[0] == "ID_Unico":
            return set(ids[1:])
        return set(ids)
    except Exception as e:
        st.warning(f"Não foi possível ler histórico de IDs: {e}")
        return set()

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
                st.error(f"❌ Erro download final: {e}")
                return False

def analisar_video_groq(video_path, status_box):
    # Verifica chave correta no secrets
    if "groq" in st.secrets and "api_key" in st.secrets["groq"]:
        api_key = st.secrets["groq"]["api_key"]
    else:
        # Fallback para formato antigo se existir
        api_key = st.secrets.get("groq_api_key")
        
    client_groq = Groq(api_key=api_key)
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
        
        Retorne JSON: {{ "ganchos_verbais": "..." }}
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
            "ganchos_verbais": resultado_ia.get("ganchos_verbais", "-")
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
    # Fallback proxy para contas free
    # run_input["proxy"] = {"useApifyProxy": True, "apifyProxyGroups": []} 

    container_log.info(f"📡 Apify: Lendo @{perfil}...")

    try:
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        if not run: return []

        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        container_log.info(f"📦 {len(dataset_items)} itens encontrados. Filtrando...")
        
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
        
        for item in dataset_items:
            tipo = item.get('type', '')
            # Filtra apenas vídeos/reels
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
            # Tenta achar URL em posts filhos (carrossel) ou alternativos
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
                "pk": str(item.get('id')), # ID ÚNICO
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

# --- BOTÃO PRINCIPAL ---
if st.button("🚀 Iniciar Análise (Apify + Groq)", type="primary"):
    
    # 1. Conecta Planilha e Carrega IDs (CACHE)
    sheet = conectar_sheets()
    if not sheet: st.stop()
    
    st.toast("Verificando banco de dados...", icon="💾")
    ids_no_banco = carregar_ids_existentes(sheet)
    st.write(f"📊 {len(ids_no_banco)} vídeos já cadastrados no banco.")

    timestamp_coleta = datetime.now().strftime("%d/%m/%Y")
    
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
            
        # Ordena por visualizações
        top_final = sorted(videos, key=lambda x: x['views'], reverse=True)[:TOP_VIDEOS]
        st.write(f"🏆 Top {len(top_final)} vídeos identificados.")
        
        barra = st.progress(0)
        
        for i, v in enumerate(top_final):
            rank = i + 1
            id_video = v['pk']
            
            # --- VERIFICAÇÃO DE ID ÚNICO (REGRA DE OURO) ---
            if id_video in ids_no_banco:
                with st.status(f"⏩ [Top {rank}] Vídeo já existe no banco (ID: {id_video})", state="complete", expanded=False):
                    st.write("Pulando download e transcrição.")
                barra.progress((i + 1) / len(top_final))
                continue
            
            # Se não existe, processa
            ia_data = {"transcricao": "", "ganchos_verbais": ""}
            
            if rank <= TOP_ANALISE_IA:
                with st.status(f"⭐ [Top {rank}] Processando Novo Vídeo ({v['views']} views)...", expanded=True) as status:
                    
                    caminho_video_temp = os.path.join('temp_videos_groq', f"{id_video}.mp4")
                    
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

            # --- SALVA NO SHEETS (ESTRUTURA CORRETA) ---
            # Ordem: ID, Data Coleta, Perfil, Data Post, URL, Views, Likes, Comments, Transcricao, Gancho, Legenda
            nova_linha = [
                id_video,                      # ID_Unico
                timestamp_coleta,              # Data_Coleta
                f"@{perfil}",                  # Perfil
                v['data_str'],                 # Data_Postagem
                v['link'],                     # URL_Original
                v['views'],                    # Views
                v['likes'],                    # Likes
                v['comments'],                 # Comments
                ia_data.get('transcricao', ''),# Transcricao_Whisper
                ia_data.get('ganchos_verbais', ''), # Gancho_Verbal
                v['caption']                   # Legenda
            ]
            
            try:
                sheet.append_row(nova_linha)
                ids_no_banco.add(id_video) # Adiciona no cache local para não duplicar no mesmo loop
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