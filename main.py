import streamlit as st
from modules.auth import check_password
from modules.ui import carregar_css

# --- CONFIGURAÇÃO ---
st.set_page_config(
    page_title="E21 Studio",
    page_icon="⚫", # Ícone da aba (favicon)
    layout="wide"
)

# 1. Injeta CSS Global
carregar_css()

# 2. Login
if not check_password():
    st.stop()

# --- ÍCONES SVG (DEFINIÇÃO) ---
# Ícones vetoriais elegantes na cor da marca
ICON_CHART = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 20V10M12 20V4M6 20V14" stroke="#F63366" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
ICON_RADAR = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="#F63366" stroke-width="2"/><path d="M12 8V12L15 15" stroke="#F63366" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
ICON_LAYERS = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#F63366" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 17L12 22L22 17" stroke="#F63366" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 12L12 17L22 12" stroke="#F63366" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

# --- HEADER ---
st.markdown("""
    <div style="text-align: center; padding: 3rem 0; margin-bottom: 2rem;">
        <h1 style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 4rem; letter-spacing: -2px; margin:0; color: #111;">
            E21 STUDIO
        </h1>
        <p style="font-family: 'Inter', sans-serif; font-size: 1rem; color: #666; letter-spacing: 2px; text-transform: uppercase; margin-top: 10px;">
            Operating System
        </p>
    </div>
""", unsafe_allow_html=True)

# --- DASHBOARD ---
# Layout em 3 colunas
c1, c2, c3 = st.columns(3)

# CARD 1: INSTAGRAM
with c1:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            {ICON_CHART}
            <h3 style="margin:0; font-size: 1.2rem;">Viral Analyzer</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="color: #555; font-size: 0.9rem; line-height: 1.6; margin-bottom: 20px;">
        Inteligência de dados para Instagram. Monitoramento de métricas e extração de padrões virais.
        </div>
        """, unsafe_allow_html=True)
        
        # CORREÇÃO: Removido o argumento 'icon' que causava erro
        st.page_link("pages/01_instagram_insights_reels.py", label="Acessar Módulo")

# CARD 2: RADAR
with c2:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            {ICON_RADAR}
            <h3 style="margin:0; font-size: 1.2rem;">Radar de Tendências</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="color: #555; font-size: 0.9rem; line-height: 1.6; margin-bottom: 20px;">
        Monitoramento de hypes em tempo real e criação de roteiros contextualizados (Newsjacking).
        </div>
        """, unsafe_allow_html=True)
        
        # CORREÇÃO: Removido o argumento 'icon'
        st.page_link("pages/03_video_diario.py", label="Acessar Módulo")

# CARD 3: CARROSSEL
with c3:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            {ICON_LAYERS}
            <h3 style="margin:0; font-size: 1.2rem;">Arquitetura de Conteúdo</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="color: #555; font-size: 0.9rem; line-height: 1.6; margin-bottom: 20px;">
        Transformação de mídias em carrosséis estruturados. IA com foco em Viralidade ou Vendas.
        </div>
        """, unsafe_allow_html=True)
        
        # CORREÇÃO: Removido o argumento 'icon'
        st.page_link("pages/04_gerador_carrossel.py", label="Acessar Módulo")

# --- FOOTER ---
st.markdown("---")
col_f1, col_f2 = st.columns([4, 1])

with col_f1:
    st.caption("E21 STUDIO INTERNAL SYSTEM v2.0")

with col_f2:
    if st.button("Logout", type="secondary", use_container_width=True):
        del st.session_state["password_correct"]
        st.rerun()