import json
import requests
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # En stabil ve korumasız JSON kaynağı
    url = "https://fixturedownload.com/feed/json/turkish-super-lig/fenerbahce"
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    print("Veri çekme işlemi başlatıldı...")
    try:
        # Scrapling engellere takılıyorsa standart requests ile deneyelim
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            for match in data:
                e = Event()
                home = match.get('HomeTeam')
                away = match.get('AwayTeam')
                e.name = f"💛💙 {home} - {away}"
                
                # Tarih (2026-05-10T19:00:00Z -> datetime)
                date_str = match['Date'].replace('Z', '+00:00')
                e.begin = datetime.fromisoformat(date_str).astimezone(timezone)
                e.location = match.get('Location')
                calendar.events.add(e)
            print(f"Başarılı: {len(data)} maç eklendi.")
        else:
            print(f"Kaynak hatası: {response.status_code}")

        # Dosyanın değiştiğini GARANTİLEMEK için her zaman bir 'Güncelleme' etkinliği ekle
        update_info = Event()
        update_info.name = f"🔄 Son Güncelleme: {datetime.now(timezone).strftime('%H:%M')}"
        update_info.begin = datetime.now(timezone)
        calendar.events.add(update_info)

    except Exception as e:
        print(f"Hata: {e}")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
