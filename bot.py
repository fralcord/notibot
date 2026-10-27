import os
import urllib.parse
import xml.etree.ElementTree as ET
import requests

# ================= CONFIGURACIÓN =================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Modifica o agrega los términos específicos de tu región
TEMAS_DE_INTERES = [
    "Gobierno Regional Los Lagos",
    "GORE Los Lagos",
    "Gobierno Regional",
]

ARCHIVO_HISTORIAL = "historial.txt"
# =================================================

def cargar_historial():
    """Carga los IDs de las noticias enviadas anteriormente."""
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return set()
    with open(ARCHIVO_HISTORIAL, "r") as f:
        return set(line.strip() for line in f)

def guardar_historial(nuevos_ids):
    """Guarda los nuevos IDs al final del archivo."""
    with open(ARCHIVO_HISTORIAL, "a") as f:
        for gid in nuevos_ids:
            f.write(f"{gid}\n")

def enviar_telegram(mensaje):
    """Envía un mensaje de texto a Telegram."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[ERROR] Credenciales de Telegram no configuradas.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR Telegram] Código: {response.status_code} - Respuesta: {response.text}")
            return False
        return True
    except requests.RequestException as e:
        print(f"[ERROR] Conexión con Telegram: {e}")
        return False

def buscar_noticias_rss(tema, historial):
    """Consulta el feed RSS enfocado en Chile (gl=CL) y filtra repetidas."""
    tema_enc = urllib.parse.quote(tema)
    # gl=CL y ceid=CL:es-419 filtran resultados para Chile
    url_rss = f"https://news.google.com/rss/search?q={tema_enc}&hl=es-419&gl=CL&ceid=CL:es-419"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    nuevas_noticias = []
    nuevos_ids = []

    try:
        respuesta = requests.get(url_rss, headers=headers, timeout=10)
        if respuesta.status_code != 200:
            print(f"[AVISO] Código HTTP {respuesta.status_code} al consultar: {tema}")
            return nuevas_noticias, nuevos_ids

        raiz = ET.fromstring(respuesta.content)
        
        # Filtra las 4 más recientes por tema
        for item in raiz.findall(".//item")[:4]:
            titulo = item.find("title").text if item.find("title") is not None else "Sin título"
            link = item.find("link").text if item.find("link") is not None else ""
            guid = item.find("guid").text if item.find("guid") is not None else link

            if guid not in historial:
                nuevas_noticias.append({"titulo": titulo, "enlace": link})
                nuevos_ids.append(guid)
                historial.add(guid)

        return nuevas_noticias, nuevos_ids
    except Exception as e:
        print(f"[ERROR] Procesando '{tema}': {e}")
        return [], []

def main():
    print("Iniciando revisión de noticias regionales...")
    historial = cargar_historial()
    ids_a_guardar = []

    for tema in TEMAS_DE_INTERES:
        print(f"Consultando: {tema}")
        noticias, nuevos_ids = buscar_noticias_rss(tema, historial)
        
        if noticias:
            ids_a_guardar.extend(nuevos_ids)
            mensaje = f"🏛️ *NOVEDADES: {tema.upper()}*\n\n"
            for item in noticias:
                titulo_limpio = item["titulo"].rsplit(" - ", 1)[0]
                mensaje += f"🔹 {titulo_limpio}\n🔗 [Leer nota]({item['enlace']})\n\n"
            
            enviado = enviar_telegram(mensaje)
            if enviado:
                print(f"Mensaje enviado con éxito para: {tema}")
        else:
            print(f"Sin novedades nuevas para: {tema}")

    if ids_a_guardar:
        guardar_historial(ids_a_guardar)
        print(f"Se guardaron {len(ids_a_guardar)} noticias en historial.txt.")

if __name__ == "__main__":
    main()
