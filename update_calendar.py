import os
import requests
from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta
import pytz

WORKER_URL = "https://script.google.com/macros/s/AKfycbzeDzbRWMuANYlSqj-o3PzseBnG68OTSzfxcT9eoe4v8R7TWgZER4tGjn65KYAOG049/exec"

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
    calendar_name = "Fenerbahçe Maç Takvimi"
    
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
            
            status_type = game.get('status', {}).get('type')
            if status_type == 'finished':
                h_score = game.get('homeScore', {}).get('display', 0)
                a_score = game.get('awayScore', {}).get('display', 0)
                e.name = f"{icon} {home_name} - {away_name} ({h_score}-{a_score})"
            else:
                e.name = f"{icon} {home_name} - {away_name}"
            
            start_ts = game.get('startTimestamp')
            if not start_ts: continue
            start_dt_utc = datetime.fromtimestamp(start_ts, pytz.utc)
            local_dt = start_dt_utc.astimezone(tr_tz)
            
            tournament_name = game.get('tournament', {}).get('name', 'Turnuva')
            channel_text = "Henüz Belli Değil"
            for t_key, broadcaster in BROADCASTERS.items():
                if t_key.lower() in tournament_name.lower():
                    channel_text = broadcaster
                    break
            
            saat_str = local_dt.strftime('%H:%M')
            e.description = f"Turnuva: {tournament_name}\nMaç Saati: {saat_str}\nYayıncı: {channel_text}{ad_footer}"
            e.alarms = [DisplayAlarm(trigger=timedelta(days=-1)), DisplayAlarm(trigger=timedelta(hours=-1))]
            
            if game.get('status', {}).get('code') == 0 and local_dt.hour == 0:
                e.begin = start_dt_utc.date()
                e.make_all_day()
            else:
                e.begin = start_dt_utc
                e.duration = timedelta(hours=2)
                
            e.uid = f"{game.get('id')}@fenerbahce-takvim"
            c.events.add(e)

    # DOSYA YAZMA KISMI (GÜNCELLENDİ)
    # ics.serialize() çıktısını satır satır işleyerek veriyi koruyoruz
    lines = c.serialize().splitlines()
    final_lines = []
    
    for line in lines:
        final_lines.append(line)
        # VERSION satırından hemen sonra takvim adını ve saat dilimini araya sokuyoruz
        if line.startswith("VERSION:2.0"):
            final_lines.append(f"X-WR-CALNAME:{calendar_name}")
            final_lines.append("X-WR-TIMEZONE:Europe/Istanbul")

    with open('fenerbahce.ics', 'w', encoding='utf-8') as f:
        # Satırları doğru şekilde birleştirip dosyaya yazıyoruz
        f.write("\n".join(final_lines))

if __name__ == "__main__":
    update_ics()
