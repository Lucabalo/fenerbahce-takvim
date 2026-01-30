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
        if "uefa" in t or "avrupa" in t or "europa" in t or "conference"
