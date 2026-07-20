import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def crear_hoja_prueba():
    # 1. Cargar el token desde el archivo local
    with open('token.json', 'r') as f:
        token_data = json.load(f)

    # 2. Cargar credenciales
    creds = Credentials.from_authorized_user_info(token_data)

    # 3. Construir servicio de Sheets
    service = build('sheets', 'v4', credentials=creds)

    # 4. Crear la hoja
    spreadsheet = {
        'properties': {
            'title': 'Hoja de Prueba desde API'
        }
    }
    sheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    
    print(f"ÉXITO: Hoja creada con ID: {sheet.get('spreadsheetId')}")
    print(f"Link: https://docs.google.com/spreadsheets/d/{sheet.get('spreadsheetId')}/edit")

if __name__ == '__main__':
    crear_hoja_prueba()