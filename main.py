import streamlit as st

# Configuração da Página (Título e Ícone da aba)
st.set_page_config(
    page_title="Agência Marketing OS",
    page_icon="🚀",
    layout="wide"
)

# Título Principal
st.title("🚀 Agência Marketing OS")
st.markdown("### Bem-vindo ao Sistema Central de Automação")
st.markdown("---")

# Layout de Dashboard simples
col1, col2 = st.columns(2)

with col1:
    st.info("👈 **Use o menu lateral** para acessar as ferramentas.")
    st.markdown("""
    **Ferramentas Disponíveis:**
    
    1.  **Gerador de Roteiros:** Cria scripts virais baseados em "modelagem".
    2.  **Instagram Insights:** Análise básica de métricas e Top Posts.
    3.  **Análise Profunda (Groq):** Transcrição completa e análise de retenção.
    4.  **Visão Computacional (Gemini):** Análise de elementos visuais e legendas.
    """)

with col2:
    st.success("🔒 **Status do Sistema:** Online e Seguro")
    st.markdown("""
    **Novidades v1.0:**
    * Integração com Google Sheets ✅
    * IA Llama 3 e Gemini 2.0 ✅
    * Login seguro do Instagram ✅
    """)

# Rodapé
st.markdown("---")
st.caption("Desenvolvido por Caio Jardim | Uso Interno da Agência")