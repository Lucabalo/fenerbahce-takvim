import json
from scrapling.fetchers import Fetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # Bu sefer daha az korumalı ve veri odaklı bir kaynak seçiyoruz
    # Not: URL, genel bir spor veri sağlayıcısı simülasyonudur
    url = "https://fixturedownload.com/feed/json/turkish-super-lig/fenerbahce"
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    print(f"Veri kaynağı güncellendi: {url}")
    try:
        # Standart Fetcher bu tür JSON kaynakları için çok daha stabildir
        page = Fetcher.get(url, stealthy_headers=True)
        
        if page.status_code != 200:
            print(f"Hata: {page.status_code}. Kaynağa erişilemedi.")
            return

        data = json.loads(page.text)
        
        if not data:
            print("Veri boş geldi.")
        else:
            for match in data:
                e = Event()
                # JSON yapısına göre (HomeTeam vs AwayTeam)
                home = match.get('HomeTeam', 'Fenerbahçe')
                away = match.get('AwayTeam', 'Rakip')
                location = match.get('Location', 'Stadyum')
                
                # Tarih dönüşümü (Örn: 2026-05-10T19:00:00Z)
                start_str = match['Date'].replace('Z', '+00:00')
                e.begin = datetime.fromisoformat(start_str).astimezone(timezone)
                
                e.name = f"💛💙 {home} - {away}"
                e.location = location
                calendar.events.add(e)

        # Dosyanın güncellendiğini anlaman için her zaman bir 'Status' ekleyelim
        status = Event()
        status.name = f"✅ Takvim Senkronize: {datetime.now(timezone).strftime('%H:%M')}"
        status.begin = datetime.now(timezone)
        calendar.events.add(status)

    except Exception as e:
        print(f"Sistem Hatası: {e}")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print(f"İşlem tamamlandı. Toplam öğe: {len(calendar.events)}")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
