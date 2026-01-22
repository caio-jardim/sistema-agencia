import streamlit as st
import os
import time
import json
import requests
import yt_dlp
from groq import Groq
from apify_client import ApifyClient
from moviepy.editor import VideoFileClip

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gerador de Carrosséis", page_icon="🎠", layout="wide")

st.title("🎠 Gerador de Carrosséis: Método Tempestade")
st.markdown("Transforme qualquer conteúdo (YouTube, Reels ou Post) em estruturas validadas.")
st.markdown("---")

# --- LOGIN ---
def check_password():
    if "password_correct" in st.session_state and st.session_state["password_correct"]:
        return True
    
    def password_entered():
        if st.session_state["password"] == st.secrets["general"]["team_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    st.text_input("Senha:", type="password", on_change=password_entered, key="password")
    return False

if not check_password():
    st.stop()

# --- CONFIGURAÇÕES DE API ---
try:
    if "groq" in st.secrets and "api_key" in st.secrets["groq"]:
        client_groq = Groq(api_key=st.secrets["groq"]["api_key"])
    else:
        st.error("Chave Groq não encontrada em [groq] api_key.")
        st.stop()
        
    if "apify_token" in st.secrets:
        client_apify = ApifyClient(st.secrets["apify_token"])
    else:
        st.error("Token Apify não encontrado.")
        st.stop()
except Exception as e:
    st.error(f"Erro de configuração de chaves: {e}")
    st.stop()

# ==========================================
# PROMPTS DE INTELIGÊNCIA (O CÉREBRO)
# ==========================================

# 1. PROMPT PARA GERAR AS IDEIAS (JSON)
SYSTEM_PROMPT_TEMPESTADE = """
VOCÊ É: Um Estrategista de Conteúdo Viral e Analista de Atenção.
SUA MISSÃO: Analisar o CONTEÚDO BASE e Gerar estruturas de conteúdo validadas psicologicamente.
O QUE VOCÊ NÃO FAZ: Você NÃO escreve roteiros, NÃO escreve legendas, NÃO escreve copy final. Você entrega a ESTRUTURA.

TOM DE VOZ:
- Analítico, cirúrgico e "Sênior".
- Foco em: "Por que isso funciona?" (Psicologia do consumidor).
- Zero "encher linguiça". Vá direto à estrutura.

EXEMPLOS DE TREINAMENTO (FEW-SHOT):

Usuário: Ideias para Padaria Artesanal.
Você:
1. “O pão que você compra não é pão”
Estrutura: Confrontação de realidade + quebra de senso comum
Por que funciona: Ataca uma crença automática do público e reposiciona a padaria como referência técnica. A ideia não é ensinar receita, e sim mudar o critério de julgamento.

2. “Por que essa fornada nunca fica igual à outra”
Estrutura: Bastidores + dinâmica invisível do processo
Por que funciona: Revela que a imperfeição controlada é sinal de qualidade artesanal. Educa o público a valorizar variáveis como fermentação natural. Transforma "defeito" em prova de excelência.

3. “O erro que faz a maioria desistir do pão artesanal”
Estrutura: Combate ao inimigo + posicionamento claro
Por que funciona: Define um vilão (pressa/atalhos) e posiciona a marca como quem escolheu o caminho difícil. Filtra curiosos de compradores reais.

FORMATO DE RESPOSTA (JSON ESTRITO):
Você deve retornar APENAS um JSON válido contendo um array de objetos. 
Não use Markdown. Não escreva nada antes ou depois do JSON.

Estrutura obrigatória:
[
  {
    "titulo": "Título Curto e Impactante",
    "estrutura": "Nome técnico da estrutura (ex: Quebra de Padrão, Lista Invertida)",
    "por_que_funciona": "Explicação estratégica de como isso muda a percepção ou ataca uma crença"
  },
  ... (total de 3 itens)
]
"""

# 2. PROMPT PARA ESCREVER O CARROSSEL (SEU NOVO PROMPT)
# 2. PROMPT ARQUITETO (AGORA EM JSON E OTIMIZADO)
SYSTEM_PROMPT_ARQUITETO = """
VOCÊ É: Um Engenheiro de Atenção e Estrategista de Narrativas (Nível Sênior).
Sua especialidade é criar roteiros de carrossel que geram "Stop Scroll" imediato.

## SEU PRIMEIRO PASSO (CRÍTICO): DEFINIR O TAMANHO
Antes de escrever, analise a complexidade do tema para definir a quantidade de slides.
Siga esta regra de "Engenharia de Tensão":

1. [Nível Simples] (5 Slides):
   - Use para: Temas com um único conflito ou dicas rápidas.
   - Estrutura: Gancho -> Erro -> Tese -> Explicação -> Fechamento.

2. [Zona Ideal] (7 a 9 Slides) -> **PREFERÊNCIA PADRÃO**:
   - Use para: A maioria dos temas virais.
   - Estrutura: Ato 1 (Choque) -> Ato 2 (Conflito + Explicação) -> Ato 3 (Síntese).

3. [Nível Blindado] (10 a 12 Slides):
   - Use para: Quebrar mitos muito fortes ou temas polêmicos que exigem muita defesa ("blindagem").

*REGRA DE OURO:* Cada slide deve ter uma "virada de pensamento". Se o raciocínio acabou, o carrossel acaba. Não encha linguiça.

## SUAS FERRAMENTAS (GATILHOS MENTAIS):
Ao escrever a "Nota de Engenharia" (no JSON), escolha um destes:
- [Paradoxo]: Uma verdade que parece mentira.
- [Inimigo Comum]: Culpar algo externo.
- [Quebra de Padrão]: Dizer o oposto do guru motivacional.
- [Tensão Latente]: A sensação de que algo vai dar errado.
- [Substituição de Herói]: Tirar o foco do esforço e colocar na estratégia.
- [Open Loop]: Abrir uma questão que só se resolve no final.

## DIRETRIZES DE ESTILO:
1. TEXTO VISUAL: Use quebras de linha (\\n). Máximo 2 frases por bloco.
2. TOM ÁCIDO: Seja direto. Corte palavras de transição.
3. ZERO OBVIEDADE: Nada de "Seja resiliente". Seja contra-intuitivo.

## O QUE VOCÊ NÃO DEVE FAZER:
- NÃO use emojis no meio do texto.
- NÃO dê boas vindas.
- NÃO explique o óbvio.

## FORMATO DE SAÍDA (JSON OBRIGATÓRIO):
Você deve retornar APENAS um objeto JSON. Sem Markdown, sem ```json```, sem intro.

Estrutura JSON:
{
  "meta_dados": {
    "tema": "Tema recebido",
    "complexidade_detectada": "Simples/Ideal/Blindado",
    "total_slides": 0
  },
  "carrossel": [
    {
      "painel": 1,
      "fase": "Gancho / Tensão / Virada / Fechamento",
      "texto": "Texto do slide aqui...",
      "nota_engenharia": "[Gatilho] Explicação técnica..."
    }
  ]
}
"""

# --- FUNÇÕES AUXILIARES ---

def limpar_json(texto):
    """Limpa formatação markdown que a IA possa colocar no JSON"""
    texto = texto.replace("```json", "").replace("```", "")
    start = texto.find("{") # Procura chaves (objeto)
    if start == -1: start = texto.find("[") # Ou colchetes (array)
    
    # Procura o final
    end_obj = texto.rfind("}")
    end_arr = texto.rfind("]")
    end = max(end_obj, end_arr) + 1
    
    if start != -1 and end != -1:
        return texto[start:end]
    return texto

def download_youtube_audio(url):
    """Baixa áudio do YouTube usando yt-dlp (Modo Android)"""
    output_filename = "temp_yt_audio"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_filename,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True, 'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        final_filename = f"{output_filename}.mp3"
        if os.path.exists(final_filename): return final_filename
        if os.path.exists(output_filename): return output_filename
        return None
    except Exception as e:
        st.warning(f"Método Android falhou. Tentando Web Creator...")
        try:
            ydl_opts['extractor_args']['youtube']['player_client'] = ['web_creator']
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            return f"{output_filename}.mp3"
        except Exception as e2:
            st.error(f"❌ Falha no download do YouTube: {e2}")
            return None

def get_instagram_data_apify(url):
    """Usa Apify para pegar dados do post (Sem searchType)"""
    run_input = {
        "directUrls": [url],
        "resultsType": "posts",
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
    }
    # run_input["proxy"] = {"useApifyProxy": True, "apifyProxyGroups": []} 
    try:
        run = client_apify.actor("apify/instagram-scraper").call(run_input=run_input)
        if not run: return None
        dataset_items = client_apify.dataset(run["defaultDatasetId"]).list_items().items
        if dataset_items: return dataset_items[0]
        return None
    except Exception as e:
        st.error(f"Erro na Apify: {e}")
        return None

def download_file(url, filename):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e:
        st.error(f"Erro download arquivo: {e}")
        return False

def transcrever_audio_groq(filepath):
    try:
        with open(filepath, "rb") as file:
            transcription = client_groq.audio.transcriptions.create(
                file=(filepath, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        return str(transcription)
    except Exception as e:
        st.error(f"Erro na Transcrição: {e}")
        return None

# --- AGENTES DE IA ---

def agente_tempestade_ideias(conteudo_base):
    """Gera 3 ideias em JSON"""
    try:
        prompt_user = f"Analise este conteúdo e gere 3 conceitos:\n\nCONTEÚDO BASE:\n{conteudo_base[:6000]}"
        completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPESTADE},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
        )
        texto_limpo = limpar_json(completion.choices[0].message.content)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro na IA Tempestade: {e}")
        return None

def agente_arquiteto_carrossel(ideia_escolhida, conteudo_base):
    """
    Gera o roteiro em JSON com os parâmetros calibrados.
    """
    try:
        prompt_user = f"""
        CONTEÚDO ORIGINAL DE BASE:
        "{conteudo_base[:3000]}"
        
        CONCEITO ESCOLHIDO PARA O CARROSSEL:
        Título: {ideia_escolhida['titulo']}
        Estrutura: {ideia_escolhida['estrutura']}
        Lógica: {ideia_escolhida['por_que_funciona']}
        """
        
        # CHAMADA CONFIGURADA EXATAMENTE COMO VOCÊ PEDIU
        completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ARQUITETO},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile",  # Modelo Sênior
            temperature=0.5,          # Equilíbrio
            top_p=0.9,
            max_tokens=1024,
            response_format={"type": "json_object"} # Garante o JSON
        )
        
        texto_limpo = limpar_json(completion.choices[0].message.content)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro na IA Arquiteto: {e}")
        return None

# --- INTERFACE PRINCIPAL ---

tipo_conteudo = st.radio("Qual a origem da ideia?", ["YouTube", "Reels (Instagram)", "Carrossel (Instagram)"], horizontal=True)
url_input = st.text_input(f"Cole o link do {tipo_conteudo}:", placeholder="https://...")

# Botão Principal (Gera as Ideias)
if st.button("⚡ Analisar e Gerar Conceitos", type="primary"):
    if not url_input:
        st.warning("Insira um link.")
    else:
        st.session_state['conteudo_base'] = None 
        st.session_state['ideias_geradas'] = None
        st.session_state['roteiro_final'] = None
        
        status = st.status("Processando conteúdo...", expanded=True)
        texto_extraido = ""

        # LÓGICA DE EXTRAÇÃO
        if tipo_conteudo == "YouTube":
            status.write("⬇️ Baixando YouTube...")
            f = download_youtube_audio(url_input)
            if f:
                status.write("👂 Transcrevendo...")
                texto_extraido = transcrever_audio_groq(f)
                if os.path.exists(f): os.remove(f)

        elif tipo_conteudo == "Reels (Instagram)":
            status.write("🕵️ Acessando Reels...")
            data = get_instagram_data_apify(url_input)
            if data and (data.get('videoUrl') or data.get('video_url')):
                v_url = data.get('videoUrl') or data.get('video_url')
                if download_file(v_url, "temp.mp4"):
                    try:
                        vc = VideoFileClip("temp.mp4")
                        vc.audio.write_audiofile("temp.mp3", verbose=False, logger=None)
                        vc.close()
                        status.write("👂 Transcrevendo...")
                        texto_extraido = transcrever_audio_groq("temp.mp3")
                    except: st.error("Erro processamento vídeo")
                    finally:
                        if os.path.exists("temp.mp4"): os.remove("temp.mp4")
                        if os.path.exists("temp.mp3"): os.remove("temp.mp3")

        elif tipo_conteudo == "Carrossel (Instagram)":
            status.write("🕵️ Lendo Carrossel...")
            data = get_instagram_data_apify(url_input)
            if data:
                cap = data.get('caption') or ""
                alts = [c.get('alt') for c in (data.get('childPosts') or []) if c.get('alt')]
                texto_extraido = f"LEGENDA:\n{cap}\nVISUAL:\n{' '.join(alts)}"

        # SE EXTRAIU COM SUCESSO, GERA AS IDEIAS
        if texto_extraido:
            st.session_state['conteudo_base'] = texto_extraido
            status.write("🧠 Gerando conceitos estruturais...")
            ideias = agente_tempestade_ideias(texto_extraido)
            
            if ideias:
                st.session_state['ideias_geradas'] = ideias
                status.update(label="Conceitos Prontos!", state="complete", expanded=False)
            else:
                status.update(label="Erro na IA", state="error")
        else:
            status.update(label="Falha na extração", state="error")

# --- EXIBIÇÃO DAS IDEIAS E GERAÇÃO DE CARROSSEL ---
if 'ideias_geradas' in st.session_state and st.session_state['ideias_geradas']:
    st.markdown("---")
    st.subheader("⛈️ Estruturas Identificadas")
    
    ideias = st.session_state['ideias_geradas']
    
    for i, ideia in enumerate(ideias):
        with st.container(border=True):
            col_txt, col_btn = st.columns([4, 1])
            
            with col_txt:
                st.markdown(f"### {i+1}. {ideia['titulo']}")
                st.caption(f"📐 **Estrutura:** {ideia['estrutura']}")
                st.write(f"💡 *{ideia['por_que_funciona']}*")
            
            with col_btn:
                st.write("")
                st.write("")
                if st.button("🎨 Gerar Carrossel", key=f"btn_car_{i}"):
                    st.session_state['ideia_ativa'] = ideia
                    # Limpa roteiro anterior se mudar de ideia
                    st.session_state['roteiro_final'] = None 
                    st.rerun()

# --- EXIBIÇÃO DO ROTEIRO FINAL (VISUAL APRIMORADO) ---
if 'ideia_ativa' in st.session_state:
    st.markdown("---")
    st.info(f"🏗️ Projetando Carrossel: **{st.session_state['ideia_ativa']['titulo']}**")
    
    # Se ainda não tem roteiro ou se trocou de ideia, gera
    if st.session_state.get('roteiro_final') is None:
        with st.spinner("O Arquiteto está desenhando os slides..."):
            roteiro_json = agente_arquiteto_carrossel(
                st.session_state['ideia_ativa'], 
                st.session_state.get('conteudo_base', '')
            )
            st.session_state['roteiro_final'] = roteiro_json
            st.rerun() # Recarrega para exibir
            
    # EXIBIÇÃO VISUAL DOS SLIDES
    roteiro = st.session_state.get('roteiro_final')
    if roteiro and 'carrossel' in roteiro:
        st.success("Projeto Finalizado! 👇")
        
        for slide in roteiro['carrossel']:
            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f"#### Painel {slide.get('painel', '#')}")
                    st.caption(f"**{slide.get('fase', 'Fase')}**")
                with c2:
                    st.markdown(f"📝 **Texto:**")
                    st.code(slide.get('texto', ''), language="text")
                    
                    st.markdown(f"🔧 **Nota de Engenharia:**")
                    st.info(slide.get('nota_engenharia', ''))
    
    if st.button("Fechar Projeto"):
        del st.session_state['ideia_ativa']
        st.session_state['roteiro_final'] = None
        st.rerun()