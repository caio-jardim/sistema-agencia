import streamlit as st
import os
import time
import json
import requests
import yt_dlp
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
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
# INTEGRAÇÃO GOOGLE SHEETS
# ==========================================

def conectar_sheets():
    """Conecta ao Google Sheets usando as credenciais do secrets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        return None

def verificar_existencia_db(client, aba_nome, url_input):
    """
    Verifica se a URL já existe na planilha.
    Retorna o texto da transcrição se existir, ou None.
    """
    try:
        sh = client.open("DB_Conteudos")
        try:
            worksheet = sh.worksheet(aba_nome)
        except:
            # Se a aba não existe, cria com os cabeçalhos corretos
            worksheet = sh.add_worksheet(title=aba_nome, rows="1000", cols="20")
            if aba_nome == "instagram":
                worksheet.append_row(["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Gancho_Verbal"])
            else:
                worksheet.append_row(["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper"])
        
        # Procura a URL na coluna 5 (URL_Original)
        # Nota: O gspread cell.col começa em 1. A coluna E é a 5.
        try:
            cell = worksheet.find(url_input)
            if cell:
                # Se achou, pega a Transcrição (Coluna 9 - I)
                # linha = cell.row
                row_values = worksheet.row_values(cell.row)
                # A transcrição é o índice 8 (coluna 9)
                if len(row_values) >= 9:
                    return row_values[8] # Retorna a transcrição
        except gspread.exceptions.CellNotFound:
            return None
            
        return None
    except Exception as e:
        st.warning(f"Não foi possível ler o banco de dados: {e}")
        return None

def salvar_no_db(client, aba_nome, dados):
    """Salva uma nova linha na planilha"""
    try:
        sh = client.open("DB_Conteudos")
        worksheet = sh.worksheet(aba_nome)
        
        # Prepara a linha baseada na estrutura pedida
        if aba_nome == "instagram":
            row = [
                dados.get("id_unico", ""),
                datetime.now().strftime("%d/%m/%Y"), # Data Coleta
                dados.get("perfil", ""),
                dados.get("data_postagem", ""),
                dados.get("url", ""),
                dados.get("views", 0),
                dados.get("likes", 0),
                dados.get("comments", 0),
                dados.get("transcricao", ""),
                dados.get("gancho_verbal", "") # Extra para Insta
            ]
        else: # Youtube
            row = [
                dados.get("id_unico", ""),
                datetime.now().strftime("%d/%m/%Y"),
                dados.get("perfil", ""),
                dados.get("data_postagem", ""),
                dados.get("url", ""),
                dados.get("views", 0),
                dados.get("likes", 0),
                dados.get("comments", 0),
                dados.get("transcricao", "")
            ]
            
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Banco de Dados: {e}")
        return False

# ==========================================
# PROMPTS DE INTELIGÊNCIA
# ==========================================

SYSTEM_PROMPT_TEMPESTADE = """
VOCÊ É: Um Estrategista de Conteúdo Viral e Analista de Atenção.
SUA MISSÃO: Analisar o CONTEÚDO BASE e Gerar estruturas de conteúdo validadas psicologicamente.
O QUE VOCÊ NÃO FAZ: Você NÃO escreve roteiros, NÃO escreve legendas, NÃO escreve copy final. Você entrega a ESTRUTURA.

TOM DE VOZ:
- Analítico, cirúrgico e "Sênior".
- Foco em: "Por que isso funciona?" (Psicologia do consumidor).
- Zero "encher linguiça". Vá direto à estrutura.

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
    end_obj = texto.rfind("}")
    end_arr = texto.rfind("]")
    end = max(end_obj, end_arr) + 1
    if start != -1 and end != -1:
        return texto[start:end]
    return texto

def get_youtube_metadata(url):
    """Extrai metadados do YouTube sem baixar o vídeo"""
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "id_unico": info.get('id'),
                "perfil": info.get('uploader') or info.get('channel'),
                "data_postagem": info.get('upload_date'), # Formato YYYYMMDD
                "views": info.get('view_count'),
                "likes": info.get('like_count'),
                "comments": info.get('comment_count'),
                "title": info.get('title')
            }
    except:
        return {}

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
    """Usa Apify para pegar dados do post"""
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
    try:
        prompt_user = f"""
        CONTEÚDO ORIGINAL DE BASE:
        "{conteudo_base[:3000]}"
        
        CONCEITO ESCOLHIDO PARA O CARROSSEL:
        Título: {ideia_escolhida['titulo']}
        Estrutura: {ideia_escolhida['estrutura']}
        Lógica: {ideia_escolhida['por_que_funciona']}
        """
        
        completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ARQUITETO},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            top_p=0.9,
            max_tokens=1024,
            response_format={"type": "json_object"}
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
        # Reset de estados
        st.session_state['conteudo_base'] = None 
        st.session_state['ideias_geradas'] = None
        st.session_state['roteiro_final'] = None
        
        status = st.status("Iniciando processo...", expanded=True)
        texto_extraido = ""
        
        # 1. CONEXÃO COM BANCO DE DADOS
        gs_client = conectar_sheets()
        if not gs_client:
            status.update(label="Erro no Banco de Dados", state="error")
            st.stop()
            
        aba_alvo = "Youtube" if tipo_conteudo == "YouTube" else "instagram"
        
        # 2. VERIFICA SE JÁ EXISTE (ECONOMIA DE CRÉDITOS)
        status.write(f"🔎 Verificando se link já existe na aba '{aba_alvo}'...")
        transcricao_db = verificar_existencia_db(gs_client, aba_alvo, url_input)
        
        if transcricao_db:
            status.write("✅ Encontrado no Banco de Dados! Usando dados salvos.")
            texto_extraido = transcricao_db
            time.sleep(1) # UX
        else:
            status.write("⚠️ Não encontrado. Iniciando extração (Apify/Download)...")
            
            # 3. PROCESSO DE EXTRAÇÃO (SE NÃO EXISTIR)
            dados_para_salvar = {}
            
            if tipo_conteudo == "YouTube":
                # Pega Metadados
                meta = get_youtube_metadata(url_input)
                dados_para_salvar = {
                    "id_unico": meta.get('id_unico', ''),
                    "perfil": meta.get('perfil', ''),
                    "data_postagem": meta.get('data_postagem', ''),
                    "url": url_input,
                    "views": meta.get('views', 0),
                    "likes": meta.get('likes', 0),
                    "comments": meta.get('comments', 0)
                }
                
                status.write("⬇️ Baixando áudio...")
                f = download_youtube_audio(url_input)
                if f:
                    status.write("👂 Transcrevendo (Groq)...")
                    texto_extraido = transcrever_audio_groq(f)
                    if os.path.exists(f): os.remove(f)
                    
            elif tipo_conteudo in ["Reels (Instagram)", "Carrossel (Instagram)"]:
                status.write("🕵️ Acessando Apify...")
                data = get_instagram_data_apify(url_input)
                
                if data:
                    # Prepara dados para salvar
                    dados_para_salvar = {
                        "id_unico": data.get('id', ''),
                        "perfil": data.get('ownerUsername', ''),
                        "data_postagem": data.get('timestamp', '')[:10],
                        "url": url_input,
                        "views": data.get('videoViewCount') or data.get('playCount', 0),
                        "likes": data.get('likesCount', 0),
                        "comments": data.get('commentsCount', 0)
                    }

                    if tipo_conteudo == "Reels (Instagram)":
                        v_url = data.get('videoUrl') or data.get('video_url')
                        if v_url and download_file(v_url, "temp.mp4"):
                            try:
                                vc = VideoFileClip("temp.mp4")
                                vc.audio.write_audiofile("temp.mp3", verbose=False, logger=None)
                                vc.close()
                                status.write("👂 Transcrevendo...")
                                texto_extraido = transcrever_audio_groq("temp.mp3")
                            except: 
                                st.error("Erro processamento vídeo")
                            finally:
                                if os.path.exists("temp.mp4"): os.remove("temp.mp4")
                                if os.path.exists("temp.mp3"): os.remove("temp.mp3")
                    
                    elif tipo_conteudo == "Carrossel (Instagram)":
                        cap = data.get('caption') or ""
                        alts = [c.get('alt') for c in (data.get('childPosts') or []) if c.get('alt')]
                        texto_extraido = f"LEGENDA:\n{cap}\nVISUAL:\n{' '.join(alts)}"

            # 4. SALVAMENTO NO BANCO (SE FOI EXTRAÍDO AGORA)
            if texto_extraido:
                dados_para_salvar["transcricao"] = texto_extraido
                # Gancho verbal simples (primeiros 100 chars) para Insta
                if aba_alvo == "instagram":
                    dados_para_salvar["gancho_verbal"] = texto_extraido[:100] + "..."
                
                status.write("💾 Salvando novo conteúdo na Planilha...")
                salvar_no_db(gs_client, aba_alvo, dados_para_salvar)

        # 5. GERAÇÃO DAS IDEIAS (IA)
        if texto_extraido:
            st.session_state['conteudo_base'] = texto_extraido
            status.write("🧠 Gerando conceitos estruturais...")
            ideias = agente_tempestade_ideias(texto_extraido)
            
            if ideias:
                st.session_state['ideias_geradas'] = ideias
                status.update(label="Processo Finalizado!", state="complete", expanded=False)
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
                    st.session_state['roteiro_final'] = None 
                    st.rerun()

# --- EXIBIÇÃO DO ROTEIRO FINAL ---
if 'ideia_ativa' in st.session_state:
    st.markdown("---")
    st.info(f"🏗️ Projetando Carrossel: **{st.session_state['ideia_ativa']['titulo']}**")
    
    if st.session_state.get('roteiro_final') is None:
        with st.spinner("O Arquiteto está desenhando os slides..."):
            roteiro_json = agente_arquiteto_carrossel(
                st.session_state['ideia_ativa'], 
                st.session_state.get('conteudo_base', '')
            )
            st.session_state['roteiro_final'] = roteiro_json
            st.rerun()
            
    roteiro = st.session_state.get('roteiro_final')
    if roteiro and 'carrossel' in roteiro:
        # Exibe Metadados
        meta = roteiro.get('meta_dados', {})
        if meta:
            c1, c2, c3 = st.columns(3)
            c1.metric("Complexidade", meta.get('complexidade_detectada', '-'))
            c2.metric("Slides", meta.get('total_slides', '-'))
            c3.caption(f"Tema: {meta.get('tema', '-')}")
            
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