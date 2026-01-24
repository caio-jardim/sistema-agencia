import streamlit as st
import json
from groq import Groq

# --- IMPORTAÇÃO DO MÓDULO QUE CRIAMOS ---
# O Streamlit entende que 'modules' é a pasta na raiz
try:
    from modules.youtube_utils import pegar_dados_youtube_apify
except ImportError:
    st.error("⚠️ Erro de Importação: Certifique-se que a pasta 'modules' existe na raiz e tem o arquivo 'youtube_utils.py'.")
    st.stop()

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Teste Modular YouTube", page_icon="🧪")
st.title("🧪 Teste de Extração: YouTube (Via Apify)")
st.info("Esta aba usa o novo método modular que não baixa vídeo, apenas extrai texto.")

# --- INPUT ---
url = st.text_input("Cole o link do YouTube para testar:")

# --- AGENTE DE IA (SIMPLIFICADO PARA TESTE) ---
def agente_analise_rapida(texto):
    if "groq" not in st.secrets: return None
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    
    prompt = f"""
    Analise esta transcrição de vídeo e me dê 3 ideias de carrossel.
    Responda APENAS em JSON: [{{ "titulo": "...", "estrutura": "..." }}]
    
    TEXTO: {texto[:10000]}
    """
    try:
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return None

# --- BOTÃO DE AÇÃO ---
if st.button("🚀 Testar Módulo Novo"):
    if not url:
        st.warning("Coloque um link.")
    else:
        # 1. CHAMA O MÓDULO NOVO
        resultado = pegar_dados_youtube_apify(url)
        
        if resultado and resultado['sucesso']:
            st.success("✅ Extração com Sucesso!")
            
            # Mostra dados brutos para você conferir
            with st.expander("Ver Dados Extraídos (Debug)"):
                st.json(resultado)
            
            st.markdown("### 📝 Transcrição Recuperada:")
            st.text_area("Texto", resultado['transcricao'][:500] + "...", height=150)
            
            # 2. TESTA A IA
            if resultado['transcricao']:
                st.markdown("---")
                st.write("🧠 **Gerando Ideias com a Transcrição...**")
                ideias = agente_analise_rapida(resultado['transcricao'])
                
                if ideias:
                    cols = st.columns(3)
                    # Verifica se veio dict (com chave carrossel/ideias) ou lista direta
                    lista_ideias = ideias.get('ideias', ideias) if isinstance(ideias, dict) else ideias
                    
                    # Tratamento de erro caso o JSON venha diferente
                    if isinstance(lista_ideias, list):
                        for i, ideia in enumerate(lista_ideias):
                            with cols[i % 3]:
                                st.success(ideia.get('titulo'))
                                st.caption(ideia.get('estrutura'))
                    else:
                        st.json(ideias)
        else:
            st.error("Falha na extração. Verifique os logs acima.")