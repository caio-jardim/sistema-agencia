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
    st.markdown("### 🔒 Acesso Restrito - Equipe E21")
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
st.title("🚀 Equipe E21 Studio")
st.markdown("### Bem-vindo ao Sistema Central de Automação")
st.markdown("---")

# Layout de Dashboard simples
col1, col2 = st.columns(2)

with col1:
    st.info("👈 **Use o menu lateral** para acessar as ferramentas.")
    st.markdown("""
    **Ferramentas Disponíveis:**
    
    1.  **Instagram Insights:** Análise básica de métricas e Top Posts.
    2.  **Gerador de Roteiros:** Cria scripts virais baseados em "modelagem".
    3.  **Vídeo Diário:** Gera temas da semana e ganchos com o nicho selecionado.
    """)

# Rodapé
st.markdown("---")
st.caption("Uso Interno da Agência")