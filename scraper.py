import json
from scrapling.fetchers import DynamicFetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # Branş ID'leri: 2841 (Futbol), 3315 (Basketbol), 72093 (Voleybol Erkek)
    team_ids = ["2841", "3315", "72093"]
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    for team_id in team_ids:
        # Hem geçmiş (last) hem gelecek (next) maçları kontrol et
        for period in ["last", "next"]:
            url = f"https://www.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
            print(f"Kontrol ediliyor: ID {team_id} - {url}")
            
            try:
                # DynamicFetcher ile gerçek tarayıcı gibi davranıyoruz
                page = DynamicFetcher.fetch(url, headless=True, network_idle=True)
                
                # SofaScore bazen veriyi JSON yerine düz metin gibi gönderir
                if not page.text or "events" not in page.text:
                    print(f"Uyarı: {team_id} için veri boş veya hatalı geldi.")
                    continue

                data = json.loads(page.text)
                events = data.get('events', [])
                
                print(f"Bulunan maç sayısı: {len(events)}")

                for match in events:
                    e = Event()
                    home = match['homeTeam']['shortName']
                    away = match['awayTeam']['shortName']
                    status = match['status']['type']
                    sport_name = match.get('sport', {}).get('name', 'Sport')
                    
                    start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
                    
                    # Branş ikonları
                    icon = "⚽" if sport_name == "Football" else "🏀" if sport_name == "Basketball" else "🏐"
                    
                    if status == 'finished':
                        h_score = match['homeScore'].get('display', 0)
                        a_score = match['awayScore'].get('display', 0)
                        e.name = f"{icon} {home} {h_score} - {a_score} {away}"
                    else:
                        e.name = f"{icon} {home} - {away}"

                    e.begin = start_date
                    calendar.events.add(e)
                    
            except Exception as e:
                print(f"Hata oluştu ({team_id}): {e}")

    # Dosyayı kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("Fenerbahçe Tüm Branşlar Takvimi güncellendi!")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
