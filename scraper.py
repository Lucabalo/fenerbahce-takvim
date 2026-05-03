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
        # Google bot korumasını aşmak için Chrome 135 gibi davranıyoruz
        # 'stealthy_headers' gerçek bir kullanıcı izlenimi verir
        page = Fetcher.get(url, impersonate='chrome135', stealthy_headers=True)
        
        if page.status_code != 200:
            print(f"Hata: {page.status_code}. Google erişimi reddetti.")
            return

        # Google genellikle maç verilerini 'application/ld+json' tipinde saklar
        # Sayfadaki tüm JSON-LD bloklarını kontrol edelim
        scripts = page.css('script[type="application/ld+json"]::text').getall()
        
        found_matches = False
        for script in scripts:
            try:
                data = json.loads(script)
                # Event veya SportsEvent tipindeki verileri arıyoruz
                if isinstance(data, list):
                    events = data
                elif isinstance(data, dict) and '@graph' in data:
                    events = data['@graph']
                else:
                    events = [data]

                for item in events:
                    if item.get('@type') in ['Event', 'SportsEvent'] and 'Fenerbahçe' in item.get('name', ''):
                        found_matches = True
                        e = Event()
                        e.name = item['name']
                        # Tarih formatını ayarla (ISO 8601 -> datetime)
                        start_str = item['startDate'].replace('Z', '+00:00')
                        e.begin = datetime.fromisoformat(start_str).astimezone(timezone)
                        calendar.events.add(e)
            except:
                continue

        if not found_matches:
            print("Uyarı: Google sayfasında yapılandırılmış maç verisi bulunamadı.")
            # Yedek: Dosyanın değiştiğini anlamak için bir 'Check' etkinliği ekleyelim
            test = Event()
            test.name = f"Son Kontrol: {datetime.now(timezone).strftime('%H:%M')}"
            test.begin = datetime.now(timezone)
            calendar.events.add(test)

    except Exception as e:
        print(f"Sistem Hatası: {e}")

    # Dosyayı kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print(f"İşlem bitti. Eklenen maç: {len(calendar.events)}")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
