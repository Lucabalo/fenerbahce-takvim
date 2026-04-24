# Fenerbahçe Maç Takvimi

Fenerbahçe Spor Kulübü maçlarını tek bir takvimde takip etmek için hazırlanmış ücretsiz ICS abonelik takvimi.

## Kapsam

| Branş | Kaynak |
|---|---|
| ⚽ Erkek Futbol | API-Football (api-sports.io) |
| 🏀 Erkek Basketbol (Beko) | API-Basketball (api-sports.io) |
| 🏐 Kadın Voleybol | API-Volleyball (api-sports.io) |

## Özellikler

- Otomatik güncelleme (GitHub Actions, her gün 03:00 TR saati)
- Geçmiş 30 gün + gelecek 90 gün fikstürü
- Maçtan 60 dakika önce hatırlatma (VALARM)
- `fenerbahce.ics` — takvim aboneliği
- `fenerbahce_matches.json` — normalize edilmiş maç verisi

## Kurulum

### GitHub Secret

`Settings → Secrets and variables → Actions` altına ekle:

```
APISPORTS_KEY = <api-sports.io API anahtarın>
```

API anahtarı almak için: https://dashboard.api-football.com

### Abonelik

```
webcal://lucabalo.github.io/fenerbahce-takvim/fenerbahce.ics
```

- **Apple:** Safari'de yukarıdaki linke tıkla
- **Google Calendar:** Ayarlar → Takvim ekle → URL ile → HTTPS linkini yapıştır
- **Android:** Google Calendar uygulamasında URL ile ekle

## Yerel Test

```bash
export APISPORTS_KEY=xxx
pip install requests ics pytz
python update_calendar.py
```

## Veri Şeması (`fenerbahce_matches.json`)

```json
{
  "sport": "football | basketball | volleyball",
  "team": "Fenerbahçe",
  "competition": "Süper Lig",
  "homeTeam": "Fenerbahçe",
  "awayTeam": "Galatasaray",
  "startTimeUtc": "2025-03-01T18:00:00+00:00",
  "startTimeTurkey": "2025-03-01T21:00:00+03:00",
  "status": "scheduled | live | finished",
  "score": { "home": null, "away": null },
  "source": "api-sports",
  "sourceEventId": "12345",
  "updatedAt": "2025-03-01T00:00:00+00:00"
}
```
