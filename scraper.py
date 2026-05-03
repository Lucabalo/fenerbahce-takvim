import json
from scrapling.fetchers import DynamicFetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    # Doğrudan takımın fikstür sayfasını hedefliyoruz
    url = "https://www.sofascore.com/team/football/fenerbahce/2841"
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    print(f"Sayfa yükleniyor: {url}")
    try:
        # Gerçek bir tarayıcı gibi sayfayı açıyoruz
        page = DynamicFetcher.fetch(
            url, 
            headless=True, 
            network_idle=True, # Sayfanın tamamen yüklenmesini bekle
            timeout=60
        )

        # Loglama: Sayfa içeriği geldi mi kontrol edelim
        print(f"Sayfa Uzunluğu: {len(page.text)}")
        
        # Sayfadaki maç verilerini içeren gizli JSON objesini bulmaya çalışıyoruz
        # SofaScore verileri genellikle '__NEXT_DATA__' adlı bir script içinde saklar
        if "__NEXT_DATA__" in page.text:
            print("Veri katmanı bulundu, ayrıştırılıyor...")
            raw_json = page.text.split('__NEXT_DATA__" type="application/json">')[1].split('</script>')[0]
            data = json.loads(raw_json)
            
            # JSON içindeki maçları bul (Yol: props -> pageProps -> events)
            events = data.get('props', {}).get('pageProps', {}).get('events', [])
            print(f"Toplam {len(events)} maç verisi yakalandı.")

            for match in events:
                e = Event()
                home = match['homeTeam']['shortName']
                away = match['awayTeam']['shortName']
                start_timestamp = match['startTimestamp']
                
                # Başlangıç zamanı
                start_date = datetime.fromtimestamp(start_timestamp, timezone)
                
                # Maç adı
                e.name = f"💛💙 {home} - {away}"
                e.begin = start_date
                calendar.events.add(e)
        else:
            print("KRİTİK HATA: Veri katmanı (NEXT_DATA) bulunamadı. SofaScore bloklamış olabilir.")

    except Exception as e:
        print(f"Sistem Hatası: {e}")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("İşlem bitti.")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
