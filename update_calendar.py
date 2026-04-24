import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, Iterable, List, Optional

import pytz
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
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

TR_DAY_WORDS = {
    "pazartesi",
    "salı",
    "sali",
    "çarşamba",
    "carsamba",
    "perşembe",
    "persembe",
    "cuma",
    "cumartesi",
    "pazar",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.7,en;q=0.6",
}


def slugify(value: str) -> str:
    value = unescape(value or "").strip().lower()
    replacements = str.maketrans("çğıöşüâîû", "cgiosuaiu")
    value = value.translate(replacements)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "match"


def stable_id(*parts: str) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_tr_datetime(text: str) -> Optional[datetime]:
    if not text:
        return None
    original = clean_text(text)
    lower = original.lower()

    time_match = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", original)
    hour, minute = (12, 0)
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2))

    # 26.04.2026 / 26/04/2026 / 26-04-2026
    numeric = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b", original)
    if numeric:
        day, month, year = int(numeric.group(1)), int(numeric.group(2)), int(numeric.group(3))
        if year < 100:
            year += 2000
        return TR_TZ.localize(datetime(year, month, day, hour, minute)).astimezone(UTC)

    # 26 Nisan 2026 / 26 Nisan
    word = re.search(r"\b(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşüâîû]+)(?:\s+(\d{4}))?\b", original, re.IGNORECASE)
    if word:
        day = int(word.group(1))
        month_name = word.group(2).lower().translate(str.maketrans("İI", "ii"))
        month = MONTHS_TR.get(month_name)
        if month:
            year = int(word.group(3)) if word.group(3) else datetime.now(TR_TZ).year
            dt = TR_TZ.localize(datetime(year, month, day, hour, minute)).astimezone(UTC)
            # If no year is present and the date is far in the past, assume next year.
            if not word.group(3) and dt < NOW_UTC - timedelta(days=180):
                dt = TR_TZ.localize(datetime(year + 1, month, day, hour, minute)).astimezone(UTC)
            return dt

    # ISO-ish date in embedded JSON
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})(?:[T\s](\d{2}:\d{2}(?::\d{2})?)?)?", original)
    if iso:
        try:
            dt = date_parser.parse(iso.group(0))
            if dt.tzinfo is None:
                dt = TR_TZ.localize(dt)
            return dt.astimezone(UTC)
        except Exception:
            pass

    return None


def in_window(dt: datetime) -> bool:
    return NOW_UTC - timedelta(days=PAST_DAYS) <= dt <= NOW_UTC + timedelta(days=FUTURE_DAYS)


def normalize_team_name(name: str) -> str:
    name = clean_text(name)
    if not name:
        return name
    name = name.replace("Fenerbahce", "Fenerbahçe")
    return name


def likely_match_object(obj: Dict[str, Any]) -> bool:
    blob = json.dumps(obj, ensure_ascii=False).lower()
    if "fener" not in blob:
        return False
    has_date = any(k.lower() in blob for k in ["date", "tarih", "time", "saat", "matchdate", "start"])
    has_team = any(k.lower() in blob for k in ["home", "away", "team", "rakip", "opponent", "homeclub", "awayclub"])
    return has_date and has_team


def walk_json(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        if likely_match_object(obj):
            yield obj
        for v in obj.values():
            yield from walk_json(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_json(item)


def find_value(obj: Any, keys: List[str]) -> Optional[Any]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = k.lower()
            if any(key in lk for key in keys):
                if isinstance(v, (str, int, float)) and str(v).strip():
                    return v
                if isinstance(v, dict):
                    nested = find_value(v, ["name", "title", "ad"])
                    if nested:
                        return nested
        for v in obj.values():
            found = find_value(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_value(item, keys)
            if found:
                return found
    return None


def normalize_from_json_object(obj: Dict[str, Any], source: Dict[str, Any], source_url: str) -> Optional[Dict[str, Any]]:
    blob = json.dumps(obj, ensure_ascii=False)
    dt = None
    for key in ["date", "tarih", "start", "time", "saat", "match", "fixture"]:
        candidate = find_value(obj, [key])
        if candidate:
            dt = parse_tr_datetime(str(candidate))
            if dt:
                break
    if not dt:
        dt = parse_tr_datetime(blob)
    if not dt or not in_window(dt):
        return None

    home = find_value(obj, ["hometeam", "home_team", "home", "evsahibi", "ev sahibi"])
    away = find_value(obj, ["awayteam", "away_team", "away", "deplasman", "opponent", "rakip"])
    competition = find_value(obj, ["league", "competition", "organization", "organizasyon", "turnuva", "category"])
    venue = find_value(obj, ["venue", "stadium", "salon", "stadyum", "location", "yer"])

    if not home or not away:
        # Last-resort extraction from text around Fenerbahçe.
        names = re.findall(r"[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9 .'-]{2,40}", blob)
        names = [clean_text(n) for n in names if "http" not in n.lower()]
        fb_names = [n for n in names if "Fener" in n]
        other_names = [n for n in names if "Fener" not in n and len(n.split()) <= 5]
        if fb_names and other_names:
            home = home or fb_names[0]
            away = away or other_names[0]

    if not home or not away:
        return None

    home = normalize_team_name(str(home))
    away = normalize_team_name(str(away))
    competition = clean_text(str(competition or source["label"]))
    venue = clean_text(str(venue or ""))

    return make_match(source, source_url, dt, home, away, competition, venue)


def text_lines_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = [clean_text(x) for x in soup.get_text("\n").split("\n")]
    return [x for x in lines if x]


def parse_from_visible_text(html: str, source: Dict[str, Any], source_url: str) -> List[Dict[str, Any]]:
    lines = text_lines_from_html(html)
    matches: List[Dict[str, Any]] = []
    used_ids = set()

    for i, line in enumerate(lines):
        dt = parse_tr_datetime(line)
        if not dt:
            # Sometimes date and time are split over adjacent lines.
            combined = " ".join(lines[i : min(i + 4, len(lines))])
            dt = parse_tr_datetime(combined)
        if not dt or not in_window(dt):
            continue

        window = lines[max(0, i - 8) : min(len(lines), i + 16)]
        joined = " | ".join(window)
        if "fener" not in joined.lower():
            continue

        # Remove obvious UI words.
        candidates = []
        for w in window:
            lw = w.lower()
            if any(skip in lw for skip in ["fikstür", "fikstur", "puan", "haber", "bilet", "detay", "tüm", "tum", "sonuç", "sonuc"]):
                continue
            if parse_tr_datetime(w):
                continue
            if re.fullmatch(r"[0-9:./\- ]+", w):
                continue
            if len(w) < 3 or len(w) > 70:
                continue
            candidates.append(w)

        fb = next((x for x in candidates if "fener" in x.lower()), None)
        opponent = next((x for x in candidates if "fener" not in x.lower() and not any(day in x.lower() for day in TR_DAY_WORDS)), None)
        if not fb or not opponent:
            continue

        # Try to infer order from the local text.
        home, away = normalize_team_name(fb), normalize_team_name(opponent)
        fb_idx = joined.lower().find(fb.lower())
        opp_idx = joined.lower().find(opponent.lower())
        if 0 <= opp_idx < fb_idx:
            home, away = normalize_team_name(opponent), normalize_team_name(fb)

        competition = source["label"]
        for w in candidates:
            lw = w.lower()
            if any(k in lw for k in ["lig", "kupa", "euroleague", "avrupa", "şampiyon", "sampiyon"]):
                competition = w
                break

        venue = ""
        for w in candidates:
            lw = w.lower()
            if any(k in lw for k in ["stad", "stadyum", "salon", "arena", "ülker", "ulker"]):
                venue = w
                break

        match = make_match(source, source_url, dt, home, away, competition, venue)
        if match["sourceEventId"] not in used_ids:
            used_ids.add(match["sourceEventId"])
            matches.append(match)

    return matches


def parse_embedded_json(html: str, source: Dict[str, Any], source_url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    matches: List[Dict[str, Any]] = []
    seen = set()

    scripts = []
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        scripts.append(next_data.string)
    for tag in soup.find_all("script", type="application/ld+json"):
        if tag.string:
            scripts.append(tag.string)

    # Also pick JS chunks containing Fener/fixture-like data.
    for tag in soup.find_all("script"):
        text = tag.string or tag.get_text() or ""
        if "fener" in text.lower() and any(x in text.lower() for x in ["fixture", "fikstur", "fikstür", "match", "date"]):
            scripts.append(text)

    for script in scripts:
        script = script.strip()
        possible_jsons = [script]
        # Attempt to capture assigned JSON blobs from scripts.
        possible_jsons += re.findall(r"(\{.*?\})", script, flags=re.DOTALL)
        for raw in possible_jsons:
            try:
                data = json.loads(raw)
            except Exception:
                continue
            for obj in walk_json(data):
                match = normalize_from_json_object(obj, source, source_url)
                if match and match["sourceEventId"] not in seen:
                    seen.add(match["sourceEventId"])
                    matches.append(match)
    return matches


def make_match(source: Dict[str, Any], source_url: str, dt_utc: datetime, home: str, away: str, competition: str, venue: str) -> Dict[str, Any]:
    dt_utc = dt_utc.astimezone(UTC)
    local = dt_utc.astimezone(TR_TZ)
    event_id = stable_id(source["sport"], dt_utc.strftime("%Y%m%d%H%M"), home, away)
    return {
        "sport": source["sport"],
        "team": "Fenerbahçe",
        "competition": competition or source["label"],
        "homeTeam": home,
        "awayTeam": away,
        "startTimeUtc": dt_utc.isoformat(),
        "startTimeTurkey": local.isoformat(),
        "status": "scheduled" if dt_utc > NOW_UTC else "finished_or_recent",
        "score": {"home": None, "away": None},
        "venue": venue or "",
        "source": "fenerbahce_official",
        "sourceUrl": source_url,
        "sourceEventId": event_id,
        "updatedAt": NOW_UTC.isoformat(),
    }


def fetch_with_requests(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"    requests status={r.status_code} len={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception as exc:
        print(f"    requests hata: {exc}")
    return None


def fetch_with_playwright(url: str) -> Optional[str]:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1365, "height": 1600},
            )
            response = page.goto(url, wait_until="networkidle", timeout=45000)
            status = response.status if response else "no-response"
            try:
                page.wait_for_timeout(2500)
            except Exception:
                pass
            html = page.content()
            browser.close()
            print(f"    playwright status={status} len={len(html)}")
            if html and len(html) > 500:
                return html
    except Exception as exc:
        print(f"    playwright hata: {exc}")
    return None


def fetch_html(url: str) -> Optional[str]:
    html = fetch_with_requests(url)
    if html:
        return html
    return fetch_with_playwright(url)


def fetch_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    print(f"\n[{source['sport']}] kaynaklar deneniyor…")
    for url in source["urls"]:
        print(f"  URL: {url}")
        html = fetch_html(url)
        if not html:
            print("    HTML alınamadı.")
            continue

        matches = parse_embedded_json(html, source, url)
        if not matches:
            matches = parse_from_visible_text(html, source, url)

        print(f"    parse edilen maç: {len(matches)}")
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
            final_lines.extend(
                [
                    "X-WR-CALNAME:Fenerbahçe Maç Takvimi",
                    "X-WR-TIMEZONE:Europe/Istanbul",
                    "X-WR-CALDESC:Fenerbahçe futbol, basketbol erkek ve voleybol kadın maç takvimi",
                ]
            )
            inserted = True
    ics_text = "\n".join(final_lines)
    # ics.py does not expose VALARM cleanly. Inject one VALARM per VEVENT.
    alarm = "BEGIN:VALARM\nACTION:DISPLAY\nDESCRIPTION:Fenerbahçe maçı 60 dakika sonra\nTRIGGER:-PT60M\nEND:VALARM\n"
    ics_text = ics_text.replace("END:VEVENT", alarm + "END:VEVENT")
    return ics_text


def write_outputs(matches: List[Dict[str, Any]]) -> None:
    with open("fenerbahce_matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    ics_text = build_calendar(matches)
    with open("fenerbahce.ics", "w", encoding="utf-8") as f:
        f.write(ics_text)

    event_count = ics_text.count("BEGIN:VEVENT")
    print(f"\n✅ fenerbahce_matches.json yazıldı: {len(matches)} maç")
    print(f"✅ fenerbahce.ics yazıldı: {event_count} VEVENT")
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
