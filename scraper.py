import json
import time
from scrapling.fetchers import DynamicFetcher
from ics import Calendar, Event
from datetime import datetime
import pytz

def fenerbahce_verilerini_cek():
    url = "https://www.sofascore.com/team/football/fenerbahce/2841"
    calendar = Calendar()
    timezone = pytz.timezone("Europe/Istanbul")

    print(f"Hedef sayfa açılıyor: {url}")
    try:
        # DynamicFetcher ile sayfayı açıyoruz
        page = DynamicFetcher.fetch(
            url, 
            headless=True, 
            network_idle=True,
            timeout=60
        )

        # Sayfada maçların yüklenmesi için 2 saniye bekle ve aşağı kaydır
        time.sleep(2)
        print("Sayfa içeriği analiz ediliyor...")

        # SofaScore veriyi __NEXT_DATA__ içinde saklıyor mu tekrar kontrol edelim
        content = page.text
        if '__NEXT_DATA__' in content:
            print("Veri bloğu yakalandı.")
            # JSON verisini çek
            json_text = content.split('__NEXT_DATA__" type="application/json">')[1].split('</script>')[0]
            data = json.loads(json_text)
            
            # Maç listesine iniyoruz
            events = data.get('props', {}).get('pageProps', {}).get('events', [])
            
            if not events:
                # Alternatif yol: pageProps içindeki tournament veya schedule bloklarını ara
                print("HATA: Events listesi boş geldi. SofaScore veri yapısını gizlemiş olabilir.")
            else:
                print(f"Başarılı! {len(events)} maç bulundu.")
                for match in events:
                    e = Event()
                    home = match['homeTeam']['shortName']
                    away = match['awayTeam']['shortName']
                    start_date = datetime.fromtimestamp(match['startTimestamp'], timezone)
                    
                    e.name = f"💛💙 {home} - {away}"
                    e.begin = start_date
                    calendar.events.add(e)
        else:
            print("KRİTİK: Veri bloğu bulunamadı. Sayfa tam yüklenmemiş olabilir.")

    except Exception as e:
        print(f"Beklenmedik bir hata: {e}")

    # Dosyayı kaydet
    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.writelines(calendar.serialize_iter())
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    fenerbahce_verilerini_cek()
