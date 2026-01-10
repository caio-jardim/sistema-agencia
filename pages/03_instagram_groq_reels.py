import streamlit as st
import time
import random
import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from instagrapi import Client
from datetime import datetime, timedelta, timezone
from groq import Groq
from moviepy.editor import VideoFileClip

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Analise Viral (Groq)", page_icon="⚡")

st.title("⚡ Analise Viral: Whisper + Groq")
st.markdown("---")

# --- CONFIGURAÇÕES LATERAIS ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=60)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=3)
    
    st.info("Este script usa Groq Whisper para transcrição completa.")

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
                "Views (Play)", "Likes", "Comentários", "Link", "Legenda",
                "Transcrição Completa (Whisper)", "Gancho Verbal (IA)"
            ])
        return sheet
    except Exception as e:
        st.error(f"Erro Sheets: {e}")
        return None

def analisar_video_groq(cl, pk_video, status_box):
    """
    Pipeline Completo: Download -> MP3 -> Whisper -> Llama 3
    """
    # Inicializa Groq com a chave segura
    client_groq = Groq(api_key=st.secrets["groq_api_key"])
    
    temp_folder = "temp_videos_groq"
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    caminho_video = os.path.join(temp_folder, f"{pk_video}.mp4")
    caminho_audio = os.path.join(temp_folder, f"{pk_video}.mp3")

    try:
        # --- PASSO 1: DOWNLOAD ---
        status_box.write("⬇️ Baixando vídeo do Instagram...")
        info_dict = cl.private_request(f"media/{pk_video}/info/")
        items = info_dict.get('items', [{}])[0]
        video_url = items.get('video_versions', [{}])[0].get('url')
        
        if not video_url: return {"transcricao": "Erro URL", "ganchos_verbais": "-"}

        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(caminho_video, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

        # --- PASSO 2: EXTRAÇÃO DE ÁUDIO ---
        status_box.write("🔊 Extraindo áudio (MoviePy)...")
        try:
            video_clip = VideoFileClip(caminho_video)
            video_clip.audio.write_audiofile(
                caminho_audio, 
                bitrate="32k", 
                verbose=False, 
                logger=None
            )
            video_clip.close()
        except Exception as e:
            return {"transcricao": "Erro Audio", "ganchos_verbais": "-"}

        # --- PASSO 3: TRANSCRIÇÃO (WHISPER) ---
        status_box.write("📝 Transcrevendo com Whisper Large v3...")
        with open(caminho_audio, "rb") as file:
            transcription = client_groq.audio.transcriptions.create(
                file=(caminho_audio, file.read()),
                model="whisper-large-v3", 
                response_format="text"
            )
        texto_transcrito_bruto = str(transcription)

        # --- PASSO 4: ANÁLISE (LLAMA 3) ---
        status_box.write("🧠 Analisando Gancho com Llama 3...")
        texto_para_analise = texto_transcrito_bruto[:6000] 

        prompt = f"""
        Abaixo está o começo da transcrição de um vídeo viral:
        "{texto_para_analise}"

        Sua tarefa: Identifique qual foi a frase exata usada no início (gancho) para prender a atenção.
        Retorne APENAS um JSON: {{ "ganchos_verbais": "A frase do gancho aqui" }}
        """
        
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, 
            response_format={"type": "json_object"}
        )

        resultado_ia = json.loads(completion.choices[0].message.content)

        # Limpeza
        if os.path.exists(caminho_video): os.remove(caminho_video)
        if os.path.exists(caminho_audio): os.remove(caminho_audio)

        return {
            "transcricao": texto_transcrito_bruto,
            "ganchos_verbais": resultado_ia.get("ganchos_verbais", "-")
        }

    except Exception as e:
        st.error(f"Erro no Processo IA: {e}")
        # Limpeza de emergência
        if os.path.exists(caminho_video): os.remove(caminho_video)
        if os.path.exists(caminho_audio): os.remove(caminho_audio)
        return {"transcricao": "Erro", "ganchos_verbais": "-"}


def pegar_dados_manuais(cl, user_id, dias, container_log):
    """Lógica de coleta adaptada"""
    items_coletados = []
    next_max_id = None
    data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    MAX_PAGINAS = 80
    
    container_log.info(f"📅 Data limite: {data_limite.strftime('%d/%m/%Y')}")

    pagina = 0
    while True:
        pagina += 1
        if pagina > MAX_PAGINAS: break

        try:
            params = {'count': 12}
            if next_max_id: params['max_id'] = next_max_id
            
            resultado = cl.private_request(f"feed/user/{user_id}/", params=params)
            items = resultado.get('items', [])
            next_max_id = resultado.get('next_max_id')
            
            if not items: break

            for item in items:
                ts = item.get('taken_at')
                data_post = datetime.fromtimestamp(ts, timezone.utc)
                
                if data_post < data_limite:
                    return items_coletados 
                
                if item.get('media_type') == 2:
                    views = item.get('play_count') or item.get('view_count', 0)
                    caption_obj = item.get('caption')
                    legenda = caption_obj.get('text', '') if caption_obj else ''
                    
                    items_coletados.append({
                        "pk": item.get('pk'),
                        "data_str": data_post.strftime("%d/%m/%Y"),
                        "views": views, 
                        "likes": item.get('like_count', 0),
                        "comments": item.get('comment_count', 0),
                        "link": f"https://www.instagram.com/p/{item.get('code')}/",
                        "caption": legenda[:300] + "..."
                    })
            
            if not next_max_id: break
            time.sleep(random.randint(2, 5)) 
                
        except Exception as e:
            container_log.warning(f"Erro leve no scan: {e}")
            break
            
    return items_coletados

# --- BOTÃO PRINCIPAL ---
if st.button("🚀 Iniciar Análise Groq", type="primary"):
    
    # 1. Login Instagram
    cl = Client()
    try:
        cl.login(st.secrets["instagram"]["user"], st.secrets["instagram"]["pass"])
        st.success("✅ Login no Instagram realizado!")
    except Exception as e:
        st.error(f"❌ Falha no Login: {e}")
        st.stop()

    # 2. Conexão Sheets
    sheet = conectar_sheets()
    if not sheet: st.stop()

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    for perfil in PERFIS_ALVO:
        st.subheader(f"🔍 @{perfil}")
        log_box = st.expander("Detalhes da Coleta", expanded=True)
        
        try:
            user_info = cl.user_info_by_username_v1(perfil)
            
            with log_box:
                videos = pegar_dados_manuais(cl, user_info.pk, DIAS_ANALISE, st)
            
            if not videos:
                st.warning("Nenhum vídeo encontrado.")
                continue

            top_final = sorted(videos, key=lambda x: x['views'], reverse=True)[:TOP_VIDEOS]
            st.write(f"🏆 Analisando Top {len(top_final)} vídeos.")
            
            rows = []
            barra = st.progress(0)
            
            for i, v in enumerate(top_final):
                rank = i + 1
                ia_data = {"transcricao": "", "ganchos_verbais": ""}
                
                # Análise IA (Groq)
                if rank <= TOP_ANALISE_IA:
                    # Cria um container visual bonito para o processo da IA
                    with st.status(f"⭐ [Top {rank}] Processando IA ({v['views']} views)...", expanded=True) as status:
                        ia_data = analisar_video_groq(cl, v['pk'], status)
                        status.update(label=f"✅ [Top {rank}] Concluído!", state="complete", expanded=False)
                    
                    # Mostra prévia da transcrição
                    if ia_data['transcricao'] and len(ia_data['transcricao']) > 10:
                        with st.expander(f"📄 Ver Transcrição Vídeo {rank}"):
                            st.caption(f"Gancho: {ia_data['ganchos_verbais']}")
                            st