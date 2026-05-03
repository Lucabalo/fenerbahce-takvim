# Fenerbahçe Takvim

GitHub Actions günde iki kez çalışır ve `fenerbahce.ics` dosyasını TheSportsDB Free API üzerinden günceller.

Aktif kaynaklar:
- Futbol: TheSportsDB team_id `133807`
- Erkek basketbol: TheSportsDB team_id `136071`
- Kadın voleybol: daha sonra ayrı kaynakla eklenecek

Google / Apple Calendar abonelik linki:

```text
https://KULLANICIADIN.github.io/REPOADI/fenerbahce.ics
```

GitHub cron UTC çalışır. Workflow şu an yaklaşık Türkiye saatiyle 09:00 ve 21:00 çalışacak şekilde ayarlı.
