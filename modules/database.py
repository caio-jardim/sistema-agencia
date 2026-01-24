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