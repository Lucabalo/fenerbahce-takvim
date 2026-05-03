import json
import time
from scrapling.fetchers import DynamicFetcher
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
        print(f"Veri çekiliyor (Browser Modu): {url}")
        
        try:
            # Dokümandaki DynamicFetcher modunu kullanıyoruz. 
            # Bu mod gerçek bir tarayıcı açar.
            page = DynamicFetcher.fetch(url, headless=True, network_idle=True)
            
            # API yanıtları bazen <body> içinde JSON olarak gelir
            content = page.text
            
            # Eğer yanıt JSON değilse, SofaScore bizi engellemiş veya yönlendirmiş demektir
            data = json.loads(content)
            events = data.get('events', [])
            
            if not events:
                print(f"Uyarı: {url} adresinden maç verisi gelmedi.")
                continue

            for match in events:
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
                
        except Exception as e:
            print(f"Veri çekme hatası: {e}")
            continue

    # Takvimi kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("fenerbahce.ics başarıyla güncellendi!")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
