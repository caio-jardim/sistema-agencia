import streamlit as st
from modules.auth import check_password
from modules.trends import gerar_hypes_gemini, escrever_roteiro_groq

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gerador de Hypes", page_icon="🔥", layout="wide")
st.title("🔥 Gerador de Pautas Virais")
st.markdown("---")

# --- LOGIN ---
if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 Radar de Tendências")
    nicho = st.text_input("Seu Nicho", "Holding Familiar")
    
    janela_tempo = st.selectbox("Janela de Tempo", ["Hoje", "Última Semana"], index=0)
    
    # NOVIDADE: Escolha do Tom
    tom_voz = st.selectbox(
        "Estilo do Conteúdo", 
        ["Polêmico (Estilo Pablo Marçal)", "Educativo (Professor)", "Analítico (Economista)", "Motivacional"]
    )
    
    st.markdown("---")
    st.header("🕵️ Restrições")
    observacoes = st.text_area("Obs:", placeholder="Ex: Não falar de política partidária...", height=100)

# --- BOTÃO DE AÇÃO ---
col1, col2 = st.columns([3, 1])
with col2:
    btn_gerar = st.button("🚀 Buscar Hypes", type="primary", use_container_width=True)

# --- LÓGICA DE GERAÇÃO (SESSION STATE) ---
if btn_gerar:
    if not nicho:
        st.warning("Preencha o nicho.")
    else:
        with st.spinner(f"🔍 O Gemini está varrendo a internet por hypes para {nicho}..."):
            # Chama a função do módulo trends.py
            pautas = gerar_hypes_gemini(nicho, janela_tempo, tom_voz, observacoes)
            
            if pautas:
                st.session_state['pautas_hype'] = pautas
                st.session_state['roteiro_hype_ativo'] = None
            else:
                st.error("O Gemini não retornou pautas válidas. Tente novamente.")

# --- EXIBIÇÃO DOS CARDS (GRID LAYOUT) ---
if 'pautas_hype' in st.session_state:
    st.markdown("### 📋 Tópicos em Alta Identificados")
    
    pautas = st.session_state['pautas_hype']
    
    # Cria uma grid de 2 colunas para ficar mais bonito
    cols = st.columns(2)
    
    for i, pauta in enumerate(pautas):
        # Alterna entre coluna 0 e 1
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"#### {i+1}. {pauta.get('titulo', 'Sem Título')}")
                st.caption(f"🔥 **Hype:** {pauta.get('hype')}")
                st.info(f"🗣️ **Gancho:** {pauta.get('gancho')}")
                
                if st.button("✨ Escrever Roteiro", key=f"btn_h_{i}", use_container_width=True):
                    st.session_state['pauta_hype_selecionada'] = pauta
                    st.rerun()

# --- ROTEIRO FINAL ---
if 'pauta_hype_selecionada' in st.session_state:
    pauta = st.session_state['pauta_hype_selecionada']
    
    st.markdown("---")
    st.subheader(f"🎬 Roteiro: {pauta['titulo']}")
    
    # Verifica se já gerou o texto para não gastar API a cada refresh
    if st.session_state.get('roteiro_hype_texto') is None or st.session_state.get('last_pauta_title') != pauta['titulo']:
        with st.spinner("✍️ A Groq está escrevendo o roteiro..."):
            texto_roteiro = escrever_roteiro_groq(pauta, nicho, tom_voz, observacoes)
            st.session_state['roteiro_hype_texto'] = texto_roteiro
            st.session_state['last_pauta_title'] = pauta['titulo']
    
    # Exibe o roteiro
    with st.container(border=True):
        st.markdown(st.session_state['roteiro_hype_texto'])
    
    if st.button("Fechar"):
        del st.session_state['pauta_hype_selecionada']
        st.rerun()