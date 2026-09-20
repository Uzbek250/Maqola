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
| 6 | **Structured abstract + kalit so'zlar** | ❌ yo'q | **1** |
| 7 | **Ma'lumot ajratish jadvali** (dizayn, n, populyatsiya) | ❌ yo'q | **1** |
| 8 | **Bayonotlar to'plami** (COI, funding, data availability, hissa) | ⚠️ qisman | **1** |
| 9 | **Title page** (muallif, affiliation, ORCID, corresponding) | ❌ yo'q | **1** |
| 10 | **BibTeX/RIS eksport** (Zotero/EndNote uchun) | ❌ yo'q | **1** |
| 11 | **Cover letter** | ❌ yo'q | **1** |
| 12 | **Inson tekshiruvi ro'yxati** | ❌ yo'q | **1** |
| 13 | **Yagona ZIP paket** (jurnal talab qiladigan fayl to'plami) | ❌ yo'q | **1** |
| 14 | **Maqsadli jurnal profili + unga moslash** | ❌ yo'q | **2** |
| 15 | **Muvofiqlik tekshiruvi** (so'z/ref limiti, majburiy bo'limlar) | ❌ yo'q | **2** |
| 16 | **To'liq matnli tahlil** (abstract o'rniga PMC Open Access) | ❌ yo'q | **3** |
| 17 | Til sayqali (jurnal darajasiga) | ⚠️ qisman | **3** |
| 18 | Antiplagiat / o'xshashlik tekshiruvi | ❌ yo'q | **3** |
| 19 | Model tanlovi (luna/terra A/B) | ⚠️ qilingan | **3** |
| 20 | Taqrizchiga javob (revision) | ❌ yo'q | **4** |

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

### Bosqich 2 — Jurnal profili + muvofiqlik
- `journals.py`: jurnal profillari (so'z limiti, tuzilma, ref uslubi, majburiy bo'limlar,
  abstract turi). Standart + mijoz qo'shadigan profillar.
- Maqola profilga moslab yoziladi (masalan Cureus tuzilmasi boshqacha).
- **Muvofiqlik tekshiruvi**: so'z soni, ref soni, majburiy bo'limlar bor-yo'qligi —
  natijada "✅/⚠️" ro'yxati. Bu insonning 10% ini ham yengillashtiradi.

### Bosqich 3 — Manba sifati va to'liq matn
- PMC Open Access'dan **to'liq matn** olish (hozir faqat abstract) — sifat shiftini
  ko'taradigan eng katta qadam.
- Til sayqali: alohida "language editor" bosqichi.
- O'xshashlik: yozilgan matn manbalarga juda o'xshab ketmaganini tekshirish.

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
