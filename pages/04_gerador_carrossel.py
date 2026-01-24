import streamlit as st
import os
import time
from moviepy.editor import VideoFileClip

# --- IMPORTAÇÃO DOS MÓDULOS (A Mágica da Organização) ---
from modules.auth import check_password
from modules.database import conectar_sheets, verificar_existencia_db, salvar_no_db
from modules.instagram import get_instagram_data_apify, download_file
from modules.ai_processor import agente_tempestade_ideias, agente_arquiteto_carrossel, transcrever_audio_groq
from modules.youtube_utils import pegar_dados_youtube_apify 

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador de Carrosséis", page_icon="🎠", layout="wide")
st.title("🎠 Gerador de Carrosséis: Método Tempestade")
st.markdown("Transforme qualquer conteúdo (YouTube, Reels ou Post) em estruturas validadas.")
st.markdown("---")

# --- LOGIN ---
if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    st.info("O sistema usa Apify/Cobalt para contornar bloqueios automaticamente.")

# --- INPUTS ---
col_tipo, col_foco = st.columns([1, 1])

with col_tipo:
    tipo_conteudo = st.radio("Origem:", ["YouTube", "Reels (Instagram)", "Carrossel (Instagram)"])

with col_foco:
    # SELETOR DE MODO (Viral vs Vendas)
    foco_analise = st.radio(
        "Foco da IA:", 
        ["Conteúdo (Viral)", "Vendas (Mentor)"], 
        help="Viral: Foca em retenção e topo de funil.\nVendas: Foca em autoridade, quebra de objeção e fundo de funil."
    )

url_input = st.text_input(f"Cole o link do {tipo_conteudo}:", placeholder="https://...")

# --- BOTÃO PRINCIPAL ---
if st.button("⚡ Analisar e Gerar Conceitos", type="primary"):
    if not url_input:
        st.warning("Insira um link.")
    else:
        # Reset de estados
        st.session_state['conteudo_base'] = None 
        st.session_state['ideias_geradas'] = None
        st.session_state['roteiro_final'] = None
        
        status = st.status("Iniciando processo...", expanded=True)
        texto_extraido = ""
        
        # 1. CONEXÃO COM BANCO DE DADOS
        gs_client = conectar_sheets() # Retorna a aba, mas usamos o .spreadsheet dentro das funcoes
        
        aba_alvo = "Youtube" if tipo_conteudo == "YouTube" else "instagram"
        transcricao_db = None
        
        # 2. VERIFICA SE JÁ EXISTE NO BANCO
        if gs_client:
            status.write(f"🔎 Verificando DB: '{aba_alvo}'...")
            transcricao_db = verificar_existencia_db(gs_client, aba_alvo, url_input)
        
        if transcricao_db:
            status.write("✅ Encontrado no Banco de Dados!")
            texto_extraido = transcricao_db
            time.sleep(1)
        else:
            status.write("⚠️ Novo link. Iniciando extração...")
            dados_para_salvar = {}
            
            # --- EXTRAÇÃO YOUTUBE (MODULAR) ---
            if tipo_conteudo == "YouTube":
                yt_data = pegar_dados_youtube_apify(url_input)
                
                if yt_data and yt_data.get('sucesso'):
                    texto_extraido = yt_data.get('transcricao', '')
                    dados_para_salvar = {
                        "id_unico": yt_data.get('id_unico'),
                        "perfil": yt_data.get('canal'),
                        "data_postagem": yt_data.get('data_post'),
                        "url": url_input,
                        "views": yt_data.get('views'),
                        "likes": yt_data.get('likes'),
                        "comments": 0,
                        "caption": yt_data.get('description', '')
                    }
                else:
                    status.update(label="Falha no YouTube", state="error")
                    st.error("Não foi possível extrair dados do YouTube.")

            # --- EXTRAÇÃO INSTAGRAM (MODULAR) ---
            elif tipo_conteudo in ["Reels (Instagram)", "Carrossel (Instagram)"]:
                status.write("🕵️ Acessando Apify (Instagram)...")
                data = get_instagram_data_apify(url_input)
                
                if data:
                    dados_para_salvar = {
                        "id_unico": data.get('id', ''),
                        "perfil": data.get('ownerUsername', ''),
                        "data_postagem": data.get('timestamp', '')[:10],
                        "url": url_input,
                        "views": data.get('videoViewCount') or data.get('playCount', 0),
                        "likes": data.get('likesCount', 0),
                        "comments": data.get('commentsCount', 0),
                        "caption": data.get('caption', '') 
                    }

                    if tipo_conteudo == "Reels (Instagram)":
                        v_url = data.get('videoUrl') or data.get('video_url')
                        # Baixa vídeo temporário para transcrever
                        if v_url and download_file(v_url, "temp.mp4"):
                            try:
                                vc = VideoFileClip("temp.mp4")
                                vc.audio.write_audiofile("temp.mp3", verbose=False, logger=None)
                                vc.close()
                                status.write("👂 Transcrevendo áudio...")
                                texto_extraido = transcrever_audio_groq("temp.mp3")
                            except Exception as e: 
                                st.error(f"Erro processamento áudio: {e}")
                            finally:
                                if os.path.exists("temp.mp4"): os.remove("temp.mp4")
                                if os.path.exists("temp.mp3"): os.remove("temp.mp3")
                    
                    elif tipo_conteudo == "Carrossel (Instagram)":
                        cap = data.get('caption') or ""
                        alts = [c.get('alt') for c in (data.get('childPosts') or []) if c.get('alt')]
                        texto_extraido = f"LEGENDA:\n{cap}\nVISUAL:\n{' '.join(alts)}"

            # 4. SALVAR NO BANCO
            if texto_extraido and gs_client:
                dados_para_salvar["transcricao"] = texto_extraido
                if aba_alvo == "instagram":
                    dados_para_salvar["gancho_verbal"] = texto_extraido[:100] + "..."
                
                status.write("💾 Salvando na Planilha...")
                salvar_no_db(gs_client, aba_alvo, dados_para_salvar)

        # 5. GERAÇÃO DAS IDEIAS (IA)
        if texto_extraido:
            st.session_state['conteudo_base'] = texto_extraido
            
            # AQUI ACONTECE A MÁGICA DO BOTÃO NOVO
            status.write(f"🧠 Gerando conceitos (Modo: {foco_analise})...")
            ideias = agente_tempestade_ideias(texto_extraido, modo=foco_analise)
            
            if ideias:
                st.session_state['ideias_geradas'] = ideias
                status.update(label="Sucesso! Ideias Geradas.", state="complete", expanded=False)
            else:
                status.update(label="Erro na IA (JSON)", state="error")
        else:
            status.update(label="Falha na extração ou transcrição vazia", state="error")

# --- VISUALIZAÇÃO DOS RESULTADOS ---
if 'ideias_geradas' in st.session_state and st.session_state['ideias_geradas']:
    st.markdown("---")
    st.subheader(f"⛈️ Estruturas Identificadas ({foco_analise})")
    
    ideias = st.session_state['ideias_geradas']
    
    for i, ideia in enumerate(ideias):
        with st.container(border=True):
            col_txt, col_btn = st.columns([4, 1])
            
            with col_txt:
                st.markdown(f"### {i+1}. {ideia.get('titulo', 'Sem Título')}")
                st.caption(f"📐 **Estrutura:** {ideia.get('estrutura', '-')}")
                st.write(f"💡 {ideia.get('por_que_funciona', '-')}")
            
            with col_btn:
                st.write("")
                st.write("")
                if st.button("🎨 Gerar Carrossel", key=f"btn_car_{i}"):
                    st.session_state['ideia_ativa'] = ideia
                    st.session_state['roteiro_final'] = None 
                    st.rerun()

# --- GERAÇÃO DO ROTEIRO FINAL ---
if 'ideia_ativa' in st.session_state:
    st.markdown("---")
    st.info(f"🏗️ Projetando Carrossel: **{st.session_state['ideia_ativa'].get('titulo')}**")
    
    if st.session_state.get('roteiro_final') is None:
        with st.spinner("O Arquiteto está desenhando os slides..."):
            roteiro_json = agente_arquiteto_carrossel(
                st.session_state['ideia_ativa'], 
                st.session_state.get('conteudo_base', '')
            )
            st.session_state['roteiro_final'] = roteiro_json
            st.rerun()
            
    roteiro = st.session_state.get('roteiro_final')
    if roteiro and 'carrossel' in roteiro:
        meta = roteiro.get('meta_dados', {})
        if meta:
            c1, c2, c3 = st.columns(3)
            c1.metric("Complexidade", meta.get('complexidade_detectada', '-'))
            c2.metric("Slides", meta.get('total_slides', '-'))
            c3.caption(f"Tema: {meta.get('tema', '-')}")
            
        st.success("Projeto Finalizado! 👇")
        
        for slide in roteiro['carrossel']:
            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f"#### Painel {slide.get('painel', '#')}")
                    st.caption(f"**{slide.get('fase', 'Fase')}**")
                with c2:
                    st.code(slide.get('texto', ''), language="text")
                    st.info(slide.get('nota_engenharia', ''))
    
    if st.button("Fechar Projeto"):
        del st.session_state['ideia_ativa']
        st.session_state['roteiro_final'] = None
        st.rerun()