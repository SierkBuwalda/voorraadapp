import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'credentials/credentials.json'
SHEET_ID = '1t5GqCNNbiBVNbfxkrKA8jgu98ZSO-aQNy8NegHcrFGA'  # dit is jouw sheet

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)
    tabs = [ws.title for ws in sheet.worksheets()]
    print("✅ Verbonden met Google Sheet!")
    print("📄 Beschikbare tabbladen:", tabs)
except Exception as e:
    print("❌ Fout bij verbinden met Google Sheet:")
    print(e)
