import streamlit as st


# Configuração da Página (Título e Ícone da aba)
st.set_page_config(
    page_title="Agência Marketing OS",
    page_icon="🚀",
    layout="wide"
)

# --- SISTEMA DE LOGIN (Copie e cole logo após os imports) ---
def check_password():
    """Retorna True se o usuário tiver a senha correta."""
    def password_entered():
        """Checa se a senha inserida bate com a dos segredos."""
        if st.session_state["password"] == st.secrets["general"]["team_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Não manter a senha na memória
        else:
            st.session_state["password_correct"] = False

    # Se a senha já foi validada, retorna True
    if "password_correct" in st.session_state:
        if st.session_state["password_correct"]:
            return True

    # Se não, mostra o campo de senha
    st.markdown("### 🔒 Acesso Restrito - Equipe Agência")
    st.text_input(
        "Digite a senha de acesso:", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if "password_correct" in st.session_state:
        if not st.session_state["password_correct"]:
            st.error("😕 Senha incorreta. Tente novamente.")
            
    return False

# BLOQUEIO DE SEGURANÇA
# Se a senha não for verificada, o script para de rodar aqui.
if not check_password():
    st.stop()


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