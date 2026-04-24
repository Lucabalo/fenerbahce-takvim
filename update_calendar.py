import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, List, Optional

import pytz
import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event

TR_TZ = pytz.timezone("Europe/Istanbul")
UTC = pytz.utc
NOW_UTC = datetime.now(UTC)
PAST_DAYS = 30
FUTURE_DAYS = 180

SOURCES = [
    {
        "sport": "football",
        "icon": "⚽",
        "label": "Futbol A Takımı",
        "duration_hours": 2,
        "urls": [
            "https://www.fenerbahce.org/branslar/futbolatakimi/fikstur",
            "https://www.fenerbahce.org/Branslar/FutbolATakimi/Fikstur",
            "https://www.fenerbahce.org/branches/footballateam/fixture",
            "https://www.fenerbahce.org/fikstur",
        ],
    },
    {
        "sport": "basketball",
        "icon": "🏀",
        "label": "Basketbol Erkek",
        "duration_hours": 2,
        "urls": [
            "https://www.fenerbahce.org/branslar/basketbolerkek/fikstur#fikstur",
            "https://www.fenerbahce.org/Branslar/BasketbolErkek/Fikstur",
            "https://www.fenerbahce.org/fikstur",
        ],
    },
    {
        "sport": "volleyball",
        "icon": "🏐",
        "label": "Voleybol Kadın",
        "duration_hours": 2,
        "urls": [
            "https://www.fenerbahce.org/branslar/voleybolkadin/fikstur",
            "https://www.fenerbahce.org/Branslar/VoleybolKadin/Fikstur",
            "https://www.fenerbahce.org/fikstur",
        ],
    },
]

MONTHS_TR = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.7,en;q=0.6",
}


def clean_text(text: str) -> str:
    text = unescape(text or "")
    return re.sub(r"\s+", " ", text).strip()


def normalize_team_name(name: str) -> str:
    name = clean_text(name)
    return name.replace("Fenerbahce", "Fenerbahçe")


def stable_id(*parts: str) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def month_no(month_name: str) -> Optional[int]:
    key = clean_text(month_name).lower().translate(str.maketrans("İI", "ii"))
    return MONTHS_TR.get(key)


def parse_date_parts(day: str, month: str, year: str, time_text: str = "12:00") -> Optional[datetime]:
    day = clean_text(day).strip().strip(".")
    year = clean_text(year)
    m_no = month_no(month)
    if not (day.isdigit() and year.isdigit() and m_no):
        return None

    tm = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", clean_text(time_text or ""))
    hour, minute = (12, 0)
    if tm:
        hour, minute = int(tm.group(1)), int(tm.group(2))

    try:
        return TR_TZ.localize(datetime(int(year), m_no, int(day), hour, minute)).astimezone(UTC)
    except Exception:
        return None


def parse_datetime_text(text: str) -> Optional[datetime]:
    text = clean_text(text)
    tm = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    hour, minute = (12, 0)
    if tm:
        hour, minute = int(tm.group(1)), int(tm.group(2))

    # 2026/04/28 20:45:00 or 2026-04-28 20:45
    iso = re.search(r"\b(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", text)
    if iso:
        y, mo, d = map(int, iso.groups())
        return TR_TZ.localize(datetime(y, mo, d, hour, minute)).astimezone(UTC)

    # 28 Nisan 2026 or 28 Nisan Salı 2026
    word = re.search(r"\b(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)(?:\s+[A-Za-zÇĞİÖŞÜçğıöşü]+)?\s+(20\d{2})\b", text, re.IGNORECASE)
    if word:
        return parse_date_parts(word.group(1), word.group(2), word.group(3), text)

    # 28 Nisan Salı without year: current year, or next year if far past.
    word_no_year = re.search(r"\b(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)", text, re.IGNORECASE)
    if word_no_year:
        year = datetime.now(TR_TZ).year
        dt = parse_date_parts(word_no_year.group(1), word_no_year.group(2), str(year), text)
        if dt and dt < NOW_UTC - timedelta(days=180):
            dt = parse_date_parts(word_no_year.group(1), word_no_year.group(2), str(year + 1), text)
        return dt

    return None


def in_window(dt: datetime) -> bool:
    return NOW_UTC - timedelta(days=PAST_DAYS) <= dt <= NOW_UTC + timedelta(days=FUTURE_DAYS)


def parse_score(text: str) -> Dict[str, Optional[int]]:
    m = re.search(r"\b(\d{1,3})\s*-\s*(\d{1,3})\b", clean_text(text))
    if not m:
        return {"home": None, "away": None}
    return {"home": int(m.group(1)), "away": int(m.group(2))}


def make_match(source: Dict[str, Any], source_url: str, dt_utc: datetime, home: str, away: str, competition: str, venue: str, raw_time_or_score: str = "") -> Dict[str, Any]:
    dt_utc = dt_utc.astimezone(UTC)
    local = dt_utc.astimezone(TR_TZ)
    event_id = stable_id(source["sport"], dt_utc.strftime("%Y%m%d%H%M"), home, away)
    score = parse_score(raw_time_or_score)
    status = "finished" if score["home"] is not None else ("scheduled" if dt_utc > NOW_UTC else "finished_or_recent")
    return {
        "sport": source["sport"],
        "team": "Fenerbahçe",
        "competition": clean_text(competition or source["label"]),
        "homeTeam": normalize_team_name(home),
        "awayTeam": normalize_team_name(away),
        "startTimeUtc": dt_utc.isoformat(),
        "startTimeTurkey": local.isoformat(),
        "status": status,
        "score": score,
        "venue": clean_text(venue or ""),
        "source": "fenerbahce_official",
        "sourceUrl": source_url,
        "sourceEventId": event_id,
        "updatedAt": NOW_UTC.isoformat(),
    }


def parse_fixture_dom(html: str, source: Dict[str, Any], source_url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    matches: List[Dict[str, Any]] = []
    seen = set()

    def add(match: Optional[Dict[str, Any]]):
        if not match:
            return
        if match["sourceEventId"] in seen:
            return
        seen.add(match["sourceEventId"])
        matches.append(match)

    # SIRADAKİ MAÇ
    for card in soup.select("li.card-next-match"):
        teams = [clean_text(x.get_text(" ")) for x in card.select(".team .name")]
        if len(teams) < 2:
            continue
        title_el = card.select_one(".match-detail .title") or card.select_one(".title")
        competition = clean_text(title_el.get_text(" ") if title_el else source["label"])

        dt = None
        countdown = card.select_one(".match-countdown")
        if countdown and countdown.get("data-countdown"):
            dt = parse_datetime_text(countdown.get("data-countdown", ""))

        info_lines = [clean_text(x.get_text(" ")) for x in card.select(".match-info li")]
        time_line = next((x for x in info_lines if re.search(r"\b\d{1,2}[:.]\d{2}\b", x)), "")
        venue = ""
        for x in info_lines:
            if not re.search(r"\b\d{1,2}[:.]\d{2}\b", x) and not re.search(r"\b\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+", x):
                venue = x
        if not dt:
            date_line = next((x for x in info_lines if re.search(r"\b\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+", x)), "")
            dt = parse_datetime_text(f"{date_line} {time_line}")
        if dt and in_window(dt):
            add(make_match(source, source_url, dt, teams[0], teams[1], competition, venue, time_line))

    # DİĞER MAÇLAR
    for item in soup.select("li.list-item"):
        day_el = item.select_one(".date .dayDigit")
        if not day_el:
            continue
        date_spans = [clean_text(x.get_text(" ")) for x in item.select(".date .detail span")]
        month = date_spans[0] if len(date_spans) >= 1 else ""
        year = next((x for x in reversed(date_spans) if re.search(r"\b20\d{2}\b", x)), "")

        detail = item.select_one(".teams .detail") or item
        hour_el = detail.select_one(".hour")
        hour_text = clean_text(hour_el.get_text(" ") if hour_el else "")
        dt = parse_date_parts(day_el.get_text(" "), month, year, hour_text)
        if not dt:
            dt = parse_datetime_text(" ".join([day_el.get_text(" "), month, year, hour_text]))
        if not dt or not in_window(dt):
            continue

        teams = [clean_text(x.get_text(" ")) for x in item.select(".teams .team .name")]
        if len(teams) < 2:
            continue

        league_el = detail.select_one(".league-name")
        competition = clean_text(league_el.get_text(" ") if league_el else source["label"])
        loc_el = detail.select_one(".location")
        venue = clean_text(loc_el.get_text(" ") if loc_el else "").lstrip("@")
        if not venue:
            mobile_venue = item.select_one(".location-mobile .text")
            venue = clean_text(mobile_venue.get_text(" ") if mobile_venue else "")

        add(make_match(source, source_url, dt, teams[0], teams[1], competition, venue, hour_text))

    return matches


def fetch_html(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"    HTTP {r.status_code}, len={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception as exc:
        print(f"    fetch hata: {exc}")
    return None


def fetch_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    print(f"\n[{source['sport']}] kaynaklar deneniyor…")
    for url in source["urls"]:
        print(f"  URL: {url}")
        html = fetch_html(url)
        if not html:
            continue
        matches = parse_fixture_dom(html, source, url)
        print(f"    DOM fixture parse: {len(matches)}")
        if matches:
            return matches
        time.sleep(1)
    return []


def dedupe_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []
    for m in sorted(matches, key=lambda x: x["startTimeUtc"]):
        key = (m["sport"], m["sourceEventId"])
        if key in seen:
            continue
        seen.add(key)
        output.append(m)
    return output


def build_calendar(matches: List[Dict[str, Any]]) -> str:
    c = Calendar()
    for m in matches:
        source = next(s for s in SOURCES if s["sport"] == m["sport"])
        start = datetime.fromisoformat(m["startTimeUtc"])
        if start.tzinfo is None:
            start = UTC.localize(start)
        start = start.astimezone(UTC)

        e = Event()
        e.uid = f"fenerbahce-{m['sport']}-{m['sourceEventId']}@fenerbahce-takvim"
        e.name = f"{source['icon']} {m['homeTeam']} - {m['awayTeam']}"
        e.begin = start
        e.duration = timedelta(hours=source["duration_hours"])
        local_text = start.astimezone(TR_TZ).strftime("%d.%m.%Y %H:%M")
        score_text = ""
        if m.get("score") and (m["score"].get("home") is not None or m["score"].get("away") is not None):
            score_text = f"\nSkor: {m['score'].get('home')} - {m['score'].get('away')}"
        e.description = (
            f"Branş: {source['label']}\n"
            f"Organizasyon: {m.get('competition') or '-'}\n"
            f"Durum: {m.get('status') or '-'}{score_text}\n"
            f"Yer: {m.get('venue') or '-'}\n"
            f"Türkiye saati: {local_text}\n"
            f"Kaynak: {m.get('sourceUrl') or '-'}"
        )
        c.events.add(e)

    lines = c.serialize().splitlines()
    final_lines = []
    inserted = False
    for line in lines:
        final_lines.append(line)
        if line.startswith("VERSION:2.0") and not inserted:
            final_lines.extend([
                "X-WR-CALNAME:Fenerbahçe Maç Takvimi",
                "X-WR-TIMEZONE:Europe/Istanbul",
                "X-WR-CALDESC:Fenerbahçe futbol, basketbol erkek ve voleybol kadın maç takvimi",
            ])
            inserted = True
    ics_text = "\n".join(final_lines)
    alarm = "BEGIN:VALARM\nACTION:DISPLAY\nDESCRIPTION:Fenerbahçe maçı 60 dakika sonra\nTRIGGER:-PT60M\nEND:VALARM\n"
    return ics_text.replace("END:VEVENT", alarm + "END:VEVENT")


def write_outputs(matches: List[Dict[str, Any]]) -> None:
    with open("fenerbahce_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    ics_text = build_calendar(matches)
    with open("fenerbahce.ics", "w", encoding="utf-8") as f:
        f.write(ics_text)

    print(f"\n✅ fenerbahce_matches.json yazıldı: {len(matches)} maç")
    print(f"✅ fenerbahce.ics yazıldı: {ics_text.count('BEGIN:VEVENT')} VEVENT")
    print(f"✅ ICS boyutu: {len(ics_text.encode('utf-8'))} byte")


def main() -> int:
    all_matches: List[Dict[str, Any]] = []
    for source in SOURCES:
        all_matches.extend(fetch_source(source))
        time.sleep(1)

    matches = dedupe_matches(all_matches)
    print(f"\nToplam normalize edilen maç: {len(matches)}")

    if not matches:
        print("⚠️  Hiç maç verisi alınamadı. Mevcut dosyalar korunuyor.")
        return 0

    write_outputs(matches)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
