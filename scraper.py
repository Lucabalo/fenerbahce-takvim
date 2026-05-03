import json
from scrapling import Fetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    urls = [
        "https://www.sofascore.com/api/v1/team/2841/events/last/0",
        "https://www.sofascore.com/api/v1/team/2841/events/next/0"
    ]
    
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    # Fetcher'ı varsayılan ayarlarla başlatıyoruz
    fetcher = Fetcher()

    for url in urls:
        print(f"Veri çekiliyor: {url}")
        
        # HATA ÇÖZÜMÜ: Stealth ayarını get içerisinde 'stealthy_headers' 
        # parametresiyle veya doğrudan kütüphanenin yeni standartlarına uygun çağırıyoruz.
        # Scrapling v0.3+ için en güvenli yol budur:
        response = fetcher.get(url, stealthy_headers=True)
        
        if response.status_code != 200:
            print(f"Hata: {response.status_code} - Veri alınamadı.")
            continue

        try:
            data = json.loads(response.text)
            events = data.get('events', [])
        except Exception as e:
            print(f"Veri ayrıştırma hatası: {e}")
            continue

        for match in events:
            # Sadece futbol branşını filtrele
            if match.get('sport') and match['sport']['name'] != 'Football':
                continue

            e = Event()
            home = match['homeTeam']['shortName']
            away = match['awayTeam']['shortName']
            status = match['status']['type']
            
            # Zaman damgasını Türkiye saatine çevir
            start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
            
            # Maç bittiyse skoru, bitmediyse sadece takımları yaz
            if status == 'finished':
                h_score = match['homeScore'].get('display', 0)
                a_score = match['awayScore'].get('display', 0)
                e.name = f"⚽ {home} {h_score} - {a_score} {away}"
            else:
                e.name = f"💛💙 {home} - {away}"

            e.begin = start_date
            calendar.events.add(e)

    # Takvim dosyasını oluştur
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("fenerbahce.ics başarıyla güncellendi!")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
