import webbrowser
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
import json

# 1. Registrar Firefox
firefox_path = 'C:/Program Files/Mozilla Firefox/firefox.exe %s'
webbrowser.register('firefox', None, webbrowser.BackgroundBrowser(firefox_path))

# 2. Configurar flujo
CLIENT_SECRETS_FILE = "client_secret.json" 
flow = InstalledAppFlow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
)

# 3. Importante: Establecemos el redirect_uri manualmente para que coincida con tu consola
flow.redirect_uri = 'http://localhost:8080/'

# 4. Generamos la URL de autorización
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

# 5. Abrimos Firefox manualmente
print("Abriendo Firefox para la autenticación...")
webbrowser.get('firefox').open(auth_url)

# 6. Ejecutamos el servidor local SIN que abra el navegador automáticamente
# Usamos 'open_browser=False' para que no intente usar Chrome
creds = flow.run_local_server(port=8080, open_browser=False)

# 7. Guardar token
with open('token.json', 'w') as f:
    f.write(creds.to_json())

print("\n¡Éxito! Token guardado correctamente en token.json")
