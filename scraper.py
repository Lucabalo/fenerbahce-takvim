import json
from scrapling.fetchers import DynamicFetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # Test için sadece Futbol (2841) ile başlayalım
    team_ids = ["2841"]
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    for team_id in team_ids:
        url = f"https://www.sofascore.com/api/v1/team/{team_id}/events/next/0"
        print(f"Denetleniyor: {url}")
        
        try:
            # Dokümana göre tarayıcıyı daha 'insansı' yapmak için bir iki ayar ekleyelim
            page = DynamicFetcher.fetch(
                url, 
                headless=True, 
                timeout=30,
                network_idle=True # Sayfanın tamamen durulmasını bekle
            )
            
            # Gelen veriyi loglara yazdıralım ki ne olduğunu görelim
            print(f"Yanıt Uzunluğu: {len(page.text)}")
            print(f"İlk 200 Karakter: {page.text[:200]}")

            if not page.text or "events" not in page.text:
                print(f"HATA: SofaScore veri göndermedi. Yanıt içeriği beklenenden farklı.")
                continue

            data = json.loads(page.text)
            events = data.get('events', [])
            print(f"Bulunan Maç: {len(events)}")

            for match in events:
                e = Event()
                home = match['homeTeam']['shortName']
                away = match['awayTeam']['shortName']
                start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
                e.name = f"💛💙 {home} - {away}"
                e.begin = start_date
                calendar.events.add(e)
                    
        except Exception as e:
            print(f"Sistem Hatası: {e}")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
