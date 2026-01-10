import streamlit as st
import time
import random
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from instagrapi import Client
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Viral Analyzer Pro", page_icon="📈")

st.title("📈 Viral Analyzer Pro + IA")
st.markdown("---")

# --- CONFIGURAÇÕES LATERAIS ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    
    # Input de perfis (separados por vírgula para facilitar)
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=15)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=1)
    
    st.warning("⚠️ O login no Instagram pode gerar desafios de segurança se rodado na nuvem.")

# --- FUNÇÕES ---

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # SEGURANÇA: Lê do secrets.toml
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        nome_planilha = "Conteudo" # Você pode colocar no secrets ou deixar fixo
        
        try:
            sheet = client.open(nome_planilha).sheet1
        except:
            sh = client.create(nome_planilha)
            sheet = sh.sheet1
            # Cria cabeçalho se for nova
            sheet.append_row([
                "Data Coleta", "Perfil", "Janela", "Rank", "Data Post", 
                "Views (Play)", "Likes", "Comentários", "Link", 
                "IA: Transcrição", "IA: Ganchos Virais", "IA: Ganchos Visuais"
            ])
        return sheet
    except Exception as e:
        st.error(f"Erro Sheets: {e}")
        return None

def analisar_video_com_gemini(video_path):
    """Envia vídeo para o Gemini e retorna JSON"""
    # Configura API Key do secrets
    genai.configure(api_key=st.secrets["gemini_api_key"])
    
    generation_config = {
      "temperature": 0.4,
      "top_p": 0.95,
      "top_k": 40,
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
            Você é um especialista em viralização de Reels. Analise este vídeo e retorne um JSON exato com estas chaves:
            {
                "transcricao": "Texto completo do que foi falado",
                "ganchos_verbais": "Quais frases exatas foram usadas no início para prender a atenção?",
                "ganchos_visuais": "O que acontece visualmente nos primeiros 3 segundos que prende o olho? (Mudança de cena, texto na tela, movimento)"
            }
            """
            
            model = genai.GenerativeModel("gemini-2.0-flash", generation_config=generation_config)
            response = model.generate_content([video_file, prompt])
            
            genai.delete_file(video_file.name)
            return json.loads(response.text)
            
    except Exception as e:
        st.error(f"Erro Gemini: {e}")
        return {"transcricao": "Erro API", "ganchos_verbais": "-", "ganchos_visuais": "-"}

def pegar_dados_manuais(cl, user_id, dias, container_log):
    """Lógica de coleta adaptada para interface visual"""
    items_coletados = []
    next_max_id = None
    data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    MAX_PAGINAS = 80
    
    container_log.info(f"📅 Buscando até: {data_limite.strftime('%d/%m/%Y')}")

    pagina = 0
    while True:
        pagina += 1
        if pagina > MAX_PAGINAS: break

        try:
            params = {'count': 12}
            if next_max_id: params['max_id'] = next_max_id
            
            # Request privado
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
                        "caption": legenda[:100] + "..."
                    })
            
            if not next_max_id: break
            time.sleep(random.randint(2, 5)) 
                
        except Exception as e:
            container_log.warning(f"Erro leve no scan: {e}")
            break
            
    return items_coletados

# --- BOTÃO PRINCIPAL ---
if st.button("🚀 Iniciar Análise", type="primary"):
    
    # 1. Login Instagram
    cl = Client()
    try:
        # Tenta login com credenciais seguras
        cl.login(st.secrets["instagram"]["user"], st.secrets["instagram"]["pass"])
        st.success("✅ Login no Instagram realizado!")
    except Exception as e:
        st.error(f"❌ Falha no Login: {e}")
        st.stop()

    # 2. Conexão Sheets
    sheet = conectar_sheets()
    if not sheet: st.stop()

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Criar pasta temp
    if not os.path.exists('temp_videos'):
        os.makedirs('temp_videos')

    # Loop Perfis
    for perfil in PERFIS_ALVO:
        st.subheader(f"🔍 @{perfil}")
        log_box = st.expander("Logs do Processamento", expanded=True)
        
        try:
            user_info = cl.user_info_by_username_v1(perfil)
            
            with log_box:
                videos = pegar_dados_manuais(cl, user_info.pk, DIAS_ANALISE, st)
            
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
                    st.info(f"⭐ Analisando vídeo Top {rank} ({v['views']} views) com IA...")
                    try:
                        # Download seguro
                        video_path = cl.video_download(v['pk'], folder='temp_videos')
                        
                        # Analisa
                        ia_data = analisar_video_com_gemini(video_path)
                        
                        # Limpa
                        if os.path.exists(video_path):
                            os.remove(video_path)
                            
                        # Delay de segurança
                        time.sleep(5)
                        
                    except Exception as e:
                        st.error(f"Erro na IA/Download: {e}")

                # Monta linha
                rows.append([
                    timestamp, f"@{perfil}", f"{DIAS_ANALISE}d", f"{rank}º",
                    v['data_str'], v['views'], v['likes'], v['comments'], v['link'],
                    ia_data.get('transcricao', ''),
                    ia_data.get('ganchos_verbais', ''),
                    ia_data.get('ganchos_visuais', '')
                ])
                
                # Atualiza barra
                barra.progress((i + 1) / len(top_final))

            # Salva no Sheets
            sheet.append_rows(rows)
            st.success(f"✅ Dados de @{perfil} salvos com sucesso!")
            time.sleep(5)

        except Exception as e:
            st.error(f"Erro crítico no perfil @{perfil}: {e}")
    
    # Limpeza final
    try:
        if os.path.exists('temp_videos'):
            for f in os.listdir('temp_videos'):
                os.remove(os.path.join('temp_videos', f))
            os.rmdir('temp_videos')
    except:
        pass

    st.balloons()
    st.success("🏁 Análise Geral Finalizada!")