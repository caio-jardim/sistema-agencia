# modules/ui.py
import streamlit as st

def carregar_css():
    """Injeta CSS global para deixar o app mais bonito"""
    st.markdown("""
        <style>
        /* Importar Fonte Google (Inter) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Melhorar Botões Primários */
        .stButton>button {
            border-radius: 12px;
            font-weight: 600;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        /* Melhorar Inputs */
        .stTextInput>div>div>input {
            border-radius: 10px;
            border: 1px solid #E0E0E0;
        }

        /* Card Personalizado (CSS Class) */
        .custom-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #F0F0F0;
            margin-bottom: 20px;
            transition: transform 0.2s;
        }
        .custom-card:hover {
            transform: scale(1.01);
            border-color: #F63366;
        }
        
        /* Títulos */
        h1, h2, h3 {
            color: #1E1E1E;
            font-weight: 800;
        }
        
        /* Remover padding excessivo do topo */
        .block-container {
            padding-top: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

def card_ideia(titulo, estrutura, explicacao, indice):
    """
    Cria um card visualmente rico usando HTML em vez de st.container
    """
    html_content = f"""
    <div class="custom-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h3 style="margin: 0; color: #333; font-size: 1.2rem;">#{indice+1} {titulo}</h3>
            <span style="background-color: #F0F2F6; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; color: #555;">
                {estrutura}
            </span>
        </div>
        <p style="color: #666; font-size: 0.95rem; line-height: 1.5;">
            💡 <b>Por que funciona:</b> {explicacao}
        </p>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)