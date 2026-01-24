import streamlit as st
import os
import time
from datetime import datetime

# --- IMPORTAÇÃO DOS MÓDULOS ---
from modules.auth import check_password
from modules.database import conectar_sheets, carregar_ids_existentes, salvar_linha_instagram
from modules.instagram import pegar_dados_apify, baixar_video_with_retry
from modules.ai_processor import analisar_video_groq

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Viral Analyzer", page_icon="⚡")
st.title("⚡ Viral Analyzer: Apify + Groq Whisper")
st.markdown("---")

# --- LOGIN ---
if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    perfis_input = st.text_area("Perfis (separe por vírgula)", "rodrigojanesbraga")
    PERFIS_ALVO = [x.strip() for x in perfis_input.split(',') if x.strip()]
    DIAS_ANALISE = st.number_input("Dias para analisar", min_value=1, value=60)
    TOP_VIDEOS = st.number_input("Top Vídeos para salvar", min_value=1, value=5)
    TOP_ANALISE_IA = st.number_input("Analisar com IA (Top X)", min_value=0, value=5)

# --- EXECUÇÃO PRINCIPAL ---
if st.button("🚀 Iniciar Análise", type="primary"):
    
    # 1. Banco de Dados
    sheet = conectar_sheets()
    if not sheet: st.stop()
    
    st.toast("Verificando banco de dados...", icon="💾")
    ids_existentes = carregar_ids_existentes(sheet)
    st.write(f"📊 {len(ids_existentes)} vídeos já cadastrados.")

    timestamp_coleta = datetime.now().strftime("%d/%m/%Y") # <--- AQUI ESTÁ A DEFINIÇÃO CORRETA
    
    if not os.path.exists('temp_videos_groq'): os.makedirs('temp_videos_groq')

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
            id_video = v['pk']
            
            # 2. Verificação de Cache
            if id_video in ids_existentes:
                with st.status(f"⏩ [Top {rank}] Já existe no banco (ID: {id_video})", state="complete", expanded=False):
                    st.write("Pulando...")
                barra.progress((i + 1) / len(top_final))
                continue
            
            # 3. Processamento IA
            ia_data = {"transcricao": "", "ganchos_verbais": ""}
            
            if rank <= TOP_ANALISE_IA:
                with st.status(f"⭐ [Top {rank}] Analisando ({v['views']} views)...", expanded=True) as status:
                    caminho_temp = os.path.join('temp_videos_groq', f"{id_video}.mp4")
                    
                    status.write("⬇️ Baixando...")
                    if baixar_video_with_retry(v['download_url'], caminho_temp):
                        ia_data = analisar_video_groq(caminho_temp, status)
                        if os.path.exists(caminho_temp): os.remove(caminho_temp)
                        status.update(label="✅ IA Concluída!", state="complete", expanded=False)
                    else:
                        status.update(label="❌ Erro Download", state="error")
                        ia_data["transcricao"] = "Erro Download"

            # 4. Salvar
            nova_linha = [
                id_video, 
                timestamp_coleta, # <--- CORRIGIDO AQUI (antes estava só 'timestamp')
                f"@{perfil}", 
                v['data_str'], 
                v['link'],
                v['views'], 
                v['likes'], 
                v['comments'],
                ia_data.get('transcricao', ''), 
                ia_data.get('ganchos_verbais', ''), 
                v['caption']
            ]
            
            if salvar_linha_instagram(sheet, nova_linha):
                ids_existentes.add(id_video)
                st.toast(f"Top {rank} salvo!", icon="💾")

            barra.progress((i + 1) / len(top_final))
        
        time.sleep(1)

    # Limpeza
    try:
        if os.path.exists('temp_videos_groq'):
            for f in os.listdir('temp_videos_groq'): os.remove(os.path.join('temp_videos_groq', f))
            os.rmdir('temp_videos_groq')
    except: pass

    st.balloons()
    st.success("🏁 Finalizado!")