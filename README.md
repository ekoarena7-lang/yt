# 🚀 YİTX Otomasyonu — AI Kontent & Sosial Media Platforması

**YİTX Otomasyonu** müstəqil süni intellekt əsaslı mətn yazılması, AI şəkil və video generasiyası, YouTube kontentinin repurposing-i (çoxlu sosial medyalara uyğunlaşdırılması) və avtomatik sosial media zamanlayıcısı (Scheduler) platformasıdır.

---

## 🚀 Xüsusiyyətlər

1. **AI Mətn Yazılması (`core/text_generator.py`)**:
   - Posts, Hooks, Captions, Blog yazıları (Gemini / Claude API).
2. **AI Şəkil & Video Generasiyası (`core/media_engine.py`)**:
   - Mətn -> Şəkil (Flux AI, Ideogram)
   - Mətn / Şəkil -> Video (Kling 3.0, Veo 3.1, Nano Banana - Kie.ai API)
3. **Kontentin Yenidən İstifadəsi (`core/repurposer.py`)**:
   - 1 YouTube videosu -> 5-10 TikTok/Reels/Shorts ssenarisi + 20 X postu + 5 LinkedIn məqaləsi.
4. **Çoxlu Sosial Medya Paylaşımı (`core/social_publisher.py`)**:
   - Instagram Reels, TikTok, YouTube Shorts, X (Twitter) və LinkedIn avto-paylaşım.
5. **Telegram İdarəetmə Botu (`bot.py`)**:
   - Telegram üzərindən ideya/link göndərmə, kontent prevyusu və təsdiq/paylaşım düymələri.
6. **Zamanlayıcı Servis (`scheduler_daemon.py`)**:
   - Bazadakı planlaşdırılmış postları vaxtı çatdıqda avtomatik sosial platformalara göndərən fon servisi.

---

## 🛠️ Quraşdırma & İşə Salma

```bash
# 1. Asılılıqları quraşdırın
pip install -r requirements.txt

# 2. Telegram Botunu işə salın
python bot.py

# 3. Fon Zamanlayıcısını işə salın (opsiyonel)
python scheduler_daemon.py
```
