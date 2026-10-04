# Maqola — tanqid bo'yicha tuzatish rejasi

**Tanqid:** ilova "referat" darajasidagi maqola chiqaradi — manbalar yonma-yon
qo'yilgan, haqiqiy sintez yo'q.

**Asosiy xulosa:** muammo MODELDA emas, ARXITEKTURADA edi. Buni sinov tasdiqladi:
promptga 6 ta qat'iy qoida qo'shgandan keyin ham model 10 bo'lim ochdi, 4 tasida
3 dan kam manba bo'ldi, taqqoslash iboralari 11 → 5 taga **kamaydi**.

---

## A. Metodologiya

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| A1 | Qidiruv sanasi, filtrlari, nechta natija topilgani yozilmagan | `sources.SEARCH_STATS` qayd etadi: so'rov, har bir bazadan soni, dublikatlar, saralangandan keyingi son, tanlangan son. Methods'ga **haqiqiy raqam** bo'lib o'tadi | ✅ |
| A2 | Tanlab olingan sharh, lekin shunday deb yozilmagan | Methods **kod tomonidan** yoziladi va ochiq aytadi: "bu TANLAB OLINGAN (narrative) sharh, tizimli emas, PRISMA qo'llanilmagan" | ✅ |
| A3 | Manba tanlash mezoni sub'ektiv | Mezon Methods'da ochiq sanab o'tiladi va *tanlab olingan* deb belgilanadi | ✅ |
| A4 | 10 ta manba keng mavzu uchun kam | **25** (so'rovda `max_sources` bilan o'zgartiriladi) | ✅ |

## B. Tarkib va tuzilish

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| B1 | Mavzu haddan keng — 6-7 mavzu yuzaki | **Kod** 3-5 mavzudan ortiq bo'lishiga yo'l qo'ymaydi (`_merge_into_shape`) | ✅ |
| B2 | Har bo'lim 1 manbaga tayanadi | **Kod** har bo'limda ≥3 manba bo'lishini kafolatlaydi; kichik mavzular juftlab birlashtiriladi | ✅ |
| B3 | Sintez yo'q — manbalar yonma-yon | Har bo'lim **alohida so'rovda** yoziladi va model faqat o'sha mavzuning manbalarini ko'radi → sanab chiqishga manba yo'q, taqqoslashga majbur | ✅ |

## C. Ilmiy aniqlik

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| C1 | Namuna hajmi yo'q, lekin shu manbalar ishlatilgan | Qoida: zaif dalildan markaziy xulosa chiqarilmaydi, kontekst sifatida ishlatiladi | ✅ |
| C2 | Cheklovlar qalqon sifatida takrorlanadi | Qoida: ogohlantirish bir marta; takrorlash taqiqlanadi | ✅ |
| C3 | O'z tahlili, tanqidiy taqqoslash yo'q | Har bir da'vo uchun dalil kuchi va sharoit ko'rsatiladi | ✅ |

## D. Format

| # | Tanqid | Tuzatish | Holat |
|---|---|---|---|
| D1 | Uch tilli annotatsiya so'zma-so'z tarjima | Har til o'sha tilning tabiiy ilmiy uslubida yoziladi | ✅ |
| D2 | Kirish darslikdek, tadqiqot savoli yo'q | Kirish oxirida aniq tadqiqot savoli + "nima noma'lum qolgan" | ✅ |

## E. Uzunlik — manba sonidan kelib chiqadi

| Manbalar | So'z nishoni | Izoh |
|---|---|---|
| 7 | 1800-2500 | qisqa sharh |
| 25 | **3782-5117** (~4695) | har manbaga ~188 so'z |
| 40 | 5559-7522 | to'liq sharh |

Ilgari uzunlik manba sonidan qat'i nazar 1800-2500 edi → 25 manbada har
iqtibosga ~90 so'z qolardi, ya'ni yuzaki. Endi `word_range()` va
`section_budgets()` hisoblaydi. Jurnal so'z limiti bo'lsa — **limit ustun**.

---

## ARXITEKTURA (asosiy o'zgarish)

`app/services/structured_writer.py`:

```
plan_themes()          model 3-5 mavzuga guruhlaydi → KOD tekshiradi
                       (_merge_into_shape: kichiklarni juftlab birlashtiradi,
                        >5 bo'lsa kamaytiradi, ishlatilmagan manbani qo'shadi)
   ↓
build_methods_section() 100% KOD — haqiqiy raqamlardan, model yozmaydi
   ↓
write_section()        har bir bo'lim ALOHIDA so'rov, faqat shu mavzuning
                       manbalari ko'rinadi (ko'pi bilan 8 manba,
                       to'liq matn 6000 belgiga qisqartiriladi)
   ↓
assembling             tartib va bo'limlar KOD nazoratida
```

**Kafolat kodda, promptda emas:** bo'limlar soni, har bo'limdagi manba soni,
umumiy uzunlik, Methods mazmuni — hammasi kod tomonidan belgilanadi.

Fallback: structured writer yiqilsa eski bir-so'rovlik usul ishlaydi.

---

## F. Foydalanuvchi hisobi

- Frontend kirganda **bir marta** ism so'raydi, brauzerda saqlaydi.
- Har so'rovda `user_name` yuboriladi; backend ism bo'yicha so'rovlar sonini
  yuritadi (diskda saqlanadi).
- Bu raqam **frontend'da ko'rinmaydi**.
- Ko'rish: `GET /usage?key=<MAQOLA_ADMIN_KEY>`. Kalit o'rnatilmasa yoki xato
  bo'lsa — 404 (endpoint borligi bilinmaydi).

---

## YAKUNIY TEKSHIRUV (25 manba, jonli kod)

| Ko'rsatkich | Tanqiddan keyin | Yakuniy |
|---|---|---|
| So'z soni | 2079 | **5083** |
| Manba qamrovi | 22/25 | **25/25** |
| Taqqoslash iborasi | 5 | **65** |
| Taqqoslashsiz mavzu bo'limi | — | **0** |
| Methods bo'limi | yo'q edi | **bor, 6/6 raqam to'g'ri** |
| Mavzu bo'limlarida manba | 1 ta bo'lardi | **4-7 ta** |
| Takroriy cheklov ogohlantirishi | ko'p marta | 1-4 marta (qalqon emas) |

Bo'limlar: Introduction, Methods: Search Strategy, 5 mavzu bo'limi, Discussion,
Limitations and Future Directions, Conclusion — jami **10**.

Methods'dagi haqiqiy raqamlar: sana, bazalar (PubMed), topilgan 50,
tanlangan 25, "TANLAB OLINGAN (narrative), tizimli emas", "PRISMA
qo'llanilmagan".

## Qo'shimcha qo'riqchilar (sinovlarda topilgan xatolar)

| Xato | Tuzatish |
|---|---|
| Qayta yozish Methods MAZMUNINI almashtirardi (sarlavha qolib, raqamlar yo'qolardi) | `_capture_section`/`_replace_section` — matn qayta yozishdan keyin tiklanadi |
| Qayta yozish tuzilmani buzardi (Methods/Discussion/Limitations yo'qolardi) | Tuzilma qo'riqchisi — buzilsa qayta yozish RAD ETILADI |
| Qayta yozish iqtiboslarni kamaytirardi | Iqtibos qamrovi qo'riqchisi (10% dan ko'p yo'qolsa rad) |
| Mavzu sarlavhalari maqola tilida emas edi | `plan_themes` tilni talab qiladi |
| GPT so'rovi juda tor (12 so'z, kasalliklar ro'yxati) → 3 natija | Promptda namuna + 8 so'z chegarasi kodda + bosqichma-bosqich kengaytirish |
| Bo'sh javobda cheksiz rekursiya (`RecursionError`) | `_fallback_themes` endi `_normalize_themes` ni chaqirmaydi |
| 800 000+ belgilik prompt API'ga sig'masdi | To'liq matn 6000 belgiga qisqartiriladi |

## Modellar

| Vazifa | Model | Holat |
|---|---|---|
| Mavzu → inglizcha kalit so'zlar | **GPT** (`gpt-5.6-luna`) | ✅ ko'chirildi |
| Maqolani yozish | GPT (`gpt-5.6-luna`) | ✅ |
| Maqolani tekshirish | **`gemini-3.5-flash-lite`** | ✅ eng oxirgi mavjud Flash Lite (API'da sinab tasdiqlandi) |
| Mavzu generatsiyasi | Gemini (zaxira zanjiri bilan) | ✅ |

**Diqqat:** `gemini-3.6-flash` (standart model) hozir **429 — kvota tugagan**.
Shuning uchun zaxira ro'yxati ishlaydigan modellardan boshlanadi
(`gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`).
`gemini-3.6-flash-lite` va `gemini-3.7-flash-lite` **mavjud emas** (404).

## Foydalanuvchi hisobi

- Frontend birinchi kirishda **bir marta** ism so'raydi (brauzerda saqlanadi).
- Backend ism bo'yicha so'rovlar sonini yuritadi (diskda saqlanadi).
- **Frontend'da ko'rinmaydi.**
- Ko'rish: `GET /usage?key=<MAQOLA_ADMIN_KEY>` — kalit bo'lmasa/xato bo'lsa 404.

## Hali qilinmagan

1. **Gumanitar soha uchun manba qidiruvi** — Crossref, ochiq repozitoriylar
   (PubMed Navoiy/Bobur bo'yicha hech narsa topmaydi).
2. **Sintez jumlasini avtomatik tekshirish** — hozir faqat promptda talab;
   bo'lim darajasida "taqqoslash bormi" nazorati yo'q.
3. **Gemini kvotasi** — 3.6-flash uchun billing kerak (hozir 3.5-flash
   zaxira ishlaydi, lekin bepul limit maqola soni oshganda yetmasligi mumkin).
