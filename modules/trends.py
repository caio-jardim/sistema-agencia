import streamlit as st
import google.generativeai as genai
from groq import Groq
import json
from datetime import datetime
from modules.prompts import PROMPT_GERADOR_LISTA_HYPE, PROMPT_ROTEIRO_HYPE

def limpar_json(texto):
    """Remove markdown ```json e ``` para evitar erros de parse"""
    texto = texto.replace("```json", "").replace("```", "")
    return texto

def configurar_gemini():
    """Configura a API do Gemini de forma segura"""
    try:
        # Tenta pegar a chave específica, se não der, tenta a genérica
        api_key = st.secrets["gemini"].get("api_marcio") or st.secrets["gemini"].get("api_key")
        if not api_key:
            st.error("Chave Gemini não encontrada no secrets.")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Erro config Gemini: {e}")
        return False

def gerar_hypes_gemini(nicho, janela, tom, obs):
    """Usa o Gemini para gerar a lista de pautas"""
    if not configurar_gemini(): return []
    
    # Modelo mais rápido e barato para listas
    model = genai.GenerativeModel('gemini-1.5-flash') 
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    # --- AQUI ESTAVA O ERRO ---
    # O Python estava tentando preencher o {janela} do texto, mas não tinha a variável aqui.
    prompt_final = PROMPT_GERADOR_LISTA_HYPE.format(
        data_hoje=data_hoje,
        nicho=nicho,
        janela=janela,  # <--- LINHA ADICIONADA (CORREÇÃO)
        tom=tom,       # (Opcional: se seu prompt não tiver {tom}, ele ignora, mas não dá erro)
        obs=obs
    )
    
    try:
        response = model.generate_content(prompt_final)
        texto_limpo = limpar_json(response.text)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro no Gemini: {e}")
        return []

def escrever_roteiro_groq(pauta, nicho, tom, obs):
    """Usa Llama 3 (Groq) para escrever o roteiro final"""
    if "groq" in st.secrets:
        client = Groq(api_key=st.secrets["groq"]["api_key"])
    else:
        st.error("Chave Groq não configurada.")
        return "Erro de configuração."

    prompt_final = PROMPT_ROTEIRO_HYPE.format(
        nicho=nicho,
        obs=obs,
        tom=tom,
        titulo=pauta['titulo'],
        hype=pauta['hype'],
        gancho=pauta['gancho']
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_final}],
            temperature=0.7 
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erro na Groq: {e}"
    