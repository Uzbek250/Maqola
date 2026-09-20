# Maqola — arxitektura rejasi (90% avtomatlashtirish)

Maqsad: qo'lyozmani jurnalga topshirishgacha bo'lgan ishning **90% ini ilova bajarsin**,
qolgan 10% ni inson qo'lda tekshirib, o'z nomidan tasdiqlasin.

Hozirgi holat: ilova **zanjirning o'rtasini** qilyapti (manba topish → yozish → Word).
Zanjirning ikki uchi — **oldi** (tayyorlash) va **oxiri** (topshirishga tayyorlash) — yo'q.
Shuning uchun natija "maqola" bo'lib chiqadi, lekin "topshirishga tayyor qo'lyozma" emas.

---

## Ish jarayonining to'liq xaritasi

| # | Qadam | Hozir | Ustuvorlik |
|---|---|---|---|
| 1 | Adabiyot qidirish (PubMed/S2) | ✅ bor | — |
| 2 | DOI haqiqiyligini tekshirish | ✅ bor | — |
| 3 | Maqola tanasi yozish | ✅ bor | — |
| 4 | Sifat tekshiruvi (AI) | ✅ bor | — |
| 5 | Word (.docx) | ✅ bor | — |
| 6 | **Structured abstract + kalit so'zlar** | ✅ **bor** | — |
| 7 | **Ma'lumot ajratish jadvali** | ✅ **bor** | — |
| 8 | **Bayonotlar to'plami** | ✅ **bor** | — |
| 9 | **Title page** (muallif joylari tayyor) | ✅ **bor** | — |
| 10 | **BibTeX/RIS eksport** | ✅ **bor** | — |
| 11 | **Cover letter** | ✅ **bor** | — |
| 12 | **Inson tekshiruvi ro'yxati** | ✅ **bor** | — |
| 13 | **Yagona ZIP paket** | ✅ **bor** | — |
| 14 | **Maqsadli jurnal profili + unga moslash** | ✅ **bor** (8 jurnal) | — |
| 15 | **Muvofiqlik tekshiruvi** | ✅ **bor** | — |
| 16 | **To'liq matnli tahlil** (PMC Open Access) | ✅ **bor** | — |
| 17 | Til sayqali (jurnal darajasiga) | ❌ yo'q | 3 |
| 18 | Antiplagiat / o'xshashlik tekshiruvi | ❌ yo'q | 3 |
| 19 | Model tanlovi (luna/terra A/B) | ⚠️ qisman (1 namuna) | 3 |
| 20 | Taqrizchiga javob (revision) | ❌ yo'q | 4 |

---

## Bosqichlar

### Bosqich 1 — To'liq qo'lyozma paketi  ← shu yerda ishlayapmiz
Zanjirning oxirini yopadi: ilova bitta ZIP beradi, ichida topshirishga kerak bo'lgan
hamma fayl bo'ladi. Inson faqat tekshiradi va muallif ma'lumotlarini to'ldiradi.

- `manuscript_service.py` — bitta LLM chaqiruvida: structured abstract, kalit so'zlar,
  highlights, ma'lumot ajratish jadvali, cover letter (JSON).
- `bibtex` — manba metadatasidan **kod tomonidan** yasaladi (LLM emas — to'qib
  qo'ymasligi uchun), RIS ham.
- Bayonotlar (COI, funding, data availability, author contributions, ethics) —
  **shablon**, muallif to'ldiradi.
- Title page — muallif joylari `[FULL NAME]` ko'rinishida tayyor.
- Inson tekshiruvi ro'yxati — nimalarni qo'lda tekshirish shart (raqamlar, n, xulosalar).
- `/download/{session_id}/package` — ZIP.

### Bosqich 2 — Jurnal profili + muvofiqlik  ✅ BAJARILDI
- `journals.py`: 8 jurnal profili (Cureus, Frontiers in Medicine, Heliyon, JCM,
  Nutrients, Medicine Baltimore, PLOS ONE, BMJ Open) — rasmiy talablardan,
  `source_url` bilan. **3 tasi narrative review qabul qilmaydi** va shunday
  belgilangan.
- Maqola profilga mos yoziladi (so'z limiti, majburiy bo'limlar, havola limiti).
- **Muvofiqlik tekshiruvi**: so'z soni, havola soni, bo'limlar, abstract turi va
  limiti (so'z/belgi), kalit so'zlar, sharh qabul qilinishi, AI siyosati, APC.
  Natija `COMPLIANCE.md` bo'lib ZIP'ga tushadi.

### Bosqich 3 — Manba sifati va to'liq matn  ✅ BAJARILDI (til sayqali qoldi)
- `fulltext.py`: Europe PMC orqali ochiq maqolalarning **to'liq matni** (kalitsiz).
  Sinovda 4/7 manba, 116 637 belgi; bitta maqola abstract'dan **19x** ko'proq.
- Promptda manba `[FULL TEXT]` yoki `[ABSTRACT ONLY]` deb belgilanadi.
- Xarajat: $0.0160 -> $0.0378 maqola boshiga.
- **Qoldi:** til sayqali bosqichi va o'xshashlik tekshiruvi.

### Bosqich 4 — Topshirgandan keyin
- Taqrizchi izohlariga javob (response to reviewers) generatori.
- Jurnal talabiga mos PDF.

---

## Arxitektura qoidalari (buzilmasin)

1. **Ma'lumot to'qilmasin.** LLM ko'rgan matndan chiqarmagan raqamni yozmasin —
   "Not reported" deb yozadi. Jadvalda `n` noma'lum bo'lsa `NR`.
2. **Referenslar kod tomonidan yasaladi** (PubMed/Crossref metadatasidan), LLM dan emas.
   DOI har doim Crossref'da tekshiriladi.
3. **Hech narsa jimgina yo'qolmasin.** Har eksport (BibTeX/RIS/ZIP) manba sonini,
   so'z sonini qaytaradi.
4. **Inson tekshiruvi majburiy qismi hujjat sifatida beriladi** — mijoz nimalarni
   qo'lda ko'zdan kechirishi aniq yozilgan bo'ladi.
