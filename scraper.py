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

# 🌊 AUTOMATA ÁRVÍZVÉDELEM
FLOOD_LIMIT = 3 

# URL-ek
URL_HA_SEARCH_BASE = "https://hardverapro.hu/aprok/keres.php?order=1&stext="
URL_MSZ = "https://www.menemszol.hu/aprohirdetes/page/1"

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

def load_keywords_by_site():
    """
    Beolvassa a keywords.txt-t.
    - Kezeli a kikommentelt sorokat (#).
    - Kezeli a 'kulcsszó -- url' formátumot a HardverAprónál (DUPLA KÖTŐJEL).
    """
    keywords = {"hardverapro": [], "menemszol": []}
    defaults = {"hardverapro": [{"word": "mac mini", "url": None}], "menemszol": ["elektron"]}

    if not os.path.exists(KEYWORDS_FILE):
        return defaults
    
    try:
        current_section = None
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                
                # Üres sorok és KOMMENTEK (#) kihagyása
                if not line or line.startswith("#"): continue
                
                # Szekciók figyelése
                if line.upper() == "[HARDVERAPRO]":
                    current_section = "hardverapro"
                    continue
                elif line.upper() == "[MENEMSZOL]":
                    current_section = "menemszol"
                    continue
                
                if current_section == "hardverapro":
                    # HardverAprónál a " -- " elválasztót keressük (DUPLA KÖTŐJEL)
                    if " -- " in line:
                        parts = line.split(" -- ")
                        word = parts[0].strip().lower()
                        url = "".join(parts[1:]).strip()
                    else:
                        # Csak sima szó
                        word = line.strip().lower()
                        url = None
                        
                    keywords["hardverapro"].append({"word": word, "url": url})
                    
                elif current_section == "menemszol":
                    keywords["menemszol"].append(line.lower())
        
        if not keywords["hardverapro"]: keywords["hardverapro"] = defaults["hardverapro"]
        if not keywords["menemszol"]: keywords["menemszol"] = defaults["menemszol"]
        return keywords

    except Exception as e:
        print(f"Hiba a kulcsszavak olvasásakor: {e}")
        return defaults

# --- 1. HARDVERAPRÓ SCRAPER ---

def scrape_hardverapro(seen_ads, keyword_objects):
    print("--- HardverApró ellenőrzése ---")
    
    ha_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://hardverapro.hu/"
    }

    for item in keyword_objects:
        keyword = item['word']
        custom_url = item['url']

        # URL MEGHATÁROZÁSA
        if custom_url:
            # Ha van egyedi kategória link
            separator = "&" if "?" in custom_url else "?"
            search_url = f"{custom_url}{separator}order=1"
            print(f"🔎 Kategória keresés: '{keyword}' itt: ...{custom_url[-30:]}")
        else:
            # Globális kereső
            search_term = f'"{keyword}"'
            print(f"🔎 Globális keresés: {search_term}...")
            search_url = f"{URL_HA_SEARCH_BASE}{search_term}"
        
        try:
            response = requests.get(search_url, headers=ha_headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            ads = soup.find_all('li', class_='media')
            
            # --- GYŰJTÉS ---
            batch_new_items = []
            
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

                # SZIGORÚ CÍM ELLENŐRZÉS
                if keyword.lower() not in title.lower(): continue
                if full_link in seen_ads: continue 
                
                batch_new_items.append({
                    "title": title,
                    "price": price,
                    "link": full_link
                })

            # --- DÖNTÉS (Árvízvédelem) ---
            count = len(batch_new_items)
            
            if count == 0:
                continue

            if count > FLOOD_LIMIT:
                print(f"🌊 FLOOD DETEKTÁLVA ({count} db)! Néma mentés...")
                
                source_name = "Kategória" if custom_url else "Kereső"
                msg = f"ℹ️ **HA Import ({source_name}):** '{keyword}'\n\nTaláltam {count} db régi hirdetést. Elmentve csendben."
                
                send_telegram(msg)
                for item in batch_new_items:
                    save_seen_ad(item['link'])
                    seen_ads.add(item['link'])
            else:
                for item in batch_new_items:
                    print(f"Új HA találat: {item['title']}")
                    msg = f"🍎 TALÁLAT (HardverApró - {keyword})!\n\n**{item['title']}**\nÁr: {item['price']}\n\nLink: {item['link']}"
                    send_telegram(msg)
                    save_seen_ad(item['link'])
                    seen_ads.add(item['link'])
            
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
        if chrome_path: co.set_paths(browser_path=chrome_path)

        page = ChromiumPage(co)
        print(f"Link megnyitása: {URL_MSZ}")
        page.get(URL_MSZ)
        
        if "Verify" in page.title or "Just a moment" in page.title:
            try:
                time.sleep(2) 
                cf_box = page.ele('@id=challenge-stage', timeout=2); 
                if cf_box: cf_box.click() 
                verify_text = page.ele('text:Verify you are human', timeout=2)
                if verify_text: verify_text.click()
                time.sleep(5) 
            except: pass

        if "Just a moment" in page.title:
             print(f"❌ Cloudflare blokkol.")
             return

        print("✅ Sikeresen betöltve!")
        soup = BeautifulSoup(page.html, 'html.parser')
        all_links = soup.find_all('a', href=True)
        
        batch_new_items = []

        for link in all_links:
            href = link['href']
            text = link.get_text(" ", strip=True)
            
            if "/aprohirdetes/" not in href: continue
            ignore_list = ["/category/", "/page/", "?sort", "&sort", "do=markRead", "/profile/"]
            if any(x in href for x in ignore_list): continue
            if not text or len(text) < 3: continue

            found_kw = None
            for kw in keywords:
                if kw in text.lower():
                    found_kw = kw
                    break
            
            if not found_kw: continue
            if href in seen_ads: continue
            if any(item['link'] == href for item in batch_new_items): continue

            batch_new_items.append({
                "title": text,
                "link": href,
                "keyword": found_kw
            })

        count = len(batch_new_items)
        print(f"  -> {count} db új találat az oldalon.")

        if count > 5: 
             print(f"🌊 FLOOD DETEKTÁLVA ({count} db)!")
             msg = f"ℹ️ **Menemszol importálás:**\n\nTaláltam {count} db eddig nem látott hirdetést. Némán elmentve."
             send_telegram(msg)
             for item in batch_new_items:
                 save_seen_ad(item['link'])
                 seen_ads.add(item['link'])
        else:
             for item in batch_new_items:
                print(f"Új Menemszol találat: {item['title']}")
                msg = f"🎹 TALÁLAT (Menemszol)!\n\n**{item['title']}**\n\nLink: {item['link']}"
                send_telegram(msg)
                save_seen_ad(item['link'])
                seen_ads.add(item['link'])

        print(f"Menemszol vége.")

    except Exception as e:
        print(f"KRITIKUS HIBA a Menemszolnál: {e}")
    finally:
        if page:
            try: page.quit()
            except: pass

# --- FŐ PROGRAM ---

if __name__ == "__main__":
    seen_ads_memory = load_seen_ads()
    all_keywords = load_keywords_by_site()
    
    scrape_hardverapro(seen_ads_memory, all_keywords['hardverapro'])
    print("-" * 30)
    scrape_menemszol(seen_ads_memory, all_keywords['menemszol'])
