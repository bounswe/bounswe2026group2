# Monitoring & Logs

Bu sayfa Render uzerindeki backend sagligini, background task hatalarini ve temel sistem performansini izlemek icin kullanilir.

## Gunluk Kontrol Noktalari

- Render backend service > Logs: canli log akisi ve son uygulama loglari.
- Render backend service > Metrics: CPU, memory, restart/deploy durumu, response time ve 5xx oranlari.
- Backend health endpoint: `/health`.
- Better Stack / Logtail source:
  - Production: `render-backend-prod`
  - Development varsa: `render-backend-dev`

## Render Log Stream Kurulumu

1. Better Stack icinde yeni bir Render log source olustur.
2. Source adini ortama gore `render-backend-prod` veya `render-backend-dev` yap.
3. Better Stack'in verdigi syslog ingest host'unu ve source token'i kopyala.
4. Render Dashboard'da workspace ana ekranindan `Integrations > Observability > Log Streams` bolumune git.
5. Default destination olarak Better Stack endpoint'ini ekle.
6. Endpoint formatini `HOST:6514` olarak gir.
7. Token alanina Better Stack source token'ini gir.
8. Kaydettikten sonra backend loglarinin Better Stack'e dusmesini birkac dakika icinde kontrol et.

Papertrail kullanilirsa ayni adimlar uygulanir, sadece Log Endpoint Papertrail'in TLS syslog endpoint'i olur.

## Alarm Kurallari

Better Stack / Logtail uzerinde asagidaki query'ler icin alarm tanimla. Esik: 15 dakika icinde en az 1 error log.

| Alarm | Query |
| --- | --- |
| Transcription hatasi | `Audio transcription failed for` |
| Transcript kaydetme hatasi | `Failed to persist transcript for media file` |
| AI tagging hatasi | `AI tagging failed for story` |

Bildirim hedefi ekip e-postasi veya ekip Slack/Discord kanali olmalidir.

Ilk fazda alarm olmayan ama takip edilecek uyari:

```text
Whisper transcription for
```

## Health Check

Render veya Better Stack uptime monitor ile backend `/health` endpoint'ini izle.

- Beklenen basarili yanit: HTTP `200`, body icinde `"status": "ok"`.
- Hata durumu: HTTP `503`, body icinde `"status": "degraded"`.
- Alarm kosulu: 2 ardisik kontrolde endpoint basarisiz veya degraded.

## Incident Kontrol Listesi

1. Render backend service > Metrics ekraninda CPU, memory, restart ve 5xx oranini kontrol et.
2. Render backend service > Logs ekraninda son deploy sonrasi error olup olmadigina bak.
3. Better Stack / Logtail'de alarm query'lerini calistir.
4. `/health` yanitinda `db` ve `storage` alanlarindan hangisinin degraded oldugunu kontrol et.
5. Son deploy zamanini ve GitHub Actions deploy summary'sini kontrol et.

## Kabul Kriterleri

- Render Logs ekraninda backend loglari gorunuyor.
- Better Stack / Logtail icinde Render'dan gelen backend loglari gorunuyor.
- Uc background task hata query'si loglari filtreleyebiliyor.
- Test amacli error log uretildiginde alarm tetikleniyor.
- `/health` uptime monitor tarafindan izleniyor.
