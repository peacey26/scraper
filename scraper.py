# --- 2. MENEMSZOL SCRAPER (JAVÍTOTT Selenium) ---

def scrape_menemszol(seen_ads):
    print("--- Menemszol.hu ellenőrzése (Böngészővel) ---")
    
    keywords = ['virus', 'access', 'elektron']
    driver = None
    
    try:
        # 1. BÖNGÉSZŐ INDÍTÁSA (JAVÍTOTT BEÁLLÍTÁSOK)
        print("Chrome indítása...")
        options = uc.ChromeOptions()
        options.add_argument('--headless=new') # Háttérben fusson
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # TRÜKK: Megadjuk, hogy ne ellenőrizze a verziót olyan szigorúan,
        # vagy hagyjuk, hogy az uc automatikusan letöltse a jót.
        # A legbiztosabb GitHubon, ha nem adunk meg verziószámot, 
        # az uc megpróbálja patchelni a rendszeren lévőt.
        driver = uc.Chrome(options=options)
        
        # 2. OLDAL BETÖLTÉSE
        print("Oldal megnyitása...")
        driver.get(URL_MSZ)
        
        # 3. VÁRAKOZÁS A CLOUDFLARE-RE
        print("Várakozás a Cloudflare átengedésre (20 mp)...")
        time.sleep(20) # Kicsit növeltem a biztonság kedvéért
        
        # 4. ADATKINYERÉS
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # DEBUG: Cím kiírása
        page_title = soup.title.get_text().strip() if soup.title else "Nincs cím"
        print(f"Betöltött oldal címe: {page_title}")

        if "Just a moment" in page_title:
             print("⚠️ MÉG MINDIG BLOKKOL (A Cloudflare nagyon kemény ma).")
        
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
        # Itt most már látni fogjuk, ha még mindig verzió baj van
        print(f"HIBA a Menemszolnál (Selenium): {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("Böngésző bezárva.")
            except:
                pass
