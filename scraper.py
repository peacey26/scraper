import requests
from bs4 import BeautifulSoup
import os
import sys

# --- BEÁLLÍTÁSOK ---
TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
# Visszatérünk az eredeti fájlnévhez, hogy tiszta legyen
SEEN_FILE = "seen_ads.txt" 
URL = "https://hardverapro.hu/aprok/pc_szerver/apple_mac_imac/mac_mini/index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": "https://hardverapro.hu/"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Hiba üzenetküldéskor: {e}")

def load_seen_ads():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_seen_ad(ad_url):
    with open(SEEN_FILE, "a") as f:
        f.write(ad_url + "\n")

def scrape():
    print("HardverApró figyelése (Javított Selector)...")
    seen_ads = load_seen_ads()
    
    try:
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Hirdetések keresése
        ads = soup.find_all('li', class_='media')
        print(f"Talált hirdetések száma: {len(ads)}")
        
        new_count = 0
        
        for ad in ads:
            # --- ITT VOLT A HIBA: A 'uad-title' helyett 'uad-col-title' kell ---
            title_div = ad.find('div', class_='uad-col-title')
            
            if not title_div:
                continue # Ha nincs címe, átugorjuk
            
            link_tag = title_div.find('a')
            if not link_tag:
                continue

            title = link_tag.get_text().strip()
            link = link_tag['href']
            
            # Link javítása: Ha nem teljes link, kiegészítjük, ha teljes, hagyjuk
            if link.startswith("http"):
                full_link = link
            else:
                full_link = f"https://hardverapro.hu{link}"

            # Ár keresése
            price_div = ad.find('div', class_='uad-price')
            price = price_div.get_text().strip() if price_div else "Nincs ár"

            # Ellenőrzés: Láttuk már?
            if full_link in seen_ads:
                continue 
            
            # Küldés
            print(f"Új találat: {title}")
            msg = f"🍎 Új Mac Mini hirdetés!\n\n**{title}**\nÁr: {price}\n\nLink: {full_link}"
            send_telegram(msg)
            
            save_seen_ad(full_link)
            seen_ads.add(full_link)
            new_count += 1

        print(f"Futás vége. {new_count} új hirdetés elküldve.")

    except Exception as e:
        print(f"KRITIKUS HIBA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    scrape()
