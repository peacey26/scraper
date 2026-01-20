{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import requests\
from bs4 import BeautifulSoup\
import os\
\
# 1. A weboldal c\'edme, amit figyelni akarsz\
URL = "https://www.arukereso.hu/..." # IDE \'cdRD A LINKET\
\
# 2. Fejl\'e9c, hogy b\'f6ng\'e9sz\uc0\u337 nek higgyen minket az oldal (fontos!)\
HEADERS = \{\
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"\
\}\
\
def check_price():\
    try:\
        response = requests.get(URL, headers=HEADERS)\
        response.raise_for_status() # Hiba, ha nem t\'f6lt be\
        \
        soup = BeautifulSoup(response.content, 'html.parser')\
\
        # 3. ITT KELL MEGTAL\'c1LNI AZ ELEMET\
        # P\'e9lda: Megkeress\'fck az \'e1rat tartalmaz\'f3 DIV-et vagy SPAN-t.\
        # Ezt az oldalon jobb klikk -> Vizsg\'e1lat (Inspect) m\'f3dban l\'e1tod.\
        # Itt egy p\'e9lda, mintha egy H1-et keresn\'e9nk:\
        product_name = soup.find('h1').get_text().strip()\
        \
        # P\'e9lda \'e1r keres\'e9sre (ez oldalank\'e9nt v\'e1ltozik!):\
        # price_element = soup.find('span', class_='price-tag').get_text()\
        \
        print(f"Siker! A term\'e9k neve: \{product_name\}")\
        \
        # 4. \'c9rtes\'edt\'e9s k\'fcld\'e9se (ezt k\'e9s\uc0\u337 bb \'e1ll\'edtjuk be pontosan)\
        # Ha v\'e1ltoz\'e1st \'e9szlel, itt k\'fcldhet emailt vagy Telegram \'fczenetet.\
        \
    except Exception as e:\
        print(f"Hiba t\'f6rt\'e9nt: \{e\}")\
\
if __name__ == "__main__":\
    check_price()}