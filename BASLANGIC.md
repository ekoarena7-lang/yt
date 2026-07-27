# 📌 BAŞLANGIÇ REHBERİ — YİTX Otomasyonu

Bu dosya **YİTX Otomasyonu** müstəqil layihəsi üçün öyrənilən dərslər, tələlər və vacib konvensiyalar haqqındadır.

---

## 🎯 Layihə Haqqında
* **Məqsəd:** Süni intellekt əsaslı kontent yaratma, idarəetmə və sosial media avtomatlaşdırma platforması (YİTX Otomasyonu).
* **Əsas Modellər:** Gemini 3.6 Flash (LLM), Kling 3.0 / Veo 3.1 (Kie AI Video), Flux (Görsel).
* **Paylaşım Platformaları:** Instagram Reels, TikTok, YouTube Shorts, X (Twitter), LinkedIn.

---

## ⚠️ Dərslər & Tuzaklar (Pitfalls)
1. **Media URL-ləri:** Sosial medyalara (Meta Graph API, TikTok API, Webhook) göndərilən videolar/şəkillər **ictimaiyyətə açıq (public URL)** olmalıdır. Lokal fayllar göndərilə bilməz. Media generasiya olunanda Kie AI cdn URL-i və ya lokal fayl üçün cdn upload servisi istifadə edilir.
2. **Rate Limits & API Quota:** YouTube Transcript çəkərkən `youtube_transcript_api` istifadə edildikdə IP bloklamasının qarşısını almaq üçün Supadata API fallback istifadə edilir.
3. **SQLite Concurrency:** SQLite bazasına eyni anda Telegram bot və `scheduler_daemon.py` yazanda lock xətası olmaması üçün WAL rejimində çalışdırılır (`PRAGMA journal_mode=WAL;`).

---

## 🔐 Credentials Bağlantısı
* Bu layihə API açarlarını `_knowledge/credentials/master.env` faylından alır.
* İcra olunan komanda: `/sifre-bagla Projeler/YITX_Otomasyonu`
