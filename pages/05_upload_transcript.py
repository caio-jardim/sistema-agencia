import streamlit as st
import time
import os

# --- IMPORTS DA ESTRUTURA ANTIGA ---
from modules.auth import check_password
from modules.ui import carregar_css
from modules.ai_processor import transcrever_arquivo_upload_groq

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Transcritor Pro", page_icon="🎙️", layout="wide")

# 1. Injeta CSS
carregar_css()

# 2. Login
if not check_password():
    st.stop()

# --- HEADER MANUAL (Já que não migramos o componente de header ainda) ---
st.markdown("""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
        <h1 style="margin:0;">Transcritor Studio</h1>
    </div>
    <p style="color: #666; font-size: 1.1rem;">Transforme áudios longos em texto em segundos (Via Groq/Whisper v3)</p>
    <hr>
""", unsafe_allow_html=True)

# --- INTERFACE ---
st.markdown("""
<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
    <strong>🚀 Diferença de Velocidade:</strong><br>
    Seu PC: ~1 hora (para 20min de áudio)<br>
    Este Sistema: <strong style="color: #F63366;">~30 segundos</strong> (para 20min de áudio)
</div>
""", unsafe_allow_html=True)

# Upload
uploaded_file = st.file_uploader(
    "Arraste seu arquivo de áudio ou vídeo aqui", 
    type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"],
    help="Limite sugerido: 25MB (aprox. 20 a 30 min de áudio dependendo da qualidade)."
)

if uploaded_file is not None:
    # Exibe detalhes do arquivo
    tamanho_mb = uploaded_file.size / 1e6
    st.info(f"📁 Arquivo: **{uploaded_file.name}** ({tamanho_mb:.2f} MB)")

    # Aviso de limite da API
    if tamanho_mb > 25:
        st.warning("⚠️ Atenção: Este arquivo é maior que 25MB. A API pode rejeitar. Se falhar, tente comprimir o áudio antes.")

    # Botão de Ação
    if st.button("⚡ Iniciar Transcrição Turbo", type="primary"):
        start_time = time.time()
        
        with st.status("Processando áudio em alta velocidade...", expanded=True) as status:
            st.write("📤 Enviando para processamento na Nuvem (LPU)...")
            
            # Chama a função que adicionamos no passo 1
            texto_final = transcrever_arquivo_upload_groq(uploaded_file)
            
            if texto_final:
                end_time = time.time()
                tempo_total = end_time - start_time
                
                status.update(label=f"✅ Concluído em {tempo_total:.2f} segundos!", state="complete", expanded=False)
                
                # --- EXIBIÇÃO DO RESULTADO ---
                st.markdown("### 📝 Transcrição:")
                st.text_area("Resultado", value=texto_final, height=400)
                
                # --- BOTÃO DE DOWNLOAD ---
                st.download_button(
                    label="📥 Baixar Transcrição (.txt)",
                    data=texto_final,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}_TRANSCRICAO.txt",
                    mime="text/plain"
                )
            else:
                status.update(label="❌ Falha na transcrição", state="error")