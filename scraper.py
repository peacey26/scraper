import requests
from bs4 import BeautifulSoup
import os
import sys

# --- BEÁLLÍTÁSOK ---
TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
SEEN_FILE = "seen_ads_v3.txt" # Új verzió, tiszta lappal!
URL = "https://hardverapro.hu/aprok/pc_szerver/apple_mac_imac/mac_mini/index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": "https://hardverapro.hu/"
}

def send_telegram(message):
    print(f"Üzenet küldése Telegramra: {message[:20]}...")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print("✅ Telegram üzenet elküldve!")
        else:
            print(f"❌ Telegram hiba: {r.text}")
    except Exception as e:
        print(f"❌ Hiba a küldésnél: {e}")

def scrape():
    print("--- DIAGNOSZTIKA INDÍTÁSA ---")
    
    # 1. TESZT: Telegram teszt (hogy kizárjuk a bot hibát)
    # Ezt az első futásnál küldi, csak hogy lássuk, működik-e a "cső".
    # Ha ez megjön, akkor a bot jó, és a scraping a rossz.
    # send_telegram("🤖 HardverApró Bot: Teszt üzenet - A rendszer él!")

    try:
        response = requests.get(URL, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        ads = soup.find_all('li', class_='media')
        print(f"Talált hirdetés blokkok száma: {len(ads)}")

        if len(ads) == 0:
            print("VÉGZETES HIBA: Nem találok hirdetéseket. Az oldal tartalma:")
            print(soup.prettify()[:1000]) # Kiírjuk az oldal elejét
            return

        # 2. TESZT: Nézzük meg az ELSŐ hirdetés belsejét!
        print("\n--- ELSŐ HIRDETÉS ELYMZÉSE ---")
        first_ad = ads[0]
        print(first_ad.prettify()) # EZ A LÉNYEG! Ebből látjuk a struktúrát.
        print("------------------------------\n")

        new_count = 0
        
        for i, ad in enumerate(ads):
            # Próbáljuk megkeresni a címet többféle módon
            title_element = ad.find('div', class_='uad-title')
            
            if not title_element:
                # HA HIBA VAN: Kiírjuk, hanyadiknál hasalt el
                if i < 3: print(f"⚠️ {i+1}. hirdetés: Nem találom a 'uad-title' div-et!")
                continue
            
            link_tag = title_element.find('a')
            if not link_tag:
                if i < 3: print(f"⚠️ {i+1}. hirdetés: Megvan a div, de nincs benne 'a' (link)!")
                continue

            title = link_tag.get_text().strip()
            link = link_tag['href']
            full_link = f"https://hardverapro.hu{link}"
            
            # Ár keresése
            price_div = ad.find('div', class_='uad-price')
            price = price_div.get_text().strip() if price_div else "Nincs ár"

            # Ha idáig eljut, akkor SIKERES az olvasás
            if i < 3: print(f"✅ {i+1}. hirdetés feldolgozva: {title} ({price})")

            # Küldés (most fájl ellenőrzés nélkül, hogy biztosan jöjjön)
            # Csak az első 3-at küldjük el tesztnek, hogy ne spammeljen szét
            if new_count < 3:
                msg = f"🔍 DIAGNOSZTIKA:\n{title}\n{price}\n{full_link}"
                send_telegram(msg)
                new_count += 1

        print(f"\nÖsszesen {new_count} üzenet elküldve a teszt során.")

    except Exception as e:
        print(f"KRITIKUS HIBA: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    scrape()
