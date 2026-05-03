import json
from scrapling.fetchers import Fetcher
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

    for url in urls:
        print(f"Veri çekiliyor: {url}")
        
        # DOKÜMANTASYON ÇÖZÜMÜ: One-off request stilini kullanıyoruz.
        # 'stealthy_headers=True' ile gerçek bir tarayıcı parmak izi gönderiyoruz.
        try:
            page = Fetcher.get(url, stealthy_headers=True)
            
            if page.status_code != 200:
                print(f"Hata: {page.status_code} - Erişim reddedildi.")
                continue

            # Scrapling page nesnesi üzerinden doğrudan metni alıyoruz
            data = json.loads(page.text)
            events = data.get('events', [])
        except Exception as e:
            print(f"Bir hata oluştu: {e}")
            continue

        for match in events:
            # Branş kontrolü
            if match.get('sport') and match['sport']['name'] != 'Football':
                continue

            e = Event()
            home = match['homeTeam']['shortName']
            away = match['awayTeam']['shortName']
            status = match['status']['type']
            
            start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
            
            if status == 'finished':
                h_score = match['homeScore'].get('display', 0)
                a_score = match['awayScore'].get('display', 0)
                e.name = f"⚽ {home} {h_score} - {a_score} {away}"
            else:
                e.name = f"💛💙 {home} - {away}"

            e.begin = start_date
            calendar.events.add(e)

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("fenerbahce.ics başarıyla güncellendi!")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
