import os
import requests
import json
from ics import Calendar, Event
from ics.alarm import DisplayAlarm
from datetime import datetime, timedelta
import pytz

# ─── Yapılandırma ────────────────────────────────────────────────────────────

APISPORTS_KEY = os.environ.get("APISPORTS_KEY", "")

BRANCHES = [
    {
        "sport": "football",
        "icon": "⚽",
        "team_label": "Fenerbahçe",
        "base_url": "https://v3.football.api-sports.io",
        "search_names": ["Fenerbahce", "Fenerbahçe"],
    },
    {
        "sport": "basketball",
        "icon": "🏀",
        "team_label": "Fenerbahçe Beko",
        "base_url": "https://v1.basketball.api-sports.io",
        "search_names": ["Fenerbahce", "Fenerbahçe", "Fenerbahce Beko"],
    },
    {
        "sport": "volleyball",
        "icon": "🏐",
        "team_label": "Fenerbahçe",
        "base_url": "https://v1.volleyball.api-sports.io",
        "search_names": ["Fenerbahce", "Fenerbahçe"],
    },
]

TR_TZ = pytz.timezone("Europe/Istanbul")
NOW_UTC = datetime.now(pytz.utc)
DATE_FROM = (NOW_UTC - timedelta(days=30)).strftime("%Y-%m-%d")
DATE_TO = (NOW_UTC + timedelta(days=90)).strftime("%Y-%m-%d")


def api_headers():
    return {
        "x-apisports-key": APISPORTS_KEY,
        "Accept": "application/json",
    }


def search_team_id(branch):
    """Çeşitli isim varyantları ile takım ID'sini arar."""
    base_url = branch["base_url"]
    for name in branch["search_names"]:
        try:
            r = requests.get(
                f"{base_url}/teams",
                headers=api_headers(),
                params={"search": name},
                timeout=15,
            )
            r.raise_for_status()
            teams = r.json().get("response", [])
            if teams:
                team = teams[0]
                # football: team.id  |  basketball/volleyball: id (üst seviye)
                team_id = (
                    team.get("team", {}).get("id")
                    or team.get("id")
                )
                if team_id:
                    print(f"  [{branch['sport']}] '{name}' → team_id={team_id}")
                    return team_id
        except Exception as exc:
            print(f"  [{branch['sport']}] Arama hatası ('{name}'): {exc}")
    return None


def fetch_fixtures_football(team_id):
    try:
        r = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=api_headers(),
            params={"team": team_id, "from": DATE_FROM, "to": DATE_TO, "timezone": "UTC"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as exc:
        print(f"  [football] Fikstür çekme hatası: {exc}")
        return []


def fetch_fixtures_generic(base_url, sport, team_id):
    try:
        r = requests.get(
            f"{base_url}/games",
            headers=api_headers(),
            params={"team": team_id, "from": DATE_FROM, "to": DATE_TO, "timezone": "UTC"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as exc:
        print(f"  [{sport}] Fikstür çekme hatası: {exc}")
        return []


def _parse_iso(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _to_turkey(dt):
    if not dt:
        return None
    return dt.astimezone(TR_TZ).isoformat()


def _map_status_football(short):
    if short in {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}:
        return "live"
    if short in {"FT", "AET", "PEN"}:
        return "finished"
    return "scheduled"


def _map_status_generic(short):
    if short in {"LIVE", "Q1", "Q2", "Q3", "Q4", "OT", "HT", "S1", "S2", "S3", "S4", "S5"}:
        return "live"
    if short in {"FT", "AOT", "AET", "Fin", "FIN", "FINISHED"}:
        return "finished"
    return "scheduled"


def normalize_football(item):
    fixture = item.get("fixture", {})
    teams = item.get("teams", {})
    goals = item.get("goals", {})
    league = item.get("league", {})
    start_dt = _parse_iso(fixture.get("date"))
    return {
        "sport": "football",
        "team": "Fenerbahçe",
        "competition": league.get("name"),
        "homeTeam": teams.get("home", {}).get("name"),
        "awayTeam": teams.get("away", {}).get("name"),
        "startTimeUtc": start_dt.isoformat() if start_dt else None,
        "startTimeTurkey": _to_turkey(start_dt),
        "status": _map_status_football(fixture.get("status", {}).get("short", "")),
        "score": {"home": goals.get("home"), "away": goals.get("away")},
        "source": "api-sports",
        "sourceEventId": str(fixture.get("id", "")),
        "updatedAt": NOW_UTC.isoformat(),
    }


def normalize_basketball(item):
    teams = item.get("teams", {})
    scores = item.get("scores", {})
    league = item.get("league", {})
    start_dt = _parse_iso(item.get("date"))
    return {
        "sport": "basketball",
        "team": "Fenerbahçe Beko",
        "competition": league.get("name"),
        "homeTeam": teams.get("home", {}).get("name"),
        "awayTeam": teams.get("away", {}).get("name"),
        "startTimeUtc": start_dt.isoformat() if start_dt else None,
        "startTimeTurkey": _to_turkey(start_dt),
        "status": _map_status_generic(item.get("status", {}).get("short", "")),
        "score": {
            "home": scores.get("home", {}).get("total"),
            "away": scores.get("away", {}).get("total"),
        },
        "source": "api-sports",
        "sourceEventId": str(item.get("id", "")),
        "updatedAt": NOW_UTC.isoformat(),
    }


def normalize_volleyball(item):
    teams = item.get("teams", {})
    scores = item.get("scores", {})
    league = item.get("league", {})
    start_dt = _parse_iso(item.get("date"))
    return {
        "sport": "volleyball",
        "team": "Fenerbahçe",
        "competition": league.get("name"),
        "homeTeam": teams.get("home", {}).get("name"),
        "awayTeam": teams.get("away", {}).get("name"),
        "startTimeUtc": start_dt.isoformat() if start_dt else None,
        "startTimeTurkey": _to_turkey(start_dt),
        "status": _map_status_generic(item.get("status", {}).get("short", "")),
        "score": {
            "home": scores.get("home", {}).get("total"),
            "away": scores.get("away", {}).get("total"),
        },
        "source": "api-sports",
        "sourceEventId": str(item.get("id", "")),
        "updatedAt": NOW_UTC.isoformat(),
    }


def fetch_and_normalize():
    all_normalized = []

    for branch in BRANCHES:
        sport = branch["sport"]
        print(f"\n[{sport}] Takım aranıyor…")

        team_id = search_team_id(branch)
        if team_id is None:
            print(f"  [{sport}] ⚠️  Takım ID bulunamadı, branch atlandı.")
            continue

        print(f"  [{sport}] Fikstür çekiliyor (team_id={team_id})…")

        if sport == "football":
            raw_items = fetch_fixtures_football(team_id)
            normalize_fn = normalize_football
        elif sport == "basketball":
            raw_items = fetch_fixtures_generic(branch["base_url"], sport, team_id)
            normalize_fn = normalize_basketball
        else:
            raw_items = fetch_fixtures_generic(branch["base_url"], sport, team_id)
            normalize_fn = normalize_volleyball

        print(f"  [{sport}] {len(raw_items)} raw kayıt alındı.")

        for item in raw_items:
            try:
                normalized = normalize_fn(item)
                if normalized.get("startTimeUtc"):
                    all_normalized.append(normalized)
            except Exception as exc:
                print(f"  [{sport}] Normalize hatası: {exc}")

    print(f"\nToplam {len(all_normalized)} maç normalize edildi.")
    return all_normalized


def build_ics(matches):
    c = Calendar()
    icon_map = {"football": "⚽", "basketball": "🏀", "volleyball": "🏐"}

    for m in matches:
        start_dt = _parse_iso(m["startTimeUtc"])
        if not start_dt:
            continue

        e = Event()
        icon = icon_map.get(m["sport"], "🏆")
        e.name = f"{icon} {m['homeTeam']} - {m['awayTeam']}"
        e.begin = start_dt
        e.duration = timedelta(hours=2)

        score_str = (
            f"{m['score']['home']} - {m['score']['away']}"
            if m["score"]["home"] is not None
            else m["status"]
        )
        turkey_time = ""
        if m.get("startTimeTurkey"):
            try:
                turkey_time = datetime.fromisoformat(m["startTimeTurkey"]).strftime(
                    "%d.%m.%Y %H:%M"
                )
            except Exception:
                turkey_time = m["startTimeTurkey"]

        e.description = "\n".join([
            f"Branş: {m['sport'].capitalize()}",
            f"Organizasyon: {m.get('competition') or 'Bilinmiyor'}",
            f"Skor/Durum: {score_str}",
            f"Türkiye Saati: {turkey_time}",
            f"Kaynak: {m['source']}",
        ])

        # Stabil UID
        e.uid = f"fenerbahce-{m['sport']}-{m['sourceEventId']}@fenerbahce-takvim"

        # 60 dakika önce VALARM
        alarm = DisplayAlarm()
        alarm.trigger = timedelta(minutes=-60)
        e.alarms.append(alarm)

        c.events.add(e)

    lines = c.serialize().splitlines()
    final_lines = []
    for line in lines:
        final_lines.append(line)
        if line.startswith("VERSION:2.0"):
            final_lines.append("X-WR-CALNAME:Fenerbahçe Maç Takvimi")
            final_lines.append("X-WR-TIMEZONE:Europe/Istanbul")

    return "\n".join(final_lines)


def update_files(matches):
    with open("fenerbahce_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    print("fenerbahce_matches.json güncellendi.")

    ics_content = build_ics(matches)
    with open("fenerbahce.ics", "w", encoding="utf-8") as f:
        f.write(ics_content)
    print("fenerbahce.ics güncellendi.")


if __name__ == "__main__":
    if not APISPORTS_KEY:
        print("HATA: APISPORTS_KEY ortam değişkeni tanımlı değil.")
        raise SystemExit(1)

    matches = fetch_and_normalize()

    if not matches:
        print("⚠️  Hiç maç verisi alınamadı. Mevcut dosyalar korunuyor.")
        raise SystemExit(0)

    update_files(matches)
    print(f"\n✅ {len(matches)} maç başarıyla güncellendi.")
