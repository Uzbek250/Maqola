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

## Hali qilinmagan

1. **Gumanitar soha uchun manba qidiruvi** — Crossref, ochiq repozitoriylar
   (PubMed Navoiy/Bobur bo'yicha hech narsa topmaydi).
2. **Sintez jumlasini avtomatik tekshirish** — "bu bo'limda taqqoslash yo'q"
   bo'lsa ogohlantirish (hozir faqat promptda talab).
3. **Guruhlab yozishni o'lchash** — model baribir ba'zi joyda manbani alohida
   gapda aytishi mumkin; statistik nazorat kerak.
