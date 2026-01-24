import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def conectar_sheets():
    """Conecta e retorna a ABA PADRÃO (Instagram) para compatibilidade."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        nome_planilha = "DB_E21_Conteudos"
        nome_aba = "instagram"
        
        try:
            sh = client.open(nome_planilha)
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Planilha '{nome_planilha}' não encontrada.")
            return None

        try:
            sheet = sh.worksheet(nome_aba)
        except:
            sheet = sh.add_worksheet(title=nome_aba, rows="1000", cols="15")
            sheet.append_row([
                "ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", 
                "URL_Original", "Views", "Likes", "Comments", 
                "Transcricao_Whisper", "Gancho_Verbal", "Legenda"
            ])
            
        return sheet # Retorna um objeto Worksheet
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        return None

def carregar_ids_existentes(sheet):
    """Lê IDs da aba fornecida."""
    try:
        ids = sheet.col_values(1)
        if ids and ids[0] == "ID_Unico":
            return set(ids[1:])
        return set(ids)
    except Exception as e:
        return set()

def salvar_linha_instagram(sheet, dados):
    """Salva linha direta (usado na página 01)."""
    try:
        sheet.append_row(dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- FUNÇÕES CORRIGIDAS PARA O GERADOR DE CARROSSEL (PÁGINA 04) ---

def verificar_existencia_db(sheet_obj, aba_nome, url_input):
    """
    Verifica URL. 
    Correção: Usa sheet_obj.spreadsheet para navegar, já que sheet_obj é uma aba.
    """
    try:
        # Pega a planilha 'mãe' da aba atual
        spreadsheet = sheet_obj.spreadsheet 
            
        try:
            worksheet = spreadsheet.worksheet(aba_nome)
        except gspread.exceptions.WorksheetNotFound:
            # Cria aba se não existir
            worksheet = spreadsheet.add_worksheet(title=aba_nome, rows="1000", cols="20")
            colunas = ["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Legenda"]
            if aba_nome == "instagram":
                colunas.insert(9, "Gancho_Verbal") # Insere na posição correta
            worksheet.append_row(colunas)
        
        # Busca a URL na coluna de Links (geralmente coluna 5)
        # O método find procura na planilha toda, é mais seguro
        try:
            cell = worksheet.find(url_input)
            if cell:
                row_values = worksheet.row_values(cell.row)
                # Retorna a transcrição (Coluna I = índice 8)
                if len(row_values) >= 9:
                    return row_values[8] 
        except gspread.exceptions.CellNotFound:
            return None
        except Exception as e:
            return None
            
        return None
    except Exception as e:
        # Ignora erro se for só 'não achei'
        if "attribute" in str(e):
            st.error(f"Erro de conexão DB: {e}")
        return None

def salvar_no_db(sheet_obj, aba_nome, dados):
    """
    Salva nova linha.
    Correção: Usa sheet_obj.spreadsheet para acessar a aba correta.
    """
    try:
        spreadsheet = sheet_obj.spreadsheet
        worksheet = spreadsheet.worksheet(aba_nome)
        
        def safe_str(key): return str(dados.get(key, "") or "")
        def safe_int(key): return int(dados.get(key, 0) or 0)
        
        legenda_limpa = safe_str("caption").replace("\t", " ").replace("\n", " ")[:4000] 

        if aba_nome == "instagram":
            row = [
                safe_str("id_unico"), datetime.now().strftime("%d/%m/%Y"), safe_str("perfil"),
                safe_str("data_postagem"), safe_str("url"), safe_int("views"), safe_int("likes"),
                safe_int("comments"), safe_str("transcricao"), safe_str("gancho_verbal"), legenda_limpa
            ]
        else:
            row = [
                safe_str("id_unico"), datetime.now().strftime("%d/%m/%Y"), safe_str("perfil"),
                safe_str("data_postagem"), safe_str("url"), safe_int("views"), safe_int("likes"),
                safe_int("comments"), safe_str("transcricao"), legenda_limpa
            ]
            
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no BD: {e}")
        return False