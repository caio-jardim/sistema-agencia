import streamlit as st
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from groq import Groq

# Configuração da Página
st.set_page_config(page_title="Fábrica de Roteiros", page_icon="📝")

st.title("🏭 Fábrica de Roteiros Virais")
st.markdown("---")

# --- CONFIGURAÇÕES NA BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Inputs que antes eram variáveis fixas
    TEMA_MACRO = st.text_input("Tema do Conteúdo", value="Holding Familiar")
    CTA_PADRAO = st.text_area("Chamada para Ação (CTA)", value="Comente 'OURO' para receber o guia gratuito.")
    NOME_PLANILHA = st.text_input("Nome da Planilha", value="Conteudo")
    
    st.info("As credenciais estão sendo lidas do arquivo secrets.toml")

# --- FUNÇÕES (Lógica Original Preservada) ---

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # ADAPTAÇÃO: Lê do st.secrets em vez do arquivo json físico
    # Criamos um dicionário com as infos que estariam no JSON
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open(NOME_PLANILHA).sheet1
        headers = sheet.row_values(1)
        if "Novo Roteiro Viral" not in headers:
            sheet.update_cell(1, len(headers) + 1, "Novo Roteiro Viral")
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return None

def gerar_roteiro_inteligente(transcricao_original, gancho_original, client_groq):
    # Prompt idêntico ao original
    prompt = f"""
    Você é um Estrategista de Conteúdo Viral e Copywriter de Elite.
    
    CONTEXTO:
    Estamos analisando um vídeo que viralizou no Instagram.
    Seu objetivo NÃO é copiar o conteúdo, mas roubar a "Estrutura Lógica" e a "Psicologia" dele para criar um novo roteiro sobre o tema: "{TEMA_MACRO}".

    DADOS DO VÍDEO VIRAL (ORIGEM):
    - Gancho que funcionou: "{gancho_original}"
    - Conteúdo falado: "{transcricao_original[:2000]}" (Resumo)

    SUA MISSÃO:
    1. Identifique o GATILHO MENTAL do viral (Foi medo? Curiosidade? "Você está fazendo errado"? Promessa de ganho fácil?).
    2. Crie um NOVO ROTEIRO sobre "{TEMA_MACRO}" usando exatamente esse mesmo gatilho, mas com palavras e exemplos diferentes.
    
    ESTRATÉGIA: (Explique em 1 frase).
    NOVO GANCHO (0-3s): (Curto e polêmico).
    DESENVOLVIMENTO: (Ensine sobre Holding Familiar).
    FINALIZAÇÃO: (Use exatamente: "{CTA_PADRAO}").
    """

    try:
        completion = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erro na geração: {e}"

# --- BOTÃO DE AÇÃO ---
if st.button("🚀 Iniciar Geração de Roteiros", type="primary"):
    
    # Inicializa Groq com a chave dos segredos
    if "groq_api_key" in st.secrets:
        client_groq = Groq(api_key=st.secrets["groq_api_key"])
    else:
        st.error("Chave da Groq não encontrada no secrets.toml")
        st.stop()

    sheet = conectar_sheets()
    
    if sheet:
        rows = sheet.get_all_values()
        headers = rows[0]
        
        try:
            idx_transcricao = headers.index("Transcrição")
            idx_gancho = headers.index("Gancho Verbal")
            idx_novo_roteiro = len(headers)
            if "Novo Roteiro Viral" in headers:
                idx_novo_roteiro = headers.index("Novo Roteiro Viral")
        except ValueError:
            st.error("❌ Colunas 'Transcrição' ou 'Gancho Verbal' não encontradas.")
            st.stop()

        # Barra de progresso visual
        progresso_texto = "Iniciando processamento..."
        barra_progresso = st.progress(0, text=progresso_texto)
        total_linhas = len(rows) - 1
        linhas_processadas = 0

        st.write(f"📊 Analisando {total_linhas} linhas...")
        
        # Container para logs em tempo real
        log_container = st.container()

        for i in range(1, len(rows)):
            row_num = i + 1
            linha = rows[i]
            
            transcricao = linha[idx_transcricao] if len(linha) > idx_transcricao else ""
            gancho = linha[idx_gancho] if len(linha) > idx_gancho else ""
            roteiro_existente = linha[idx_novo_roteiro] if len(linha) > idx_novo_roteiro else ""
            
            status_msg = ""
            
            if transcricao and len(transcricao) > 50 and not roteiro_existente:
                with log_container:
                    st.toast(f"Gerando roteiro da linha {row_num}...", icon="🤖")
                
                novo_roteiro = gerar_roteiro_inteligente(transcricao, gancho, client_groq)
                
                sheet.update_cell(row_num, idx_novo_roteiro + 1, novo_roteiro)
                
                with log_container:
                    st.success(f"✅ Linha {row_num}: Roteiro criado!")
                    with st.expander(f"Ver Roteiro {row_num}"):
                        st.write(novo_roteiro)
                
                time.sleep(3) # Respeitando delay da Groq
            else:
                # Opcional: mostrar logs de pulo
                pass

            # Atualiza barra
            linhas_processadas += 1
            percentual = int((linhas_processadas / total_linhas) * 100)
            barra_progresso.progress(percentual, text=f"Processando linha {row_num} de {len(rows)}...")

        st.success("🏁 Processo finalizado com sucesso!")
        st.balloons()