# modules/ai_processor.py
import streamlit as st
import os
import json
from groq import Groq
from moviepy.editor import VideoFileClip
from modules.prompts import PROMPT_ANALISE_GANCHO # <--- Importa o prompt

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