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
        try:
            sh = client.open("DB_E21_Conteudos")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ A planilha 'DB_E21_Conteudos' não foi encontrada.")
            return None
            
        # Tenta abrir a aba. Se não existir (WorksheetNotFound), cria.
        try:
            worksheet = sh.worksheet(aba_nome)
        except gspread.exceptions.WorksheetNotFound:
            # Só entra aqui se REALMENTE não existir
            worksheet = sh.add_worksheet(title=aba_nome, rows="1000", cols="20")
            if aba_nome == "instagram":
                worksheet.append_row(["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Gancho_Verbal", "Legenda"])
            else:
                worksheet.append_row(["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Legenda"])
        
        # Procura a URL
        try:
            cell = worksheet.find(url_input)
            if cell:
                row_values = worksheet.row_values(cell.row)
                if len(row_values) >= 9:
                    return row_values[8] # Retorna a transcrição
        except gspread.exceptions.CellNotFound:
            return None
        except Exception as e:
            return None
            
        return None
    except Exception as e:
        # Se der erro de "Already exists" aqui, ignoramos e seguimos
        if "already exists" in str(e):
            return None
        st.warning(f"Aviso no banco de dados: {e}")
        return None

def salvar_no_db(client, aba_nome, dados):
    """
    Salva uma nova linha na planilha com ID_Unico e colunas atualizadas.
    """
    try:
        sh = client.open("DB_E21_Conteudos")
        worksheet = sh.worksheet(aba_nome)
        
        # Funções auxiliares para evitar erros de NoneType
        def safe_str(key): return str(dados.get(key, "") or "")
        def safe_int(key): return int(dados.get(key, 0) or 0)
        
        # Limpa o texto da legenda
        legenda_limpa = safe_str("caption").replace("\t", " ").replace("\n", " ")[:4000] 

        if aba_nome == "instagram":
            # Colunas: ID_Unico, Data_Coleta, Perfil, Data_Postagem, URL_Original, Views, Likes, Comments, Transcricao_Whisper, Gancho_Verbal, Legenda
            row = [
                safe_str("id_unico"),
                datetime.now().strftime("%d/%m/%Y"),
                safe_str("perfil"),
                safe_str("data_postagem"),
                safe_str("url"),
                safe_int("views"),
                safe_int("likes"),
                safe_int("comments"),
                safe_str("transcricao"),
                safe_str("gancho_verbal"),
                legenda_limpa
            ]
        else: # Youtube
            # Colunas: ID_Unico, Data_Coleta, Perfil, Data_Postagem, URL_Original, Views, Likes, Comments, Transcricao_Whisper, Legenda
            row = [
                safe_str("id_unico"),
                datetime.now().strftime("%d/%m/%Y"),
                safe_str("perfil"),
                safe_str("data_postagem"),
                safe_str("url"),
                safe_int("views"),
                safe_int("likes"),
                safe_int("comments"),
                safe_str("transcricao"),
                legenda_limpa
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


SYSTEM_PROMPT_ARQUITETO = """
VOCÊ É: Um Engenheiro de Atenção e Estrategista de Narrativas (Nível Sênior).
Sua especialidade é criar roteiros de carrossel que geram "Stop Scroll" imediato.

## SEU PRIMEIRO PASSO: DEFINIR O TAMANHO
1. [Nível Simples] (5 Slides)
   - Use para: Temas com um único conflito ou dicas rápidas.
   - Estrutura: Gancho -> Erro -> Tese -> Explicação -> Fechamento.

2. [Zona Ideal] (7 a 9 Slides) -> **PREFERÊNCIA PADRÃO**:
   - Use para: A maioria dos temas virais.
   - Estrutura: Ato 1 (Choque) -> Ato 2 (Conflito + Explicação) -> Ato 3 (Síntese).

3. [Nível Blindado] (10 a 12 Slides)
  - Use para: Quebrar mitos muito fortes ou temas polêmicos que exigem muita defesa ("blindagem").

  
*REGRA DE OURO:* Cada slide deve ter uma "virada de pensamento". Se o raciocínio acabou, o carrossel acaba. Não encha linguiça.

## SUAS FERRAMENTAS (GATILHOS):
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
- NÃO copiar completamente o conteúdo, se for transcrição de vídeo, parafraseie, reescreva

## FORMATO DE SAÍDA (JSON OBRIGATÓRIO):
Retorne APENAS um objeto JSON.

{
  "meta_dados": {
    "tema": "Tema recebido",
    "complexidade_detectada": "Simples/Ideal/Blindado",
    "total_slides": 0
  },
  "carrossel": [
    {
      "painel": 1,
      "fase": "Gancho",
      "texto": "Texto aqui...",
      "nota_engenharia": "[Gatilho] Explicação..."
    }
  ]
}
"""

# --- FUNÇÕES AUXILIARES ---

def limpar_json(texto):
    """Limpa de forma CIRÚRGICA para garantir JSON válido."""
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

def get_youtube_metadata(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "id_unico": info.get('id'),
                "perfil": info.get('uploader') or info.get('channel'),
                "data_postagem": info.get('upload_date'),
                "views": info.get('view_count'),
                "likes": info.get('like_count'),
                "comments": info.get('comment_count'),
                "title": info.get('title'),
                "caption": info.get('description', '')
            }
    except:
        return {}

def download_youtube_audio(url, cookies_content=None):
    """
    Baixa áudio do YouTube com Cookies e Headers para evitar erro 403.
    """
    output_filename = "temp_yt_audio"
    cookie_file = "cookies_temp.txt"
    use_cookies = False
    
    # Prepara o arquivo de cookies
    if cookies_content and len(cookies_content) > 50:
        with open(cookie_file, "w") as f:
            f.write(cookies_content)
        use_cookies = True
    
    # Configuração BLINDADA do yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best', # Tenta o melhor áudio, se falhar, pega o melhor geral
        'outtmpl': output_filename,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False, # Mudei para False para ver logs se precisar
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True, # Não trava se der erro num formato específico
        
        # Headers para fingir ser um Chrome Windows (deve bater com seus cookies)
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        }
    }

    if use_cookies:
        ydl_opts['cookiefile'] = cookie_file
    else:
        # Se não tem cookies, usa a tática da TV
        ydl_opts['extractor_args'] = {
            'youtube': {'player_client': ['android', 'web']}
        }

    try:
        st.info(f"🔄 Baixando YouTube... ({'Com Cookies' if use_cookies else 'Sem Cookies'})")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Verifica se baixou o MP3
        final_filename = f"{output_filename}.mp3"
        if os.path.exists(final_filename):
            if os.path.exists(cookie_file): os.remove(cookie_file)
            return final_filename
            
        # Fallback: Às vezes o yt-dlp baixa mas não converte se o ffmpeg falhar
        if os.path.exists(output_filename):
            if os.path.exists(cookie_file): os.remove(cookie_file)
            return output_filename

        return None

    except Exception as e:
        if os.path.exists(cookie_file): os.remove(cookie_file)
        st.error(f"❌ Erro yt-dlp: {e}")
        return None
   
def get_instagram_data_apify(url):
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
        prompt_user = f"Analise este conteúdo e gere 3 conceitos:\n\nCONTEÚDO BASE:\n{conteudo_base[:12000]}" # Aumentei o contexto
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
    Gera o roteiro em JSON usando a transcrição COMPLETA (ou quase completa)
    para evitar alucinações.
    """
    try:
        prompt_user = f"""
        INSTRUÇÃO CRÍTICA: Baseie-se ESTRITAMENTE na transcrição/conteúdo abaixo para criar o roteiro.
        Não invente fatos que não estejam no texto base.
        
        === CONTEÚDO ORIGINAL (TRANSCRIÇÃO) ===
        "{conteudo_base[:12000]}" 
        =======================================
        
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
            max_tokens=2048, # Aumentei para garantir resposta completa
            response_format={"type": "json_object"}
        )
        
        texto_limpo = limpar_json(completion.choices[0].message.content)
        return json.loads(texto_limpo)
    except Exception as e:
        st.error(f"Erro na IA Arquiteto: {e}")
        return None

# --- INTERFACE PRINCIPAL ---
# --- INTERFACE PRINCIPAL & SIDEBAR ---

# 1. Sidebar de Cookies (Para resolver o erro do YouTube)
with st.sidebar:
    st.header("⚙️ Configurações YouTube")
    youtube_cookies = st.text_area(
        "🍪 Cookies (Anti-Bloqueio)", 
        placeholder="Cole o conteúdo do arquivo cookies.txt aqui...",
        help="Use a extensão 'Get cookies.txt LOCALLY' no Chrome para pegar seus cookies logado no YouTube."
    )

# 2. Escolha do Conteúdo (APENAS UMA VEZ)
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
        
        aba_alvo = "Youtube" if tipo_conteudo == "YouTube" else "instagram"
        transcricao_db = None
        
        # 2. VERIFICA SE JÁ EXISTE (ECONOMIA DE CRÉDITOS)
        if gs_client:
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
                meta = get_youtube_metadata(url_input)
                dados_para_salvar = {
                    "id_unico": meta.get('id_unico', ''),
                    "perfil": meta.get('perfil', ''),
                    "data_postagem": meta.get('data_postagem', ''),
                    "url": url_input,
                    "views": meta.get('views', 0),
                    "likes": meta.get('likes', 0),
                    "comments": meta.get('comments', 0),
                    "caption": meta.get('caption', '') 
                }
                
                status.write("⬇️ Baixando áudio...")
                # Passa os cookies da sidebar
                f = download_youtube_audio(url_input, youtube_cookies)
                if f:
                    status.write("👂 Transcrevendo (Groq)...")
                    texto_extraido = transcrever_audio_groq(f)
                    if os.path.exists(f): os.remove(f)
                    
            elif tipo_conteudo in ["Reels (Instagram)", "Carrossel (Instagram)"]:
                status.write("🕵️ Acessando Apify...")
                data = get_instagram_data_apify(url_input)
                
                if data:
                    dados_para_salvar = {
                        "id_unico": data.get('id', ''),
                        "perfil": data.get('ownerUsername', ''),
                        "data_postagem": data.get('timestamp', '')[:10],
                        "url": url_input,
                        "views": data.get('videoViewCount') or data.get('playCount', 0),
                        "likes": data.get('likesCount', 0),
                        "comments": data.get('commentsCount', 0),
                        "caption": data.get('caption', '') 
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

            # 4. SALVAMENTO NO BANCO
            if texto_extraido and gs_client:
                dados_para_salvar["transcricao"] = texto_extraido
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
                status.update(label="Erro na IA (Formato JSON)", state="error")
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