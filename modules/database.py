# modules/database.py
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def conectar_sheets():
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
            
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        return None

def carregar_ids_existentes(sheet):
    try:
        ids = sheet.col_values(1)
        if ids and ids[0] == "ID_Unico":
            return set(ids[1:])
        return set(ids)
    except Exception as e:
        return set()

def salvar_linha_instagram(sheet, dados):
    """Função para salvar linha padronizada"""
    try:
        sheet.append_row(dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False
    
def verificar_existencia_db(client, aba_nome, url_input):
    """Verifica se URL existe e retorna transcrição"""
    try:
        try:
            sh = client.open("DB_E21_Conteudos")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ A planilha 'DB_E21_Conteudos' não foi encontrada.")
            return None
            
        try:
            worksheet = sh.worksheet(aba_nome)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=aba_nome, rows="1000", cols="20")
            if aba_nome == "instagram":
                worksheet.append_row(["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Gancho_Verbal", "Legenda"])
            else:
                worksheet.append_row(["ID_Unico", "Data_Coleta", "Perfil", "Data_Postagem", "URL_Original", "Views", "Likes", "Comments", "Transcricao_Whisper", "Legenda"])
        
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
        if "already exists" in str(e): return None
        st.warning(f"Aviso DB: {e}")
        return None

def salvar_no_db(client, aba_nome, dados):
    """Salva nova linha na planilha"""
    try:
        sh = client.open("DB_E21_Conteudos")
        worksheet = sh.worksheet(aba_nome)
        
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