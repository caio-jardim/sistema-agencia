import streamlit as st
import time
import random
import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from instagrapi import Client
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Analise Visual (Gemini)", page_icon="👁️")

st.title("👁️ Analise Visual: Gemini Vision")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=15)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=1)
    
    st.info("Este robô usa a visão do Gemini para analisar ganchos visuais e verbais.")

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
            # Cabeçalho atualizado com LEGENDA
            sheet.append_row([
                "Data Coleta", "Perfil", "Janela", "Rank", "Data Post", 
                "Views (Play)", "Likes", "Comentários", "Link", "Legenda",
                "Conteúdo (IA)", "Gancho Verbal (IA)", "Gancho Visual (IA)"
            ])
        return sheet
    except Exception as e:
        st.error(f"Erro Sheets: {e}")
        return None

def analisar_video_gemini(cl, pk_video, status_box):
    """Pipeline: Pega URL -> Baixa MP4 -> Envia pro Gemini"""
    
    # Configura Gemini com a chave segura
    genai.configure(api_key=st.secrets["gemini_api_key"])
    generation_config = {
      "temperature": 0.4,
      "top_p": 0.95,
      "top_k": 40,
      "max_output_tokens": 8192,
      "response_mime_type": "application/json",
    }
    
    temp_folder = "temp_videos_gemini"
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    caminho_arquivo = os.path.join(temp_folder, f"{pk_video}.mp4")

    try:
        # 1. Obter URL
        status_box.write("⬇️ Obtendo URL do vídeo...")
        info_dict = cl.private_request(f"media/{pk_video}/info/")
        items = info_dict.get('items', [{}])[0]
        video_versions = items.get('video_versions', [])
        
        if not video_versions:
             return {"transcricao": "Erro: URL não achada", "ganchos_verbais": "-", "ganchos_visuais": "-"}
             
        video_url = video_versions[0].get('url')

        # 2. Baixar
        status_box.write("⬇️ Baixando arquivo .mp4...")
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(caminho_arquivo, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        # 3. Enviar para IA
        status_box.write("♊ Enviando para o Gemini Vision...")
        video_file = genai.upload_file(path=caminho_arquivo)
        
        while video_file.state.name == "PROCESSING":
            time.sleep(1)
            video_file = genai.get_file(video_file.name)
            
        if video_file.state.name == "FAILED":
            return {"transcricao": "Erro Processamento IA", "ganchos_verbais": "-", "ganchos_visuais": "-"}

        prompt = """
        Analise este vídeo curto de Reels. Retorne um JSON exato com estas chaves:
        {
            "transcricao": "Resumo do que foi falado",
            "ganchos_verbais": "Frase exata usada no inicio para prender atenção",
            "ganchos_visuais": "O que acontece visualmente nos primeiros 3s que chama atenção"
        }
        """
        model = genai.GenerativeModel("gemini-2.0-flash", generation_config=generation_config)
        response = model.generate_content([video_file, prompt])
        
        # Limpeza
        genai.delete_file(video_file.name)
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
            
        return json.loads(response.text)

    except Exception as e:
        status_box.error(f"Erro IA: {e}")
        if os.path.exists(caminho_arquivo):
            try: os.remove(caminho_arquivo)
            except: pass
        return {"transcricao": "Erro", "ganchos_verbais": "-", "ganchos_visuais": "-"}

def pegar_dados_manuais(cl, user_id, dias, container_log):
    """Lógica de Coleta"""
    items_coletados = []
    next_max_id = None
    data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    MAX_PAGINAS = 80
    
    container_log.info(f"📅 Buscando posts desde: {data_limite.strftime('%d/%m/%Y')}")

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
                        "caption": legenda[:500] + "..." # Aumentei limite
                    })
            
            if not next_max_id: break
            time.sleep(random.randint(2, 5)) 
                
        except Exception as e:
            container_log.warning(f"Erro leve no scan: {e}")
            break
            
    return items_coletados

# --- BOTÃO DE AÇÃO ---
if st.button("🚀 Iniciar Análise Gemini", type="primary"):
    
    # 1. Login
    cl = Client()
    try:
        cl.login(st.secrets["instagram"]["user"], st.secrets["instagram"]["pass"])
        st.success("✅ Login Instagram OK")
    except Exception as e:
        st.error(f"❌ Falha Login: {e}")
        st.stop()

    # 2. Sheets
    sheet = conectar_sheets()
    if not sheet: st.stop()

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    for perfil in PERFIS_ALVO:
        st.subheader(f"🔍 @{perfil}")
        log_box = st.expander("Logs da Coleta", expanded=True)
        
        try:
            user_info = cl.user_info_by_username_v1(perfil)
            
            with log_box:
                videos = pegar_dados_manuais(cl, user_info.pk, DIAS_ANALISE, st)
            
            if not videos:
                st.warning("Sem vídeos recentes.")
                continue

            top_final = sorted(videos, key=lambda x: x['views'], reverse=True)[:TOP_VIDEOS]
            st.write(f"🏆 Top {len(top_final)} vídeos selecionados.")
            
            rows = []
            barra = st.progress(0)
            
            for i, v in enumerate(top_final):
                rank = i + 1
                ia_data = {"transcricao": "", "ganchos_verbais": "", "ganchos_visuais": ""}
                
                # Análise IA
                if rank <= TOP_ANALISE_IA:
                    # Status Box bonita
                    with st.status(f"⭐ [Top {rank}] Analisando com Gemini...", expanded=True) as status:
                        ia_data = analisar_video_gemini(cl, v['pk'], status)
                        status.update(label=f"✅ [Top {rank}] Análise concluída!", state="complete", expanded=False)
                    
                    time.sleep(2) 

                rows.append([
                    timestamp, f"@{perfil}", f"{DIAS_ANALISE}d", f"{rank}º",
                    v['data_str'], v['views'], v['likes'], v['comments'], v['link'],
                    v['caption'],
                    ia_data.get('transcricao', ''),
                    ia_data.get('ganchos_verbais', ''),
                    ia_data.get('ganchos_visuais', '')
                ])
                
                barra.progress((i + 1) / len(top_final))
            
            sheet.append_rows(rows)
            st.toast(f"@{perfil} salvo na planilha!", icon="💾")
            time.sleep(5)

        except Exception as e:
            st.error(f"Erro crítico @{perfil}: {e}")
            continue

    # Limpeza final
    if os.path.exists("temp_videos_gemini"):
        try:
            for f in os.listdir("temp_videos_gemini"):
                os.remove(os.path.join("temp_videos_gemini", f))
            os.rmdir("temp_videos_gemini")
        except:
            pass

    st.balloons()
    st.success("🏁 FIM DO PROCESSO.")