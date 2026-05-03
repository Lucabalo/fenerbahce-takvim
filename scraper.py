import json
from scrapling.fetchers import Fetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # Google'da direkt fikstür aratıyoruz
    url = "https://www.google.com/search?q=fenerbahce+mac+fiksturu"
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    print(f"Veri çekiliyor: {url}")
    try:
        # HATA ÇÖZÜMÜ: 'chrome135' yerine genel 'chrome' kullanıyoruz.
        # Scrapling bunu otomatik olarak desteklenen en güncel Chrome sürümüne eşler.
        page = Fetcher.get(url, impersonate='chrome', stealthy_headers=True)
        
        if page.status_code != 200:
            print(f"Hata: {page.status_code}. Google erişimi reddetti.")
            return

        # Google'ın yapılandırılmış JSON-LD verilerini yakalayalım
        scripts = page.css('script[type="application/ld+json"]::text').getall()
        
        found_matches = False
        for script in scripts:
            try:
                data = json.loads(script)
                # JSON-LD içindeki etkinlikleri (maçları) filtrele
                events = []
                if isinstance(data, list):
                    events = data
                elif isinstance(data, dict):
                    events = data.get('@graph', [data])

                for item in events:
                    # 'Event' veya 'SportsEvent' tipinde ve Fenerbahçe içerenleri al
                    if item.get('@type') in ['Event', 'SportsEvent'] and 'Fenerbahçe' in item.get('name', ''):
                        found_matches = True
                        e = Event()
                        e.name = item['name']
                        # Tarih dönüşümü
                        start_str = item['startDate'].replace('Z', '+00:00')
                        e.begin = datetime.fromisoformat(start_str).astimezone(timezone)
                        calendar.events.add(e)
            except:
                continue

        # Dosyanın her seferinde değişmesini garantilemek için 'kontrol' etkinliği ekliyoruz
        check_event = Event()
        check_event.name = f"📍 Takvim Güncellendi: {datetime.now(timezone).strftime('%H:%M')}"
        check_event.begin = datetime.now(timezone)
        calendar.events.add(check_event)

        if not found_matches:
            print("Uyarı: Google'dan maç verisi ayıklanamadı, sadece kontrol etkinliği eklendi.")

    except Exception as e:
        print(f"Sistem Hatası: {e}")

    # Dosyayı kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print(f"İşlem bitti. Toplam öğe: {len(calendar.events)}")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
