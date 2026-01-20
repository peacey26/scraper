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

# FRISSÍTETT ÁLCÁZÁS (Hogy igazi Mac-nek tűnjön)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
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
    print("HardverApró figyelése...")
    seen_ads = load_seen_ads()
    
    try:
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # DEBUG: Írjuk ki az oldal címét, hogy lássuk, nem-e blokkoltak
        page_title = soup.title.get_text().strip() if soup.title else "Nincs cím"
        print(f"Az oldal címe amit látok: {page_title}")

        # A hirdetések listája (li elemek 'media' osztállyal)
        ads = soup.find_all('li', class_='media')
        print(f"Talált hirdetések száma: {len(ads)}")

        if len(ads) == 0:
            print("!!! NEM TALÁLTAM HIRDETÉST. LEHET HOGY BLOKKOLTAK? !!!")
            # Kiírjuk az oldal elejét, hogy lássuk mi ez
            print("Az oldal eleje:\n", response.text[:500])
        
        new_count = 0
        
        for ad in ads:
            title_element = ad.find('div', class_='uad-title')
            if not title_element: continue
            
            link_tag = title_element.find('a')
            if not link_tag: continue

            title = link_tag.get_text().strip()
            link = link_tag['href']
            full_link = f"https://hardverapro.hu{link}"

            price_div = ad.find('div', class_='uad-price')
            price = price_div.get_text().strip() if price_div else "Nincs ár"

            if full_link in seen_ads:
                continue 
            
            print(f"Új hirdetés: {title}")
            msg = f"🍎 Új Mac Mini hirdetés!\n\n**{title}**\nÁr: {price}\n\nLink: {full_link}"
            send_telegram(msg)
            
            save_seen_ad(full_link)
            seen_ads.add(full_link)
            new_count += 1

        if new_count == 0 and len(ads) > 0:
            print("Nem volt új hirdetés (már mindet láttuk).")
        elif new_count > 0:
            print(f"{new_count} új hirdetés elküldve.")

    except Exception as e:
        print(f"Hiba történt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    scrape()
