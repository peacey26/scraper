# --- 2. MENEMSZOL SCRAPER (KÉPERNYŐFOTÓS DEBUG) ---

def scrape_menemszol(seen_ads):
    print("--- Menemszol.hu ellenőrzése (Fényképezős Debug) ---")
    
    keywords = ['virus', 'access', 'elektron']
    driver = None
    
    try:
        print("Chrome indítása...")
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = uc.Chrome(options=options)
        
        print("Oldal megnyitása...")
        driver.get(URL_MSZ)
        
        print("Várakozás (25 mp)...") # Kicsit növeltük
        time.sleep(25)
        
        # --- DIAGNOSZTIKA START ---
        
        # 1. HTML Cím kiírása
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_title = soup.title.get_text().strip() if soup.title else "Nincs cím"
        print(f"Betöltött oldal címe: {page_title}")
        
        # 2. Hirdetések keresése
        ads = soup.find_all('li', class_='ipsDataItem')
        count = len(ads)
        print(f"Talált hirdetések száma: {count}")

        # 3. FÉNYKÉPEZÉS (Ha 0 hirdetés van, vagy gyanús az oldal)
        if count == 0 or "Just a moment" in page_title:
            print("⚠️ GYANÚS! Képernyőfotó készítése: debug_screenshot.png")
            driver.save_screenshot("debug_screenshot.png")
            # Mentsük el a HTML-t is, hátha abban látunk valamit
            with open("debug_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        
        # --- DIAGNOSZTIKA END ---

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
        if driver:
            try:
                driver.quit()
            except:
                pass
