import streamlit as st
import os
import json
from groq import Groq
from moviepy.editor import VideoFileClip

# Importa TODOS os prompts necessários (Página 01 e 04)
from modules.prompts import (
    PROMPT_ANALISE_GANCHO, 
    SYSTEM_PROMPT_TEMPESTADE, 
    SYSTEM_PROMPT_ARQUITETO, 
    SYSTEM_PROMPT_VENDAS
)

# --- FUNÇÕES UTILITÁRIAS ---

def limpar_json(texto):
    """Limpa formatação de markdown para evitar erro de JSON"""
    texto = texto.replace("```json", "").replace("```", "").strip()
    start_arr = texto.find("[")
    end_arr = texto.rfind("]")
    start_obj = texto.find("{")
    end_obj = texto.rfind("}")
    
    if start_arr != -1 and end_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        return texto[start_arr:end_arr+1]
    if start_obj != -1 and end_obj != -1:
        return texto[start_obj:end_obj+1]
    return texto

def transcrever_audio_groq(filepath):
    """Transcreve áudio usando Whisper na Groq (Usado na Pag 04)"""
    if "groq" not in st.secrets: return None
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    try:
        with open(filepath, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(filepath, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        return str(transcription)
    except Exception as e:
        st.error(f"Erro na Transcrição: {e}")
        return None

# --- FUNÇÕES PARA PÁGINA 01 (INSTAGRAM ANALYZER) ---

def analisar_video_groq(video_path, status_box):
    """Extrai áudio, transcreve e analisa ganchos (Usado na Pag 01)"""
    if "groq" in st.secrets and "api_key" in st.secrets["groq"]:
        client_groq = Groq(api_key=st.secrets["groq"]["api_key"])
    else:
        return {"transcricao": "Erro: Chave Groq não configurada", "ganchos_verbais": "-"}

    audio_path = video_path.replace(".mp4", ".mp3")

    try:
        status_box.write("🔊 Extraindo áudio...")
        try:
            video_clip = VideoFileClip(video_path)
            video_clip.audio.write_audiofile(audio_path, bitrate="32k", verbose=False, logger=None)
            video_clip.close()
        except Exception as e:
            return {"transcricao": f"Erro MoviePy: {e}", "ganchos_verbais": "-"}

        status_box.write("📝 Transcrevendo (Whisper)...")
        with open(audio_path, "rb") as file:
            transcription = client_groq.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3", 
                response_format="text"
            )
        texto_transcrito_completo = str(transcription)

        status_box.write("🧠 Analisando com Llama 3...")
        
        prompt_final = PROMPT_ANALISE_GANCHO.format(
            texto_transcrito=texto_transcrito_completo[:4000]
        )
        
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_final}],
            temperature=0.1, 
            response_format={"type": "json_object"}
        )

        resultado_ia = json.loads(completion.choices[0].message.content)

        if os.path.exists(audio_path): os.remove(audio_path)

        return {
            "transcricao": texto_transcrito_completo,
            "ganchos_verbais": resultado_ia.get("ganchos_verbais", "-"),
            "ganchos_visuais": resultado_ia.get("ganchos_visuais", "-")
        }

    except Exception as e:
        status_box.error(f"Erro Groq: {e}")
        if os.path.exists(audio_path): os.remove(audio_path)
        return {"transcricao": "Erro API", "ganchos_verbais": "-"}

# --- FUNÇÕES PARA PÁGINA 04 (GERADOR DE CARROSSEL) ---

def agente_tempestade_ideias(conteudo_base, modo="Conteúdo (Viral)"):
    """
    Gera conceitos baseados no modo escolhido (Viral ou Mentor).
    """
    if "groq" not in st.secrets: return None
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    
    # Lógica de Seleção de Persona
    if modo == "Vendas (Mentor)":
        system_prompt = SYSTEM_PROMPT_VENDAS
        instruction_extra = "ATENÇÃO: Atue no MODO A (Criação). Foque 100% em conversão, quebra de objeção e autoridade. Gere 3 opções em JSON."
    else:
        system_prompt = SYSTEM_PROMPT_TEMPESTADE
        instruction_extra = "Foque em viralidade, retenção e topo de funil. Gere 3 conceitos em JSON."

    try:
        prompt_user = f"""
        {instruction_extra}
        
        CONTEÚDO BASE PARA ANÁLISE:
        {conteudo_base[:12000]}
        """
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        texto_limpo = limpar_json(completion.choices[0].message.content)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro na IA Tempestade ({modo}): {e}")
        return None

def agente_arquiteto_carrossel(ideia_escolhida, conteudo_base):
    """
    Gera o roteiro detalhado do carrossel.
    """
    if "groq" not in st.secrets: return None
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    try:
        prompt_user = f"""
        INSTRUÇÃO CRÍTICA: Baseie-se ESTRITAMENTE na transcrição/conteúdo abaixo.
        === CONTEÚDO ORIGINAL ===
        "{conteudo_base[:15000]}" 
        =========================
        CONCEITO: {ideia_escolhida.get('titulo')}
        ESTRUTURA: {ideia_escolhida.get('estrutura')}
        LÓGICA: {ideia_escolhida.get('por_que_funciona')}
        """
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ARQUITETO},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            top_p=0.9,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        texto_limpo = limpar_json(completion.choices[0].message.content)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro na IA Arquiteto: {e}")
        return None

def transcrever_arquivo_upload_groq(uploaded_file):
    """
    Recebe um arquivo do st.file_uploader, salva temporariamente,
    transcreve via Groq (Ultra Rápido) e retorna o texto.
    """
    if "groq" not in st.secrets:
        st.error("Chave Groq não configurada.")
        return None

    client = Groq(api_key=st.secrets["groq"]["api_key"])
    
    # 1. Salvar o arquivo temporariamente no disco
    # O Streamlit mantém o arquivo na RAM, a Groq precisa ler do disco ou buffer nomeado
    temp_filename = f"temp_{uploaded_file.name}"
    
    try:
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 2. Enviar para a Groq (Modelo Whisper Large v3)
        # Isso substitui o processamento local pesado
        with open(temp_filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(temp_filename, file.read()),
                model="whisper-large-v3", # Modelo mais preciso e rápido do mundo atualmente
                response_format="text",
                language="pt" # Força português
            )
            
        # 3. Limpeza
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return str(transcription)

    except Exception as e:
        st.error(f"Erro na transcrição: {e}")
        # Garante a limpeza mesmo se der erro
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return None