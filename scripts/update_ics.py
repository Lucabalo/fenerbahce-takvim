from __future__ import annotations

import json
import time
import random
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("fenerbahce.ics")

# ✅ HAR’dan doğrulandı
TEAM_FOOTBALL_ID = 3052
TEAM_BASKET_ID = 3514
TEAM_VOLLEY_ID = 38868

def ical_dt_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def add_alarm_60m(vevent_lines: list[str]) -> list[str]:
    if any(l.strip() == "BEGIN:VALARM" for l in vevent_lines):
        return vevent_lines

    alarm = [
        "BEGIN:VALARM",
        "TRIGGER:-PT60M",
        "ACTION:DISPLAY",
        "DESCRIPTION:Maç başlamak üzere (60 dk kaldı).",
        "END:VALARM",
    ]

    out: list[str] = []
    for l in vevent_lines:
        if l.strip() == "END:VEVENT":
            out.extend(alarm)
        out.append(l)
    return out

def normalize_text(s: str) -> str:
    return (s or "").strip()

def channel_for(kind: str, tournament_name: str) -> str:
    t = (tournament_name or "").lower()

    if kind == "football":
        if "süper lig" in t or "super lig" in t:
            return "Kanal: beIN SPORTS"
        if "türkiye kupası" in t or "turkiye kupasi" in t or "kupa" in t:
            return "Kanal: A Spor / ATV"
        if "uefa" in t or "avrupa" in t or "europa" in t or "conference" in t or "champions" in t:
            return "Kanal: TRT 1"
        return "Kanal: TBD"

    if kind == "basket":
        if "euroleague" in t:
            return "Kanal: S Sport"
        if "bsl" in t or "basketbol süper ligi" in t or "basketbol super ligi" in t:
            return "Kanal: beIN SPORTS"
        return "Kanal: TBD"

    if kind == "volley":
        # Bilinmiyor
        return "Kanal: TBD"

    return "Kanal: TBD"

def http_json(url: str) -> dict:
    """
    GitHub Actions'ta SofaScore bazen 403 veriyor.
    - Önce requests
    - 403 ise cloudscraper
    - Olmazsa workflow düşmesin diye boş events döndür
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
    }

    # küçük jitter (rate limit azaltır)
    time.sleep(random.uniform(0.2, 0.8))

    # 1) requests ile dene
    try:
        import requests
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code != 403:
            print(f"[WARN] HTTP {r.status_code} for {url}")
            return {"events": []}
    except Exception as e:
        print(f"[WARN] requests failed for {url}: {e}")

    # 2) 403 ise cloudscraper ile dene
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        r = scraper.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"[WARN] cloudscraper HTTP {r.status_code} for {url}")
        return {"events": []}
    except Exception as e:
        print(f"[WARN] cloudscraper failed for {url}: {e}")
        return {"events": []}

def fetch_pages(team_id: int, which: str, max_pages: int = 3) -> list[dict]:
    """
    which: 'next' veya 'last'
    paging: /events/next/0, /events/next/1, ...
    max_pages düşük tutuldu (rate limit azaltmak için).
    """
    all_events: list[dict] = []
    for page in range(max_pages):
        url = f"https://www.sofascore.com/api/v1/team/{team_id}/events/{which}/{page}"
        data = http_json(url)
        events = data.get("events", [])
        if not events:
            break
        all_events.extend(events)
    return all_events

def build_events(kind: str, team_id: int, emoji: str) -> list[list[str]]:
    events_json: list[dict] = []
    events_json += fetch_pages(team_id, "last", max_pages=3)
    events_json += fetch_pages(team_id, "next", max_pages=3)

    vevents: list[list[str]] = []
    now_stamp = ical_dt_z(datetime.now(timezone.utc))

    for ev in events_json:
        ts = ev.get("startTimestamp")
        if not ts:
            continue

        dt_start = datetime.fromtimestamp(ts, tz=timezone.utc)

        home = normalize_text((ev.get("homeTeam") or {}).get("name", "Home"))
        away = normalize_text((ev.get("awayTeam") or {}).get("name", "Away"))
        tournament = normalize_text(((ev.get("tournament") or {}).get("name")) or kind)

        event_id = ev.get("id", "")
        uid = f"sofascore-{kind}-{event_id}-{ts}@lucabalo.github.io"

        chan = channel_for(kind, tournament)
        desc = f"{chan}\\nKaynak: SofaScore"

        vevent = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{ical_dt_z(dt_start)}",
            f"SUMMARY:{emoji} {home} - {away} ({tournament})",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
        vevents.append(add_alarm_60m(vevent))

    return vevents

def dedupe_by_uid(vevents: list[list[str]]) -> list[list[str]]:
    seen = set()
    out: list[list[str]] = []
    for ev in vevents:
        uid = next((l[4:] for l in ev if l.startswith("UID:")), None)
        if not uid or uid in seen:
            continue
        seen.add(uid)
        out.append(ev)
    return out

def write_calendar(vevents: list[list[str]]):
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Lucabalo//Fenerbahce Takvim//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Fenerbahçe Maç Takvimi",
        "X-WR-TIMEZONE:Europe/Istanbul",
    ]

    lines = header[:]
    for ev in vevents:
        lines.extend(ev)
    lines.append("END:VCALENDAR")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")

def main():
    all_ev: list[list[str]] = []
    all_ev += build_events("football", TEAM_FOOTBALL_ID, "⚽")
    all_ev += build_events("basket", TEAM_BASKET_ID, "🏀")
    all_ev += build_events("volley", TEAM_VOLLEY_ID, "🏐")

    all_ev = dedupe_by_uid(all_ev)

    # Eğer hepsi 403 yüzünden boş geldiyse workflow yine yeşil kalsın diye
    # en azından boş bir takvim üretelim (abonelik bozulmasın)
    write_calendar(all_ev)

if __name__ == "__main__":
    main()
