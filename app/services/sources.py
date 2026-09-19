"""
Haqiqiy ilmiy manbalarni topish servisi.
MUHIM: bu modul AI'dan mustaqil ishlaydi. Hech qachon AI'ga "manba to'qi" demaymiz -
avval shu yerdan HAQIQIY maqolalarni topamiz, keyin AI'ga faqat shularni beramiz.

Sifat siyosati:
- Yangi maqolalar ustuvor (so'nggi bir necha yil, aks holda mavzu bo'yicha eskirgan bo'lishi mumkin)
- Semantic Scholar uchun citation soni bo'yicha saralanadi (ko'proq iqtibos = ko'proq ishonchli manba)
- Abstract'i yo'q yoki juda qisqa manbalar chiqarib tashlanadi (AI'ga foyda bermaydi)
"""
import httpx
import math
from datetime import datetime
from app.config import NCBI_API_KEY, NCBI_EMAIL, SEMANTIC_SCHOLAR_API_KEY

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

MIN_ABSTRACT_LENGTH = 200  # bundan qisqa abstract AI uchun deyarli foydasiz
RECENCY_YEARS = 6  # shundan eski maqolalar "eskirgan" deb hisoblanadi (chiqarilmaydi, faqat pastroq saralanadi)


async def search_pubmed(query: str, max_results: int = 15) -> list[dict]:
    """
    PubMed'dan (tibbiyot/biomeditsina uchun eng ishonchli, bepul, kalitsiz) qidiradi.
    max_results kattaroq so'raladi, chunki keyin filtrlab-saralab, eng yaxshilarini tanlaymiz.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
            "email": NCBI_EMAIL,
        }
        if NCBI_API_KEY:
            search_params["api_key"] = NCBI_API_KEY

        resp = await client.get(PUBMED_SEARCH_URL, params=search_params)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "rettype": "abstract",
            "retmode": "xml",
            "email": NCBI_EMAIL,
        }
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY

        fetch_resp = await client.get(PUBMED_FETCH_URL, params=fetch_params)
        fetch_resp.raise_for_status()

        return _parse_pubmed_xml(fetch_resp.text)


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    results = []

    for article in root.findall(".//PubmedArticle"):
        try:
            pmid = article.findtext(".//PMID", default="")
            title = article.findtext(".//ArticleTitle", default="").strip()

            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join(a.text or "" for a in abstract_parts).strip()

            authors = []
            for author in article.findall(".//Author"):
                last = author.findtext("LastName", default="")
                initials = author.findtext("Initials", default="")
                if last:
                    authors.append(f"{last} {initials}".strip())

            journal = article.findtext(".//Journal/Title", default="")
            year_text = article.findtext(".//PubDate/Year", default="")
            if not year_text:
                medline_date = article.findtext(".//PubDate/MedlineDate", default="")
                year_text = medline_date[:4] if medline_date else ""

            doi = ""
            for el_id in article.findall(".//ArticleId"):
                if el_id.get("IdType") == "doi":
                    doi = el_id.text or ""

            if title and len(abstract) >= MIN_ABSTRACT_LENGTH:
                results.append({
                    "source": "PubMed",
                    "id": pmid,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "journal": journal,
                    "year": year_text,
                    "doi": doi,
                    "citation_count": None,  # PubMed bu ma'lumotni bermaydi
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })
        except Exception:
            continue

    return results


async def search_semantic_scholar(query: str, max_results: int = 15) -> list[dict]:
    """
    Semantic Scholar'dan qidiradi. citationCount ham so'raladi - bu manba sifatini
    baholashda muhim mezon (ko'p iqtibos qilingan maqola ko'proq ishonch uyg'otadi).

    API kalit bo'lsa `x-api-key` sarlavhasida yuboriladi — aks holda kalitsiz
    foydalanuvchilar bilan umumiy limit bo'lishilib, 429 (Too Many Requests) olinadi.
    """
    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,venue,externalIds,url,citationCount",
        }
        resp = await client.get(SEMANTIC_SCHOLAR_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        results = []
        for paper in data:
            abstract = paper.get("abstract") or ""
            if len(abstract) < MIN_ABSTRACT_LENGTH:
                continue
            results.append({
                "source": "Semantic Scholar",
                "id": paper.get("paperId", ""),
                "title": paper.get("title", ""),
                "abstract": abstract,
                "authors": [a.get("name", "") for a in paper.get("authors", [])],
                "journal": paper.get("venue", ""),
                "year": str(paper.get("year", "")) if paper.get("year") else "",
                "doi": paper.get("externalIds", {}).get("DOI", ""),
                "citation_count": paper.get("citationCount"),
                "url": paper.get("url", ""),
            })
        return results


def _quality_score(source: dict) -> float:
    """
    Manbani saralash uchun bitta ball hisoblaydi. Yuqoriroq ball = yuqoriroq ustuvorlik.
    - Yangilik: joriy yildan qancha uzoq bo'lsa, ball shuncha kamayadi
    - Citation soni: ko'proq iqtibos = qo'shimcha ball (log shkala, bitta "viral" maqola
      hammasini bosib ketmasligi uchun)
    """
    current_year = datetime.now().year
    score = 0.0

    try:
        year = int(source.get("year") or 0)
        age = max(current_year - year, 0)
        recency_score = max(0.0, 1.0 - (age / (RECENCY_YEARS * 2)))
        score += recency_score * 10
    except (ValueError, TypeError):
        pass

    citations = source.get("citation_count")
    if citations is not None and citations > 0:
        score += math.log10(citations + 1) * 3

    return score


async def find_sources(
    query: str,
    prefer_medical: bool = True,
    max_results: int = 10,
) -> list[dict]:
    """
    Asosiy funksiya: manbalarni yig'adi, sifat bo'yicha saralaydi, eng yaxshilarini qaytaradi.
    Ko'proq so'raladi (zaxira bilan), keyin saralab eng yaxshilari tanlanadi - shunda
    "birinchi topilgan" emas, "eng sifatli" manbalar AI'ga beriladi.
    """
    raw_pool_size = max_results * 2
    results = []

    if prefer_medical:
        try:
            results = await search_pubmed(query, raw_pool_size)
        except Exception as e:
            print(f"PubMed xatosi: {e}")

    if len(results) < raw_pool_size:
        try:
            extra = await search_semantic_scholar(query, raw_pool_size - len(results))
            results.extend(extra)
        except Exception as e:
            print(f"Semantic Scholar xatosi: {e}")

    seen_titles = set()
    unique_results = []
    for r in results:
        key = r["title"].strip().lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_results.append(r)

    unique_results.sort(key=_quality_score, reverse=True)
    return unique_results[:max_results]
