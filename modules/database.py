import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def conectar_sheets():
    """Conecta e retorna a ABA PADRÃO para compatibilidade, mas permite acesso global."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Tenta abrir a aba instagram padrão só para retornar um objeto válido
        # Mas o importante é o objeto 'client' ou 'spreadsheet'
        try:
            sh = client.open("DB_E21_Conteudos")
            try:
                sheet = sh.worksheet("instagram")
            except:
                sheet = sh.add_worksheet(title="instagram", rows="1000", cols="20")
            return sheet
        except Exception as e:
            st.error(f"Erro ao abrir planilha: {e}")
            return None
    except Exception as e:
        st.error(f"Erro credenciais: {e}")
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
    """Verifica se URL existe na aba específica."""
    try:
        spreadsheet = sheet_obj.spreadsheet
        
        # 1. Tenta pegar a aba, se não existir, cria com os cabeçalhos certos
        try:
            worksheet = spreadsheet.worksheet(aba_nome)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=aba_nome, rows="1000", cols="20")
            
            # CABEÇALHOS PERSONALIZADOS POR ABA
            if aba_nome == "instagram":
                # Reels/Posts
                header = ["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Gancho_Verbal", "Legenda"]
            elif aba_nome == "carrossel":
                # NOVO: Carrossel
                header = ["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Carrossel", "Legenda"]
            else:
                # Youtube
                header = ["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Legenda"]
            
            worksheet.append_row(header)
        
        # 2. Busca URL
        try:
            cell = worksheet.find(url_input)
            if cell:
                row_values = worksheet.row_values(cell.row)
                # Retorna a transcrição (Coluna I = índice 8)
                if len(row_values) >= 9:
                    return row_values[8] 
        except gspread.exceptions.CellNotFound:
            return None
            
        return None
    except Exception as e:
        if "attribute" in str(e): st.error(f"Erro DB: {e}")
        return None

def salvar_no_db(sheet_obj, aba_nome, dados):
    """Salva nova linha na aba específica."""
    try:
        spreadsheet = sheet_obj.spreadsheet
        worksheet = spreadsheet.worksheet(aba_nome)
        
        def safe_str(key): return str(dados.get(key, "") or "")
        def safe_int(key): return int(dados.get(key, 0) or 0)
        
        # Limpa legenda para não quebrar o CSV/Excel
        legenda_limpa = safe_str("caption").replace("\t", " ").replace("\n", " ")[:4000] 

        if aba_nome == "instagram":
            row = [
                safe_str("id_unico"), datetime.now().strftime("%d/%m/%Y"), safe_str("perfil"),
                safe_str("data_postagem"), safe_str("url"), safe_int("views"), safe_int("likes"),
                safe_int("comments"), safe_str("transcricao"), safe_str("gancho_verbal"), legenda_limpa
            ]
        elif aba_nome == "carrossel":
            # LÓGICA NOVA PARA CARROSSEL
            row = [
                safe_str("id_unico"), datetime.now().strftime("%d/%m/%Y"), safe_str("perfil"),
                safe_str("data_postagem"), safe_str("url"), safe_int("views"), safe_int("likes"),
                safe_int("comments"), safe_str("transcricao"), legenda_limpa
            ]
        else: # Youtube
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