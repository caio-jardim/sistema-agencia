import streamlit as st
import os
import time
from moviepy.editor import VideoFileClip

# --- IMPORTAÇÃO DOS MÓDULOS ---
from modules.auth import check_password
from modules.database import conectar_sheets, verificar_existencia_db, salvar_no_db
from modules.instagram import get_instagram_data_apify, download_file
from modules.ai_processor import agente_tempestade_ideias, agente_arquiteto_carrossel, transcrever_audio_groq
from modules.youtube_utils import pegar_dados_youtube_apify 

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador de Carrosséis", page_icon="🎠", layout="wide")
st.title("🎠 Gerador de Carrosséis")
st.markdown("Transforme qualquer conteúdo (YouTube, Reels ou Post) em estruturas validadas.")
st.markdown("---")

# --- LOGIN ---
if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    st.info("O sistema usa Apify/Cobalt para evitar bloqueios automaticamente.")

# --- INPUTS ---
col_tipo, col_foco = st.columns([1, 1])

with col_tipo:
    tipo_conteudo = st.radio("Origem:", ["YouTube", "Reels (Instagram)", "Carrossel (Instagram)"])

with col_foco:
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
        st.session_state['url_ref'] = url_input 
        st.session_state['ideia_ativa'] = None 
        
        status = st.status("Iniciando processo...", expanded=True)
        texto_extraido = ""
        
        # 1. CONEXÃO COM BANCO DE DADOS
        gs_client = conectar_sheets() 
        
        # Define o nome correto da aba baseado no tipo
        if tipo_conteudo == "YouTube":
            aba_alvo = "Youtube"
        elif tipo_conteudo == "Carrossel (Instagram)":
            aba_alvo = "carrossel" # <--- ABA NOVA
        else:
            aba_alvo = "instagram" # Reels
            
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
            
            # --- YOUTUBE ---
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
                    st.error("Não foi possível extrair dados.")

            # --- REELS (INSTAGRAM) ---
            elif tipo_conteudo == "Reels (Instagram)":
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
                    v_url = data.get('videoUrl') or data.get('video_url')
                    if v_url and download_file(v_url, "temp.mp4"):
                        try:
                            vc = VideoFileClip("temp.mp4")
                            vc.audio.write_audiofile("temp.mp3", verbose=False, logger=None)
                            vc.close()
                            status.write("👂 Transcrevendo áudio...")
                            texto_extraido = transcrever_audio_groq("temp.mp3")
                        except Exception as e: 
                            st.error(f"Erro áudio: {e}")
                        finally:
                            if os.path.exists("temp.mp4"): os.remove("temp.mp4")
                            if os.path.exists("temp.mp3"): os.remove("temp.mp3")

            # --- CARROSSEL (INSTAGRAM) - NOVO ---
            elif tipo_conteudo == "Carrossel (Instagram)":
                status.write("🕵️ Lendo Carrossel (Apify)...")
                data = get_instagram_data_apify(url_input)
                
                if data:
                    # Monta o objeto para salvar
                    dados_para_salvar = {
                        "id_unico": data.get('id', ''),
                        "perfil": data.get('ownerUsername', ''),
                        "data_postagem": data.get('timestamp', '')[:10],
                        "url": url_input,
                        "views": data.get('viewCount') or data.get('playCount', 0), # As vezes vem viewCount em posts
                        "likes": data.get('likesCount', 0),
                        "comments": data.get('commentsCount', 0),
                        "caption": data.get('caption', '') 
                    }
                    
                    # Lógica de Extração de Texto do Carrossel
                    # A Groq não vê imagem, então montamos um "Roteiro de Leitura"
                    status.write("📑 Extraindo textos dos slides...")
                    
                    # 1. Pega a legenda
                    txt_final = f"=== LEGENDA DO POST ===\n{data.get('caption', '')}\n\n"
                    txt_final += "=== CONTEÚDO DOS SLIDES (TEXTO ALTERNATIVO/OCR) ===\n"
                    
                    # 2. Itera sobre os slides (childPosts)
                    slides = data.get('childPosts', [])
                    if not slides:
                        # As vezes o carrossel vem sem childPosts se for imagem única ou erro
                        # Tenta pegar displayUrl ou alt da imagem principal
                        alt = data.get('alt') or "Imagem única sem descrição."
                        txt_final += f"Slide Único: {alt}"
                    else:
                        for i, slide in enumerate(slides):
                            # Tenta pegar Alt Text ou Descrição
                            texto_slide = slide.get('alt') or slide.get('description') or slide.get('accessibilityCaption')
                            if not texto_slide:
                                texto_slide = "[Imagem sem texto detectado pela API]"
                            
                            txt_final += f"SLIDE {i+1}: {texto_slide}\n"
                    
                    texto_extraido = txt_final

            # 4. SALVAR NO BANCO
            if texto_extraido and gs_client:
                dados_para_salvar["transcricao"] = texto_extraido
                
                # Reels tem gancho, Carrossel não necessariamente (salva direto na col Transcricao_Carrossel)
                if aba_alvo == "instagram":
                    dados_para_salvar["gancho_verbal"] = texto_extraido[:100] + "..."
                
                status.write("💾 Salvando na Planilha...")
                salvar_no_db(gs_client, aba_alvo, dados_para_salvar)

        # 5. GERAÇÃO DAS IDEIAS (IA)
        if texto_extraido:
            st.session_state['conteudo_base'] = texto_extraido
            
            status.write(f"🧠 Gerando conceitos (Modo: {foco_analise})...")
            ideias = agente_tempestade_ideias(texto_extraido, modo=foco_analise)
            
            if ideias:
                st.session_state['ideias_geradas'] = ideias
                status.update(label="Sucesso! Ideias Geradas.", state="complete", expanded=False)
            else:
                status.update(label="Erro na IA (JSON)", state="error")
        else:
            status.update(label="Falha na extração ou texto vazio", state="error")

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

# --- EDITOR DE ROTEIRO ---
if 'ideia_ativa' in st.session_state and st.session_state['ideia_ativa']:
    st.markdown("---")
    st.info(f"🏗️ Projetando Carrossel: **{st.session_state['ideia_ativa'].get('titulo')}**")
    
    # Gera o roteiro se ainda não existir
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
        # Metadados
        meta = roteiro.get('meta_dados', {})
        if meta:
            c1, c2, c3 = st.columns(3)
            c1.metric("Complexidade", meta.get('complexidade_detectada', '-'))
            c2.metric("Slides", meta.get('total_slides', '-'))
            c3.caption(f"Tema: {meta.get('tema', '-')}")
            
        st.markdown("### ✏️ Editor de Slides")
        st.caption("Faça seus ajustes abaixo. O texto é salvo automaticamente.")
        
        # ID ÚNICO PARA O CACHE
        unique_id = str(hash(st.session_state['ideia_ativa']['titulo']))
        
        slides = roteiro['carrossel']
        for i, slide in enumerate(slides):
            with st.container(border=True):
                col_meta, col_edit = st.columns([1, 3])
                
                with col_meta:
                    st.markdown(f"#### Slide {slide.get('painel', i+1)}")
                    st.caption(f"**Fase:** {slide.get('fase', '-')}")
                    
                    with st.expander("Engenharia (Nota)"):
                        st.info(slide.get('nota_engenharia', '-'))

                with col_edit:
                    novo_texto = st.text_area(
                        label="Conteúdo do Slide (Editável)",
                        value=slide.get('texto', ''),
                        height=150,
                        key=f"slide_edit_{unique_id}_{i}"
                    )
                    st.session_state['roteiro_final']['carrossel'][i]['texto'] = novo_texto

        # --- ÁREA DE EXPORTAÇÃO ---
        st.markdown("---")
        st.subheader("📋 Área de Transferência (Docs)")
        
        titulo_final = meta.get('tema', 'Carrossel')
        link_ref = st.session_state.get('url_ref', 'Link não salvo')
        
        texto_exportacao = f"CARROSSEL: {titulo_final}\n"
        texto_exportacao += f"Referência: {link_ref}\n\n"
        
        for slide in st.session_state['roteiro_final']['carrossel']:
            num = slide.get('painel', '#')
            txt = slide.get('texto', '')
            texto_exportacao += f"SLIDE {num}:\n{txt}\n\n"
            
        st.code(texto_exportacao, language="text")
        st.success("👆 Clique no ícone de copiar no canto superior direito do bloco acima.")

    if st.button("Fechar Projeto", type="secondary"):
        del st.session_state['ideia_ativa']
        st.session_state['roteiro_final'] = None
        st.rerun()