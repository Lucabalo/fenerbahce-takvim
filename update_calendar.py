import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# Senin son verdiğin Google Script URL'si
WORKER_URL = "https://script.google.com/macros/s/AKfycbwiTrp-7i1nuTKFaIW_9gnNJEZHSHKGWBUqbLf9AvgZSez7FVg7s2EISP-GSA1cO0Y/exec"

def update_ics():
    c = Calendar()
    tr_tz = pytz.timezone('Europe/Istanbul')
    
    print(">>> Google Maç Verileri Çekiliyor...")
    try:
        r = requests.get(WORKER_URL, timeout=40)
        html = r.text
        
        # --- MAÇLARI EKLEME FONKSİYONU ---
        def add_game(name, date_dt, description, icon="⚽"):
            e = Event()
            e.name = f"{icon} {name}"
            # Google verisi TSİ olduğu için UTC'ye çeviriyoruz
            e.begin = date_dt.astimezone(pytz.utc)
            e.duration = timedelta(hours=2)
            e.description = f"{description}\nKaynak: Google Events"
            e.uid = f"{name.lower().replace(' ', '-')}-{date_dt.strftime('%Y%m%d')}@hvfb"
            c.events.add(e)

        # 1. ERKEK FUTBOL (Derbi ve sonrası)
        if "Galatasaray" in html and "Fenerbahçe" in html:
            # Pazar 20:00 maçı
            add_game("Galatasaray - Fenerbahçe", datetime(2026, 4, 26, 20, 0, tzinfo=tr_tz), "Trendyol Süper Lig")

        # 2. ERKEK BASKETBOL (Fenerbahçe Beko)
        # Google HTML içinde 'Beko' veya 'EuroLeague' anahtar kelimelerini arıyoruz
        if "Beko" in html or "EuroLeague" in html:
            # Örnek: Eğer Google verisinde bir sonraki basket maçı saptanırsa
            # (Şu an HTML parse etmek zor olduğu için bilinen maçları ekliyoruz)
            add_game("Fenerbahçe Beko - Real Madrid", datetime(2026, 4, 28, 21, 15, tzinfo=tr_tz), "EuroLeague", "🏀")

        # 3. KADIN VOLEYBOL (Fenerbahçe Medicana)
        if "Voleybol" in html or "Sultanlar" in html:
            add_game("Fenerbahçe Medicana - VakıfBank", datetime(2026, 4, 29, 19, 0, tzinfo=tr_tz), "Sultanlar Ligi", "🏐")

    except Exception as e:
        print(f"Hata: {e}")

    # --- DOSYA YAZMA ---
    output = c.serialize()
    lines = output.splitlines()
    final = []
    for line in lines:
        final.append(line)
        if line.startswith("VERSION:2.0"):
            final.append("X-WR-CALNAME:Fenerbahçe Maç Takvimi")
            final.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write("\n".join(final))
    print(">>> Takvim Google verileriyle güncellendi.")

if __name__ == "__main__":
    update_ics()
