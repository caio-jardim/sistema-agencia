import streamlit as st
from modules.auth import check_password
from modules.ui import carregar_css

# --- CONFIGURAÇÃO ---
st.set_page_config(
    page_title="E21 STUDIO",
    page_icon="🚀",
    layout="wide"
)

# 1. Injeta o CSS (Fontes, sombras, botões arredondados)
carregar_css()

# 2. Sistema de Login (Modular)
if not check_password():
    st.stop()

# --- HEADER (CABEÇALHO COM HTML/CSS) ---
st.markdown("""
    <div style="text-align: center; padding: 2rem 0; margin-bottom: 2rem;">
        <h1 style="font-size: 3.5rem; margin-bottom: 0.5rem; background: -webkit-linear-gradient(45deg, #F63366, #FF8E53); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Agência OS
        </h1>
        <p style="font-size: 1.2rem; color: #555;">
            Sistema Central de Inteligência Artificial e Automação
        </p>
    </div>
""", unsafe_allow_html=True)

# --- DASHBOARD (GRID DE FERRAMENTAS) ---
st.markdown("### 🛠️ Hub de Ferramentas")
st.markdown("Selecione uma ferramenta no menu lateral para começar.")

# Layout em 3 colunas para parecer um "Software"
col1, col2, col3 = st.columns(3)

# CARD 1: INSTAGRAM
with col1:
    with st.container(border=True):
        st.markdown("### 📊 Viral Analyzer")
        st.caption("Página 01")
        st.markdown("""
        **Função:** Analisa perfis do Instagram, baixa Reels e extrai métricas.
        
        * 🕵️ Monitoramento de Concorrentes
        * 📈 Extração de Top Posts
        * 💾 Banco de Dados Automático
        """)
        st.info("Status: ✅ Operacional")

# CARD 2: VÍDEO DIÁRIO (HYPES)
with col2:
    with st.container(border=True):
        st.markdown("### 🔥 Radar de Hypes")
        st.caption("Página 03")
        st.markdown("""
        **Função:** Varre a internet em busca de tendências e cria conexões com seu nicho.
        
        * 🌍 Notícias em Tempo Real (Gemini)
        * ✍️ Roteiros Polêmicos ou Educativos
        * ⚡ Newsjacking Automático
        """)
        st.info("Status: ✅ Operacional")

# CARD 3: GERADOR DE CARROSSEL
with col3:
    with st.container(border=True):
        st.markdown("### 🎠 Fábrica de Carrosséis")
        st.caption("Página 04")
        st.markdown("""
        **Função:** Transforma vídeos ou links em carrosséis de retenção.
        
        * 🧠 IA Estrategista (Viral vs Vendas)
        * 🏗️ Arquiteto de Slides
        * 📥 Download YouTube/Insta Integrado
        """)
        st.info("Status: ✅ Operacional")

# --- ÁREA DE NOTIFICAÇÕES / ATALHOS ---
st.markdown("---")
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown("#### 📢 Atualizações do Sistema")
    st.success("24/01: Módulo 'Gerador de Carrossel' atualizado com IA de Vendas (Mentor).")
    st.info("23/01: Integração Apify + Cobalt para downloads sem bloqueio.")

with c2:
    st.markdown("#### 🔒 Segurança")
    st.caption(f"Logado como: **Equipe E21**")
    if st.button("Sair / Logout"):
        del st.session_state["password_correct"]
        st.rerun()