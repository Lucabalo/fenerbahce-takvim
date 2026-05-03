import json
import os
from scrapling import Fetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # SofaScore API Linkleri (Gelecek ve Geçmiş Maçlar)
    urls = [
        "https://www.sofascore.com/api/v1/team/2841/events/last/0",
        "https://www.sofascore.com/api/v1/team/2841/events/next/0"
    ]
    
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    for url in urls:
        print(f"Veri çekiliyor: {url}")
        # Scrapling'in en gelişmiş modunu kullanıyoruz
        # Bu aşamada arka planda kurduğumuz tüm kütüphaneler devreye girer
        fetcher = Fetcher(url, stealth=True)
        
        if fetcher.status_code != 200:
            print(f"Hata: {fetcher.status_code} - Engel aşılamadı.")
            continue

        try:
            data = json.loads(fetcher.page_source)
            events = data.get('events', [])
        except Exception as e:
            print(f"Veri ayrıştırma hatası: {e}")
            continue

        for match in events:
            # Sadece Futbol maçlarını filtrele (isteğe bağlı)
            if match.get('sport') and match['sport']['name'] != 'Football':
                continue

            e = Event()
            home = match['homeTeam']['shortName']
            away = match['awayTeam']['shortName']
            status = match['status']['type']
            
            # Başlangıç zamanı (UTC'den Türkiye saatine çevrim)
            start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
            
            # Maç durumuna göre isim belirleme
            if status == 'finished':
                h_score = match['homeScore'].get('display', 0)
                a_score = match['awayScore'].get('display', 0)
                e.name = f"⚽ {home} {h_score} - {a_score} {away}"
            else:
                e.name = f"💛💙 {home} - {away}"

            e.begin = start_date
            calendar.events.add(e)

    # .ics dosyasını oluştur ve kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("fenerbahce.ics başarıyla güncellendi!")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
