import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import shutil

# --- MOTOR: DrissionPage ---
from DrissionPage import ChromiumPage, ChromiumOptions

# --- BEÁLLÍTÁSOK ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
SEEN_FILE = "seen_ads.txt"
KEYWORDS_FILE = "keywords.txt"

# 🤫 CSENDES MÓD
# Ha új kulcsszót adsz hozzá, állítsd ezt True-ra egy kör erejéig!
# True = Elmenti a találatokat, de NEM küld Telegram üzenetet.
# False = Normál működés, küld üzenetet.
SILENT_MODE = True 

# URL-ek
URL_HA_SEARCH_BASE = "https://hardverapro.hu/aprok/keres.php?order=1&stext="
URL_MSZ = "https://www.menemszol.hu/aprohirdetes/page/1"

# --- KÖZÖS SEGÉDFÜGGVÉNYEK ---

def send_telegram(message):
    # Ha be van kapcsolva a Csendes Mód, akkor itt kilépünk küldés nélkül
    if SILENT_MODE:
        print("🤫 Csendes mód aktív: Üzenet kihagyva.")
        return

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

def load_keywords_by_site():
    """
    Beolvassa a keywords.txt-t és szétválogatja a szavakat.
    """
    keywords = {
        "hardverapro": [],
        "menemszol": []
    }
    
    defaults = {
        "hardverapro": ["mac mini"],
        "menemszol": ["elektron", "access", "virus", "focusrite"]
    }

    if not os.path.exists(KEYWORDS_FILE):
        print("⚠️ Nem található a keywords.txt, alapértelmezett szavakat használom.")
        return defaults
    
    try:
        current_section = None
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                if line.upper() == "[HARDVERAPRO]":
                    current_section = "hardverapro"
                    continue
                elif line.upper() == "[MENEMSZOL]":
                    current_section = "menemszol"
                    continue
                
                if current_section in keywords:
                    keywords[current_section].append(line.lower())
        
        if not keywords["hardverapro"]: keywords["hardverapro"] = defaults["hardverapro"]
        if not keywords["menemszol"]: keywords["menemszol"] = defaults["menemszol"]
            
        return keywords

    except Exception as e:
        print(f"Hiba a kulcsszavak olvasásakor: {e}")
        return defaults

# --- 1. HARDVERAPRÓ SCRAPER ---

def scrape_hardverapro(seen_ads, keywords):
    print("--- HardverApró ellenőrzése ---")
    
    ha_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://hardverapro.hu/"
    }

    for keyword in keywords:
        search_term = f'"{keyword}"'
        print(f"🔎 Keresés erre: {search_term}...")
        
        search_url = f"{URL_HA_SEARCH_BASE}{search_term}"
        
        try:
            response = requests.get(search_url, headers=ha_headers)
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

                # Cím ellenőrzés
                if keyword.lower() not in title.lower():
                    continue

                if full_link in seen_ads: continue 
                
                print(f"Új HA találat: {title}")
                msg = f"🍎 TALÁLAT (HardverApró - {keyword})!\n\n**{title}**\nÁr: {price}\n\nLink: {full_link}"
                
                # Itt hívjuk meg a küldést (ami ellenőrzi a SILENT_MODE-ot)
                send_telegram(msg)
                
                # De a mentés MINDIG megtörténik!
                save_seen_ad(full_link)
                seen_ads.add(full_link)
                new_count += 1
            
            print(f"  -> {new_count} új találat ennél a szónál.")
            time.sleep(2)

        except Exception as e:
            print(f"HIBA a HardverAprónál ({keyword}): {e}")

# --- 2. MENEMSZOL SCRAPER ---

def scrape_menemszol(seen_ads, keywords):
    print("--- Menemszol.hu ellenőrzése ---")
    
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
        
        # --- CLOUDFLARE ---
        if "Verify" in page.title or "Just a moment" in page.title:
            print("⚠️ Cloudflare gyanú! Megoldás indítása...")
            try:
                time.sleep(2) 
                cf_box = page.ele('@id=challenge-stage', timeout=2)
                if cf_box: cf_box.click() 
                verify_text = page.ele('text:Verify you are human', timeout=2)
                if verify_text: verify_text.click()
                time.sleep(5) 
            except: pass

        if "Just a moment" in page.title:
             print(f"❌ Cloudflare blokkol.")
        else:
            print("✅ Sikeresen betöltve!")
            
            soup = BeautifulSoup(page.html, 'html.parser')
            all_links = soup.find_all('a', href=True)
            print(f"  -> Az oldalon összesen {len(all_links)} db link van.")
            
            new_count = 0
            
            for link in all_links:
                href = link['href']
                text = link.get_text(" ", strip=True)
                
                if "/aprohirdetes/" not in href: continue
                ignore_list = ["/category/", "/page/", "?sort", "&sort", "do=markRead", "/profile/"]
                if any(x in href for x in ignore_list): continue
                if not text or len(text) < 3: continue

                if not any(word in text.lower() for word in keywords): continue
                if href in seen_ads: continue

                print(f"Új Menemszol találat: {text}")
                msg = f"🎹 TALÁLAT (Menemszol)!\n\n**{text}**\n\nLink: {href}"
                
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
    all_keywords = load_keywords_by_site()
    
    scrape_hardverapro(seen_ads_memory, all_keywords['hardverapro'])
    print("-" * 30)
    scrape_menemszol(seen_ads_memory, all_keywords['menemszol'])
