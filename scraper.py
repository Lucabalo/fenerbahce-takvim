import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from ics import Calendar, Event

API_KEY = os.getenv("THESPORTSDB_API_KEY", "123")
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
CURRENT_SEASON = os.getenv("SEASON", "2025-2026")

IST = ZoneInfo("Europe/Istanbul")
UTC = timezone.utc
NOW_UTC = datetime.now(UTC)
PAST_DAYS = 30
FUTURE_DAYS = 210

SIGNATURE = "Bu takvim HvFB Derneği için Ahmet Saatçıoğlu tarafından hazırlanmıştır."

BROADCASTERS = {
    "EuroLeague": "S Sport",
    "Süper Lig": "beIN SPORTS",
    "Turkish Cup": "A Spor",
}

TEAMS = {
    "football": {
        "team_id": "133807",
        "label": "Fenerbahçe Erkek Futbol",
        "calendar_name": "Fenerbahçe",
        "icon": "⚽",
        "duration_hours": 2,
    },
    "basketball_men": {
        "team_id": "136071",
        "label": "Fenerbahçe Beko Erkek Basketbol",
        "calendar_name": "Fenerbahçe Beko",
        "icon": "🏀",
        "duration_hours": 2,
    },
    "volleyball_women": {
        "team_id": None,
        "label": "Fenerbahçe Kadın Voleybol",
        "calendar_name": "Fenerbahçe Kadın Voleybol",
        "icon": "🏐",
        "duration_hours": 2,
    },
}

HEADERS = {
    "User-Agent": "FenerbahceTakvim/1.0 (+https://github.com/) Python requests",
    "Accept": "application/json,text/plain,*/*",
}


def stable_hash(*parts: str) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def simplify_competition(name: str) -> str:
    if not name:
        return "Organizasyon bilgisi yok"

    replacements = {
        "EuroLeague Basketball": "EuroLeague",
        "Turkish Super Lig": "Süper Lig",
        "Turkey Super Lig": "Süper Lig",
        "Turkish Süper Lig": "Süper Lig",
    }

    return replacements.get(name, name)


def get_broadcaster(competition: str) -> str:
    return BROADCASTERS.get(competition, "Yayın bilgisi eklenecek")


def build_description(match: Dict[str, Any]) -> str:
    competition = simplify_competition(match.get("competition") or "")
    broadcaster = get_broadcaster(competition)

    return f"""{competition}
Yayıncı: {broadcaster}

{SIGNATURE}"""


def parse_event_datetime(event: Dict[str, Any]) -> Optional[datetime]:
    date_value = event.get("dateEvent") or event.get("dateEventLocal")
    if not date_value:
        return None

    time_value = event.get("strTime") or "12:00:00"
    time_value = time_value.replace("Z", "").strip()

    if len(time_value) == 5:
        time_value += ":00"

    if not time_value:
        time_value = "12:00:00"

    try:
        naive = datetime.fromisoformat(f"{date_value}T{time_value}")
    except ValueError:
        try:
            naive = datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    return naive.replace(tzinfo=UTC).astimezone(IST)


def in_window(dt_ist: datetime) -> bool:
    dt_utc = dt_ist.astimezone(UTC)
    return NOW_UTC - timedelta(days=PAST_DAYS) <= dt_utc <= NOW_UTC + timedelta(days=FUTURE_DAYS)


def api_get(path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    response = requests.get(url, params=params or {}, headers=HEADERS, timeout=30)
    print(f"GET {response.url} -> HTTP {response.status_code}")
    response.raise_for_status()
    return response.json()


def fetch_team_events(branch: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    team_id = config.get("team_id")
    if not team_id:
        print(f"[{branch}] team_id yok, şimdilik atlanıyor.")
        return []

    raw_events: List[Dict[str, Any]] = []

    try:
        payload = api_get("eventsseason.php", {
            "id": team_id,
            "s": CURRENT_SEASON,
        })
        raw_events = payload.get("events") or []
        print(f"[{branch}] sezon maçları alındı: {len(raw_events)}")
    except Exception as exc:
        print(f"[{branch}] eventsseason.php hata: {exc}")
        raw_events = []

    if not raw_events:
        for endpoint in ("eventsnext.php", "eventslast.php"):
            try:
                payload = api_get(endpoint, {"id": team_id})
                raw_events.extend(payload.get("events") or [])
            except Exception as exc:
                print(f"[{branch}] {endpoint} hata: {exc}")

    normalized: List[Dict[str, Any]] = []

    for event in raw_events:
        dt_ist = parse_event_datetime(event)
        if not dt_ist or not in_window(dt_ist):
            continue

        home = event.get("strHomeTeam") or ""
        away = event.get("strAwayTeam") or ""

        if "Fenerbah" not in home and "Fenerbah" not in away:
            continue

        score_home = event.get("intHomeScore")
        score_away = event.get("intAwayScore")

        status = "finished" if score_home not in (None, "") or score_away not in (None, "") else "scheduled"
        event_id = event.get("idEvent") or stable_hash(branch, dt_ist.isoformat(), home, away)

        normalized.append({
            "id": f"{branch}-{event_id}",
            "sourceEventId": str(event_id),
            "branch": branch,
            "sport": branch,
            "team": config["calendar_name"],
            "homeTeam": home,
            "awayTeam": away,
            "opponent": away if "Fenerbah" in home else home,
            "competition": event.get("strLeague") or event.get("strSeason") or config["label"],
            "season": event.get("strSeason") or "",
            "startTimeUtc": dt_ist.astimezone(UTC).isoformat(),
            "startTimeTurkey": dt_ist.isoformat(),
            "venue": event.get("strVenue") or "",
            "status": status,
            "score": {
                "home": int(score_home) if str(score_home).isdigit() else None,
                "away": int(score_away) if str(score_away).isdigit() else None,
            },
            "source": "TheSportsDB",
            "sourceUrl": f"https://www.thesportsdb.com/event/{event_id}",
            "timeConfidence": "utc_converted_from_thesportsdb",
            "updatedAt": NOW_UTC.isoformat(),
        })

    print(f"[{branch}] normalize edilen maç: {len(normalized)}")
    return normalized


def fetch_all_matches() -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []

    for branch, config in TEAMS.items():
        matches.extend(fetch_team_events(branch, config))

    return dedupe_matches(matches)


def dedupe_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []

    for match in sorted(matches, key=lambda item: item["startTimeUtc"]):
        key = (match["branch"], match["sourceEventId"])
        if key in seen:
            continue

        seen.add(key)
        output.append(match)

    return output


def build_calendar(matches: List[Dict[str, Any]]) -> str:
    calendar = Calendar()

    for match in matches:
        config = TEAMS[match["branch"]]
        start_utc = datetime.fromisoformat(match["startTimeUtc"]).astimezone(UTC)

        event = Event()
        event.uid = f"fenerbahce-{match['branch']}-{match['sourceEventId']}@fenerbahce-takvim"
        event.name = f"{config['icon']} {match['homeTeam']} - {match['awayTeam']}"
        event.begin = start_utc
        event.duration = timedelta(hours=config["duration_hours"])
        event.location = match.get("venue") or ""
        event.description = build_description(match)

        calendar.events.add(event)

    text = calendar.serialize()
    lines = text.splitlines()
    final_lines = []
    inserted = False

    for line in lines:
        final_lines.append(line)

        if line.startswith("VERSION:2.0") and not inserted:
            final_lines.extend([
                "X-WR-CALNAME:Fenerbahçe Maç Takvimi",
                "X-WR-TIMEZONE:Europe/Istanbul",
                "X-WR-CALDESC:Fenerbahçe futbol ve erkek basketbol maç takvimi",
            ])
            inserted = True

    alarm = (
        "BEGIN:VALARM\n"
        "ACTION:DISPLAY\n"
        "DESCRIPTION:Fenerbahçe maçı 60 dakika sonra\n"
        "TRIGGER:-PT60M\n"
        "END:VALARM\n"
    )

    return "\n".join(final_lines).replace("END:VEVENT", alarm + "END:VEVENT")


def write_outputs(matches: List[Dict[str, Any]]) -> None:
    with open("fenerbahce_matches.json", "w", encoding="utf-8") as file:
        json.dump(matches, file, ensure_ascii=False, indent=2)

    with open("fenerbahce.ics", "w", encoding="utf-8") as file:
        file.write(build_calendar(matches))

    print(f"✅ fenerbahce_matches.json yazıldı: {len(matches)} maç")
    print("✅ fenerbahce.ics yazıldı")


def main() -> int:
    matches = fetch_all_matches()
    print(f"Toplam maç: {len(matches)}")

    if not matches:
        print("⚠️ API'den maç alınamadı. Mevcut fenerbahce.ics korunuyor.")
        return 0

    write_outputs(matches)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
