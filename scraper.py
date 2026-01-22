import requests
from bs4 import BeautifulSoup
import os
import sys
import time

# --- ÚJ IMPORTOK A BÖNGÉSZŐHÖZ ---
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# --- BEÁLLÍTÁSOK ---
TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
SEEN_FILE = "seen_ads.txt"

# URL-ek
URL_HA = "https://hardverapro.hu/aprok/pc_szerver/apple_mac_imac/mac_mini/index.html"
URL_MSZ = "https://www.menemszol.hu/aprohirdetes/"

# --- KÖZÖS SEGÉDFÜGGVÉNYEK ---

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

# --- 1. HARDVERAPRÓ SCRAPER (Marad a gyors requests megoldás) ---

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
            
            if link.startswith("http"):
                full_link = link
            else:
                full_link = f"https://hardverapro.hu{link}"

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

# --- 2. MENEMSZOL SCRAPER (ÚJ: Real Browser / Selenium) ---

def scrape_menemszol(seen_ads):
    print("--- Menemszol.hu ellenőrzése (Böngészővel) ---")
    
    keywords = ['virus', 'access', 'elektron']
    driver = None
    
    try:
        # 1. BÖNGÉSZŐ INDÍTÁSA
        print("Chrome indítása...")
        options = uc.ChromeOptions()
        options.add_argument('--headless=new') # Háttérben fusson (ne nyisson ablakot)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = uc.Chrome(options=options)
        
        # 2. OLDAL BETÖLTÉSE
        print("Oldal megnyitása...")
        driver.get(URL_MSZ)
        
        # 3. VÁRAKOZÁS A CLOUDFLARE-RE (Nagyon fontos!)
        print("Várakozás a Cloudflare átengedésre (15 mp)...")
        time.sleep(15) 
        
        # 4. ADATKINYERÉS
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # DEBUG: Cím kiírása
        page_title = soup.title.get_text().strip() if soup.title else "Nincs cím"
        print(f"Betöltött oldal címe: {page_title}")

        if "Just a moment" in page_title:
             print("⚠️ MÉG MINDIG BLOKKOL (Növelni kell az időt vagy user-agentet cserélni).")
             # Ha blokkol, lementjük a képernyőképet a GitHubra (opcionális debug)
             # driver.save_screenshot("debug_error.png")

        ads = soup.find_all('li', class_='ipsDataItem')
        print(f"Talált hirdetések száma: {len(ads)}")
        
        new_count = 0

        for ad in ads:
            try:
                title_element = ad.find('h4', class_='ipsDataItem_title') or ad.find('h3', class_='ipsDataItem_title')
                
                if not title_element: continue

                title = title_element.get_text(strip=True)
                
                link_element = title_element.find('a')
                if not link_element: continue
                    
                full_link = link_element['href']

                price = "N/A"
                price_element = ad.find('span', class_='cClassifiedPrice') or ad.find('span', class_='ipsType_price')
                if price_element:
                    price = price_element.get_text(strip=True)

                if not any(word in title.lower() for word in keywords):
                    continue

                if full_link in seen_ads:
                    continue

                print(f"Új Menemszol találat: {title}")
                msg = f"🎹 TALÁLAT (Virus/Access/Elektron)!\n\n**{title}**\nÁr: {price}\n\nLink: {full_link}"
                send_telegram(msg)
                
                save_seen_ad(full_link)
                seen_ads.add(full_link)
                new_count += 1

            except Exception as e:
                print(f"Hiba egy hirdetésnél: {e}")
                continue
        
        print(f"Menemszol vége. {new_count} új hirdetés.")

    except Exception as e:
        print(f"HIBA a Menemszolnál (Selenium): {e}")
    finally:
        # Mindenképp zárjuk be a böngészőt, hogy ne ragadjon be a memória
        if driver:
            try:
                driver.quit()
                print("Böngésző bezárva.")
            except:
                pass

# --- FŐ PROGRAM ---

if __name__ == "__main__":
    seen_ads_memory = load_seen_ads()
    scrape_hardverapro(seen_ads_memory)
    print("-" * 30)
    scrape_menemszol(seen_ads_memory)
