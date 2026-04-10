import os
import requests
from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta
import pytz

WORKER_URL = "https://script.google.com/macros/s/AKfycbzeDzbRWMuANYlSqj-o3PzseBnG68OTSzfxcT9eoe4v8R7TWgZER4tGjn65KYAOG049/exec"

# Yayıncı Kuruluş Eşleşmeleri
BROADCASTERS = {
    "Trendyol Süper Lig": "beIN SPORTS",
    "Euroleague": "S Sport",
    "Turkish Basketball Super League": "beIN SPORTS",
    "VVSL Lig, Women": "TRT Spor Yıldız",
    "Champions League Women": "S Sport / Tivibu",
    "UEFA Europa League": "TRT / Tabii",
    "Turkiye Kupasi": "A Spor"
}

TEAMS = {
    "Futbol_Erkek": {"id": "3052", "icon": "⚽"},
    "Voleybol_Kadin": {"id": "38868", "icon": "🏐"},
    "Basketbol_Erkek": {"id": "3514", "icon": "🏀"}
}

def fetch_events(team_id, period):
    target_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/{period}/0"
    full_proxy_url = f"{WORKER_URL}?url={target_url}"
    try:
        r = requests.get(full_proxy_url, timeout=30)
        if r.status_code == 200:
            return r.json().get('events', [])
    except: pass
    return []

def update_ics():
    c = Calendar()
    c.creator = "Fenerbahce Takvim Botu"
    tr_tz = pytz.timezone('Europe/Istanbul')
    ad_footer = "\n\n---\nBu Takvim HvFB Derneği için Ahmet Saatçıoğlu tarafından oluşturulmuştur."
    
    for branch, data in TEAMS.items():
        team_id = data["id"]
        icon = data["icon"]
        all_games = fetch_events(team_id, 'last') + fetch_events(team_id, 'next')
        
        for game in all_games:
            if game.get('status', {}).get('type') == 'canceled':
                continue
                
            e = Event()
            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})
            home_name = home_team.get('shortName') or home_team.get('name') or "Fenerbahçe"
            away_name = away_team.get('shortName') or away_team.get('name') or "Rakip"
            
            # Başlık Skor Kontrolü
            status_type = game.get('status', {}).get('type')
            if status_type == 'finished':
                h_score = game.get('homeScore', {}).get('display', 0)
                a_score = game.get('awayScore', {}).get('display', 0)
                e.name = f"{icon} ({h_score}-{a_score}) {home_name} - {away_name}"
            else:
                e.name = f"{icon} {home_name} - {away_name}"
            
            # Zaman Ayarı
            start_ts = game.get('startTimestamp')
            if not start_ts: continue
            start_dt_utc = datetime.fromtimestamp(start_ts, pytz.utc)
            local_dt = start_dt_utc.astimezone(tr_tz)
            
            # KANAL BİLGİSİ (Önce bizim listeye bak, yoksa API'ye bak)
            tournament_name = game.get('tournament', {}).get('name', '')
            
            # Bizim BROADCASTERS listemizde geçiyor mu kontrol et
            channel_text = "Henüz Belli Değil"
            for t_key, broadcaster in BROADCASTERS.items():
                if t_key.lower() in tournament_name.lower():
                    channel_text = broadcaster
                    break
            
            # Eğer hala belli değilse ve API'den veri gelmişse onu kullan
            if channel_text == "Henüz Belli Değil":
                api_channels = game.get('tvChannels', [])
                if api_channels:
                    channel_text = ", ".join([c.get('name') for c in api_channels])

            saat_str = local_dt.strftime('%H:%M')
            e.description = (
                f"Turnuva: {tournament_name}\n"
                f"Maç Saati: {saat_str}\n"
                f"Yayıncı: {channel_text}"
                f"{ad_footer}"
            )
            
            # Hatırlatıcılar
            e.alarms = [DisplayAlarm(trigger=timedelta(days=-1)), DisplayAlarm(trigger=timedelta(hours=-1))]
            
            # Zamanlama
            if game.get('status', {}).get('code') == 0 and local_dt.hour == 0:
                e.begin = start_dt_utc.date()
                e.make_all_day()
            else:
                e.begin = start_dt_utc
                e.duration = timedelta(hours=2)
                
            e.uid = f"{game.get('id')}@fenerbahce-takvim"
            c.events.add(e)

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        f.write(c.serialize())

if __name__ == "__main__":
    update_ics()
