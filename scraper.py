import requests
from bs4 import BeautifulSoup
import os
import sys

# KÖRNYEZETI VÁLTOZÓK
TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
SEEN_FILE = "seen_ads.txt"

# A HardverApró Mac Mini oldala
URL = "https://hardverapro.hu/aprok/pc_szerver/apple_mac_imac/mac_mini/index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
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
    print("HardverApró figyelése...")
    seen_ads = load_seen_ads()
    
    try:
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # A hirdetések listája (li elemek 'media' osztállyal)
        ads = soup.find_all('li', class_='media')

        new_count = 0
        
        # Végigmegyünk a hirdetéseken
        for ad in ads:
            # Cím és Link keresése (általában a 'uad-title' osztályban van a link)
            title_element = ad.find('div', class_='uad-title')
            if not title_element: continue
            
            link_tag = title_element.find('a')
            if not link_tag: continue

            title = link_tag.get_text().strip()
            link = link_tag['href']
            
            # A link relatív (pl. /apro/...), ezért elé kell tenni a domaint
            full_link = f"https://hardverapro.hu{link}"

            # Ár keresése
            price_div = ad.find('div', class_='uad-price')
            price = price_div.get_text().strip() if price_div else "Nincs ár"

            # ELLENŐRZÉS: Láttuk már ezt a linket?
            if full_link in seen_ads:
                continue # Ha igen, ugorjunk a következőre
            
            # Ha nem láttuk, küldés és mentés
            print(f"Új hirdetés: {title}")
            msg = f"🍎 Új Mac Mini hirdetés!\n\n**{title}**\nÁr: {price}\n\nLink: {full_link}"
            send_telegram(msg)
            
            save_seen_ad(full_link)
            seen_ads.add(full_link) # Hozzáadjuk a memóriához a futás idejére is
            new_count += 1

        if new_count == 0:
            print("Nem volt új hirdetés.")
        else:
            print(f"{new_count} új hirdetés elküldve.")

    except Exception as e:
        print(f"Hiba történt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    scrape()
