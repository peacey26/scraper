import requests
from bs4 import BeautifulSoup
import os
import sys

# KÖRNYEZETI VÁLTOZÓK BETÖLTÉSE (GitHub Secrets-ből)
TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# EZT A LINKET ÍRD ÁT ARRA, AMIT FIGYELNI AKARSZ:
URL = "https://www.arukereso.hu/videokartya-c3142/asus/geforce-rtx-3060-12gb-gddr6-192bit-dual-rtx3060-o12g-v2-p663414923/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Hiba az üzenet küldésekor: {e}")

def scrape():
    print(f"Lekérdezés indítása: {URL}")
    try:
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- ITT KELL MEGADNI MIT KERESÜNK ---
        # Árukereső példa: Az ár általában a "price" osztályban van, vagy az xl-price-ban.
        # Jobb klikk az áron a böngészőben -> Vizsgálat -> nézd meg a class nevét.
        
        # Ez egy általános keresés az oldal címére (tesztnek):
        title = soup.find('h1').get_text().strip()
        print(f"Találat: {title}")
        
        # Üzenet küldése
        send_telegram_message(f"🔔 A Scraper lefutott!\nTermék: {title}\nLink: {URL}")
        
    except Exception as e:
        print(f"Hiba történt: {e}")
        send_telegram_message(f"⚠️ Hiba a scraperben: {e}")
        sys.exit(1)

if __name__ == "__main__":
    scrape()
