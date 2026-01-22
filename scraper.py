import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import shutil

# --- ÚJ MOTOR: DrissionPage ---
from DrissionPage import ChromiumPage, ChromiumOptions

# --- BEÁLLÍTÁSOK ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
SEEN_FILE = "seen_ads.txt"

# URL-ek
URL_HA = "https://hardverapro.hu/aprok/pc_szerver/apple_mac_imac/mac_mini/index.html"

# KIZÁRÓLAG EZT AZ EGY OLDALT FIGYELJÜK:
URL_MSZ = "https://www.menemszol.hu/aprohirdetes/"

# --- KÖZÖS SEGÉDFÜGGVÉNYEK ---

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("Hiba: Nincs beállítva TELEGRAM_TOKEN vagy TELEGRAM_CHAT_ID")
        return
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

# --- 1. HARDVERAPRÓ SCRAPER ---

def scrape_hardverapro(seen_ads):
    print("--- HardverApró ellenőrzése ---")
    ha_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://hardverapro.hu/"
    }
    try:
        response = requests.get(URL_HA, headers=ha_headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        ads = soup.find_all('li', class_='media')
        new_count = 0
        for ad in ads:
            title_div = ad.find('div', class_='uad-col-title')
            if not title_div: continue
            link_tag = title_div.find('a')
            if not link_tag: continue
            title = link_tag.get_text().strip()
            link = link_tag['href']
            full_link = link if link.startswith("http") else f"https://hardverapro.hu{link}"
            price_div = ad.find('div', class_='uad-price')
            price = price_div.get_text().strip() if price_div else "Nincs ár"

            if full_link in seen_ads: continue 
            print(f"Új HA találat: {title}")
            msg = f"🍎 Új Mac Mini hirdetés!\n\n**{title}**\nÁr: {price}\n\nLink: {full_link}"
            send_telegram(msg)
            save_seen_ad(full_link)
            seen_ads.add(full_link)
            new_count += 1
        print(f"HA vége. {new_count} új hirdetés.")
    except Exception as e:
        print(f"HIBA a HardverAprónál: {e}")

# --- 2. MENEMSZOL SCRAPER (DrissionPage - LINK VADÁSZ MÓD) ---

def scrape_menemszol(seen_ads):
    print("--- Menemszol.hu ellenőrzése (Link Vadász Mód) ---")
    
    keywords = ['virus', 'access', 'elektron', 'focusrite']
    page = None
    
    try:
        print("Böngésző konfigurálása...")
        co = ChromiumOptions()
        co.set_argument('--no-sandbox')
        co.set_argument('--headless=new')
        co.set_argument('--disable-gpu')
        co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

        chrome_path = shutil.which("google-chrome") or shutil.which("chrome") or shutil.which("chromium")
        if chrome_path:
             co.set_paths(browser_path=chrome_path)

        page = ChromiumPage(co)
        print(f"Link megnyitása: {URL_MSZ}")
        page.get(URL_MSZ)
        
        # Cloudflare kezelés
        time.sleep(5)
        if "Verify" in page.title or "Just a moment" in page.title:
            print("⚠️ Cloudflare gyanú! Kísérlet a megoldásra...")
            try:
                cf_box = page.ele('@id=challenge-stage', timeout=2)
                if cf_box: cf_box.click() 
                verify_text = page.ele('text:Verify you are human', timeout=2)
                if verify_text: verify_text.click()
                time.sleep(10)
            except: pass

        if "Just a moment" in page.title:
             print(f"❌ Cloudflare blokkol. Kép mentése...")
             page.get_screenshot(path='debug_screenshot.png')
        else:
            print("✅ Sikeresen betöltve! HTML mentése debug célra...")
            
            # ELMENTJÜK A HTML-T, HOGY LÁSSUK MIT LÁT A ROBOT
            with open("debug_source.html", "w", encoding="utf-8") as f:
                f.write(page.html)

            # --- ÚJ KERESÉSI LOGIKA: LINK VADÁSZAT ---
            soup = BeautifulSoup(page.html, 'html.parser')
            
            # Megkeresünk MINDEN linket az oldalon
            all_links = soup.find_all('a', href=True)
            print(f"  -> Az oldalon összesen {len(all_links)} db link van.")
            
            new_count = 0
            
            for link in all_links:
                href = link['href']
                text = link.get_text(" ", strip=True) # A link szövege (pl. a hirdetés címe)
                
                # SZŰRÉS 1: Csak azokat nézzük, amik hirdetésre mutatnak ("/item/")
                # Ez a Menemszol hirdetések mintázata
                if "/aprohirdetes/item/" not in href:
                    continue
                
                # Ha a link szövege üres (pl. egy kép linkje), próbáljuk megkeresni a címet máshol
                if not text:
                    # Néha a linkben van egy img tag, de nekünk a szöveg kell.
                    # Ha üres, ugrunk.
                    continue

                # SZŰRÉS 2: Kulcsszó keresése a CÍMBEN (a link szövegében)
                if not any(word in text.lower() for word in keywords):
                    continue

                # SZŰRÉS 3: Duplikáció
                if href in seen_ads:
                    continue

                # Ha idáig eljutottunk, ez egy ÚJ TALÁLAT!
                print(f"Új Menemszol találat: {text}")
                
                # Megpróbáljuk megkeresni az árat (ez nehézkes, ha nem tudjuk a struktúrát,
                # de a cím és a link a lényeg!)
                price = "N/A (Kattints a linkre)"
                
                msg = f"🎹 TALÁLAT (Főoldali lista)!\n\n**{text}**\nÁr: {price}\n\nLink: {href}"
                send_telegram(msg)
                
                save_seen_ad(href)
                seen_ads.add(href)
                new_count += 1
            
            print(f"Menemszol vége. {new_count} új hirdetés.")

    except Exception as e:
        print(f"KRITIKUS HIBA a Menemszolnál: {e}")
    finally:
        if page:
            try:
                page.quit()
                print("Böngésző bezárva.")
            except:
                pass

# --- FŐ PROGRAM ---

if __name__ == "__main__":
    seen_ads_memory = load_seen_ads()
    scrape_hardverapro(seen_ads_memory)
    print("-" * 30)
    scrape_menemszol(seen_ads_memory)
