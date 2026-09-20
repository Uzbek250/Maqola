# Maqola Generator — ishga tushirish qo'llanmasi

## 1. Kerakli API kalitlari

- **OpenAI (GPT)**: https://platform.openai.com/api-keys
- **Gemini**: https://aistudio.google.com/apikey (bepul tier bor)
- **NCBI email**: shunchaki o'z emailingizni yozing (PubMed talab qiladi, kalit shart emas)

## 2. Lokal test (Render'ga chiqarishdan oldin, tavsiya etiladi)

```bash
cd article-bot
pip install -r requirements.txt --break-system-packages
cp .env.example .env
# .env faylini oching, OPENAI_API_KEY va GEMINI_API_KEY qiymatlarini haqiqiy kalitlar bilan almashtiring
uvicorn app.main:app --reload
```

Brauzerda: `http://localhost:8000` — bu yerda `{"status": "ishlayapti"}` chiqishi kerak.

`frontend/index.html` faylini brauzerda oching (to'g'ridan-to'g'ri, ya'ni fayl // orqali) —
u avtomatik `localhost:8000` bilan gaplashadi.

## 3. Render.com'ga deploy qilish

1. Bu papkani GitHub repo'ga yuklang (yangi repo yarating, push qiling)
2. Render.com'da: New → Web Service → GitHub repo'ni tanlang
3. Render `render.yaml` faylini avtomatik o'qiydi (Blueprint sifatida)
4. Environment Variables bo'limida quyidagilarni qo'lda kiriting (bular `sync: false` bo'lgani uchun Render so'raydi):
   - `OPENAI_API_KEY`
   - `GEMINI_API_KEY`
   - `NCBI_EMAIL`
5. Deploy tugagach, Render sizga URL beradi (masalan `https://maqola-generator.onrender.com`)

## 4. Frontend'ni ulash

`frontend/index.html` faylida shu qatorni toping:
```js
: "https://SIZNING-RENDER-URL.onrender.com";
```
Va uni haqiqiy Render URL'ingizga almashtiring. Keyin bu HTML faylni:
- Yoki mijozga to'g'ridan-to'g'ri fayl sifatida bering
- Yoki Render'ning o'zida "Static Site" sifatida alohida deploy qiling
- Yoki Netlify/Vercel'ga bepul joylashtiring (eng oson yo'l)

## 5. Muhim eslatmalar

- **Render Free tier** — 15 daqiqa harakatsizlikdan keyin "uxlab qoladi", birinchi so'rov ~1 daqiqa
  kutishi mumkin. **Yechim qo'llandi:** har 10 daqiqada `/health` ga ping yuboradigan vazifa
  (`~/.hermes/scripts/maqola_keepalive.py`) servisni uyg'oq tutadi. Render bepul tarifda oyiga
  750 soat beradi, bitta servisga ~730 soat kerak — bemalol sig'adi. Servis o'chib qolsa,
  ping vazifasi ogohlantirish yuboradi (sog'lom bo'lsa jim turadi).
- **Gemini bepul tarif juda kam** — chaqiruvlar soni cheklangan (`limit: 20`), bir necha
  maqoladan keyin `429` qaytaradi va sifat tekshiruvi ishlamay qoladi (maqola baribir
  qaytariladi, lekin tekshiruvsiz). Barqaror ishlash uchun Gemini'da billing yoqing —
  bu serverga qaraganda muhimroq.
- **PubMed** — kalitsiz sekundiga 3 so'rov chegarasi bor. Agar tez-tez ishlatilsa, `.env`ga
  bepul NCBI API key qo'shish tavsiya etiladi: https://www.ncbi.nlm.nih.gov/account/settings/
- **Xarajat** — GPT-4o va Gemini API pullik (token asosida). Har bir maqola generatsiyasi
  taxminan $0.05-$0.20 atrofida xarajat qiladi (mavzu murakkabligiga qarab). Buni narxingizga
  kiritib hisoblang.
- **100% "AI ekanligi bilinmasligi" kafolat emas** — bu haqda mijozga oldindan ayting (avvalgi
  suhbatda batafsil muhokama qilingan).

## 6. Yangi qo'shilgan sifat-nazorati (2-versiya)

- **3 bosqichli yozish**: Outline (reja) → To'liq maqola → kerak bo'lsa Rewrite (2 martagacha)
- **Uzunlik nazorati**: 1800-2500 so'z oralig'i majburiy, bundan tashqarida bo'lsa Gemini buni
  "uzunlik_muammosi" deb belgilaydi va majburiy qayta yozish ishga tushadi
- **AI-klishe taqiqi**: uch tilda (uz/en/ru) taqiqlangan iboralar ro'yxati promptga kiritilgan
- **Til tanlash**: `/generate` so'roviga `language: "uz"/"en"/"ru"` parametri qo'shildi,
  frontend'da ham dropdown bor
- **Manba sifati**: endi 2 barobar ko'proq manba so'raladi, keyin yangilik (RECENCY_YEARS=6)
  va citation soni (Semantic Scholar uchun) bo'yicha saralanadi, eng яхшиlari tanlanadi;
  dublikat sarlavhalar avtomatik olib tashlanadi
- **Qattiqroq review**: Gemini endi alohida `hallucination_topildi` va `uzunlik_muammosi`
  bayroqlarini qaytaradi; ulardan biri `true` bo'lsa, muammolar soni oz bo'lsa ham majburiy
  qayta yozish ishga tushadi (`needs_rewrite` funksiyasi, `app/services/gemini_service.py`)

Sozlash kerak bo'lsa: `app/services/gpt_service.py` faylida `MIN_WORDS`, `MAX_WORDS`,
`BANNED_PHRASES_*` ro'yxatlarini, `app/services/sources.py`da `RECENCY_YEARS` va
`MIN_ABSTRACT_LENGTH`ni, `app/main.py`da `MAX_REWRITE_ATTEMPTS`ni o'zgartiring.

## 7. Fon vazifasi (job) API — 3-versiya

Maqola yaratish 60–285 soniya davom etadi. Buni bitta HTTP so'rov ichida kutish yomon:
brauzer/proksi timeout berishi mumkin va mijoz "ishlamayapti" deb o'ylaydi. Shuning uchun
**asinxron rejim** qo'shildi.

| Endpoint | Nima qiladi |
|---|---|
| `POST /jobs` | Vazifani boshlaydi, **darhol** (202) `job_id` qaytaradi |
| `GET /jobs/{job_id}` | Holat: `status`, `progress` (0-100), `step`, tayyor bo'lsa `result` |
| `POST /generate` | Eski sinxron rejim — o'zgarmagan (orqaga moslik saqlanadi) |
| `GET /download/{session_id}` | Word (.docx) yuklab olish |

```bash
# 1) Vazifani boshlash — javob bir zumda keladi
curl -X POST https://SIZNING-URL.onrender.com/jobs \
  -H "Content-Type: application/json" \
  -d '{"topic":"vitamin D deficiency and immune function","is_medical":true,"language":"en"}'
# -> {"job_id":"7870251048ab42c8","status":"queued","status_url":"/jobs/7870251048ab42c8"}

# 2) Holatni so'rash (progress ko'rsatish uchun)
curl https://SIZNING-URL.onrender.com/jobs/7870251048ab42c8
# -> {"status":"running","progress":45,"step":"Maqola yozilmoqda",...}
# tayyor bo'lganda: {"status":"done","progress":100,"result":{...}}
```

Progress bosqichlari: 5% mavzu tahlili → 15% manba qidirish → 25% DOI tekshiruvi →
35% reja → 45% yozish → 70% sifat tekshiruvi → 78% qayta yozish → 100% tayyor.

`status` qiymatlari: `queued`, `running`, `done`, `error` (xato bo'lsa `error` maydonida
o'zbekcha sabab keladi). Frontend (`frontend/index.html`) shu oqimdan foydalanadi va
progress chizig'ini ko'rsatadi.

Xotira cheklovi: eng oxirgi 100 ta vazifa saqlanadi, tugaganlari 1 soatdan keyin
o'chiriladi (`MAX_JOBS`, `JOB_TTL_SECONDS` — `app/main.py`).

## 8. Keyingi qadamlar (agar sifat yetarli bo'lmasa)

- GPT-4o o'rniga `o1` yoki `gpt-4-turbo` sinab ko'ring (sifat farqi bo'lishi mumkin, narx boshqacha)
- `rewrite_article` funksiyasini bir necha marta chaqirish (hozir faqat 1 marta qayta yozadi)
- Gemini review'ni yanada qattiqroq qilish uchun promptni kuchaytirish
