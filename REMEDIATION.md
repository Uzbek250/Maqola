# Maqola — tuzatish rejasi (tanqid bo'yicha)

Tanqid: ilova "referat" darajasidagi maqola chiqaradi — 10 ta manba yonma-yon
qo'yilgan, haqiqiy sintez yo'q. Quyida har bir nuqta va uning tuzatilishi.

---

## A. Metodologiya

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| A1 | Qidiruv sanasi, filtrlari, nechta natija topilgani yozilmagan | `sources.SEARCH_STATS` qayd etadi: so'rov, har bir bazadan soni, dublikatlar, saralangandan keyingi son, tanlangan son. Ular Methods bo'limiga **haqiqiy raqam** sifatida o'tadi | ✅ |
| A2 | Tanlab olingan sharh, lekin shunday deb yozilmagan | Methods bloki endi ochiq yozadi: "bu TANLAB OLINGAN (narrative) sharh, TIZIMLI emas — PRISMA atamasi ishlatilmasin" | ✅ |
| A3 | Manba tanlash mezoni sub'ektiv | Mezon Methods'da ochiq sanab o'tiladi (moslik, annotatsiya to'liqligi, yangilik) va *tanlab olingan* deb belgilanadi — da'vo qilinmaydi | ✅ |
| A4 | 10 ta manba keng mavzu uchun kam | `max_sources` **25** ga oshirildi (so'rovda o'zgartirish mumkin) | ✅ |

## B. Tarkib va tuzilish

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| B1 | Mavzu haddan tashqari keng — 6-7 mavzu yuzaki | Yangi qoida 16: **3-5 tadan ortiq mustaqil mavzu ochilmasin**. Keng mavzuda bo'limlar soni kamayadi, chuqurlik oshadi | ✅ |
| B2 | Har bir bo'lim 1 ta manbaga tayanadi | Yangi qoida 14a: **har bir bo'lim kamida 3 xil manbaga** tayansin; 1 manbaga tayanadigan bo'lim ochilmasin | ✅ |
| B3 | Sintez yo'q — manbalar yonma-yon | Yangi qoida 14b-14c: manbalar **o'zaro solishtirilsin** (mos/zid) va har bo'lim **sintez jumlasi** bilan tugasin | ✅ |

## C. Ilmiy aniqlik

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| C1 | Namuna hajmi yo'q, lekin shu manbalar ishlatilgan | Qoida 17: dalil zaif bo'lsa (n yo'q, hayvon modeli) undan **markaziy xulosa chiqarilmasin** — kontekst sifatida ishlatilsin | ✅ |
| C2 | Cheklovlar qalqon sifatida takrorlanadi | Qoida 17: ogohlantirish **bir marta** aytiladi, har paragrafda takrorlanmaydi | ✅ |
| C3 | O'z tahlili, tanqidiy taqqoslash yo'q | Qoida 15: har bir da'vo uchun dalil kuchi va qanday sharoitda natija o'zgarishi yozilsin | ✅ |

## D. Format

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| D1 | Uch tilli annotatsiya so'zma-so'z tarjima | Prompt o'zgardi: har bir til **o'sha tilning tabiiy ilmiy uslubida** yozilsin, so'zma-so'z tarjima qilinmasin. Mazmun bir xil, **ifoda har tilda o'ziga xos** | ✅ |
| D2 | Kirish darslikdek, tadqiqot savoli yo'q | Qoida 18: Kirish oxirida **aniq tadqiqot savoli/maqsadi** + "nima noma'lum qolgan" bo'lsin | ✅ |

## E. Eng katta muammo — "referat" formati

Yangi qoida 14 va 15 aynan shuni hal qiladi:
- bo'lim = 1 manba emas, kamida 3 manba;
- manbalar birin-ketin aytilmaydi, **taqqoslanadi**;
- har bo'lim **sintez** jumlasi bilan tugaydi.

**Nazorat namunasi kerak:** tuzatishdan keyin bir mavzuda maqola yozdirib,
"har bo'limda nechta manba bor" va "sintez jumlasi bormi" tekshirilishi shart.

---

## F. Foydalanuvchi hisobi (alohida vazifa)

- Frontend kirganda **bir marta** ism so'raydi, brauzerda saqlaydi.
- Har so'rovda `user_name` yuboriladi.
- Backend ism bo'yicha **so'rovlar sonini** yuritadi (diskda saqlanadi).
- Bu raqam **frontend'da ko'rinmaydi**.
- Ko'rish: `GET /usage?key=<MAQOLA_ADMIN_KEY>` — kalit env'da; o'rnatilmasa
  endpoint 404 (ochiq qolmasin).

---

## Keyingi qadamlar (hali qilinmagan)

1. **Gumanitar soha uchun manba qidiruvi** — Crossref, ochiq repozitoriylar
   (hozir PubMed Navoiy/Bobur bo'yicha hech narsa topmaydi).
2. **Har bo'limdagi manba sonini avtomatik tekshirish** — "1 manbaga tayanadigan
   bo'lim" bo'lsa ogohlantirish (hozir faqat promptda talab).
3. **Sintez jumlasini tekshirish** — Gemini tekshiruviga "referat belgilari"
   mezonini qo'shish.
