# modules/ai_processor.py
import streamlit as st
import os
import json
from groq import Groq
import json
from modules.prompts import SYSTEM_PROMPT_TEMPESTADE, SYSTEM_PROMPT_ARQUITETO, SYSTEM_PROMPT_VENDAS
from moviepy.editor import VideoFileClip
from modules.prompts import PROMPT_ANALISE_GANCHO 

def analisar_video_groq(video_path, status_box):
    if "groq" in st.secrets and "api_key" in st.secrets["groq"]:
        client_groq = Groq(api_key=st.secrets["groq"]["api_key"])
    else:
        client_groq = Groq(api_key=st.secrets.get("groq_api_key"))

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
        
        # Usa o prompt que importamos
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

def limpar_json(texto):
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

def agente_tempestade_ideias(conteudo_base, modo="Conteúdo (Viral)"):
    """
    Gera conceitos baseados no modo escolhido.
    modo: "Conteúdo (Viral)" ou "Vendas (Mentor)"
    """
    if "groq" not in st.secrets: return None
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    
    # Seleção do Prompt do Sistema
    if modo == "Vendas (Mentor)":
        system_prompt = SYSTEM_PROMPT_VENDAS
        # Reforço específico para o Mentor focar em conversão/vendas no JSON
        instruction_extra = "Foque 100% em conversão, quebra de objeção e autoridade. Gere 3 opções em JSON."
    else:
        system_prompt = SYSTEM_PROMPT_TEMPESTADE
        instruction_extra = "Foque em viralidade e retenção. Gere 3 conceitos em JSON."

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
            response_format={"type": "json_object"} # Garante que venha JSON
        )
        texto_limpo = limpar_json(completion.choices[0].message.content)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro na IA ({modo}): {e}")
        return None

# ... (mantenha agente_arquiteto_carrossel igual) ...

def agente_arquiteto_carrossel(ideia_escolhida, conteudo_base):
    if "groq" not in st.secrets: return None
    client = Groq(api_key=st.secrets["groq"]["api_key"])
    try:
        prompt_user = f"""
        INSTRUÇÃO CRÍTICA: Baseie-se ESTRITAMENTE na transcrição/conteúdo abaixo.
        === CONTEÚDO ORIGINAL ===
        "{conteudo_base[:12000]}" 
        =========================
        CONCEITO: {ideia_escolhida['titulo']}
        ESTRUTURA: {ideia_escolhida['estrutura']}
        LÓGICA: {ideia_escolhida['por_que_funciona']}
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