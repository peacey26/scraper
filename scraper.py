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

# KIZÁRÓLAG EZT AZ EGY OLDALT FIGYELJÜK MOST:
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

# --- 1. HARDVERAPRÓ SCRAPER (Requests - Gyors) ---

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

# ---
