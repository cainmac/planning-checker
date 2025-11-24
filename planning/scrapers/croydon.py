# planning/scrapers/croydon.py

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

CROYDON_BASE = "https://publicaccess3.croydon.gov.uk"
SEARCH_PAGE_URL = CROYDON_BASE + "/online-applications/"
RESULTS_URL = CROYDON_BASE + "/online-applications/simpleSearchResults.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0 Safari/537.36"
    )
}


def scrape(address: str, max_pages: int = 10):
    """
    Fetch ALL planning applications for an address from Croydon,
    following the 'Next' link (class='next') up to max_pages.

    Returns list of dicts: {title, url, address}
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # 1) Hit the main page first to obtain cookies/session
    try:
        session.get(SEARCH_PAGE_URL, timeout=10)
    except Exception as e:
        raise RuntimeError(f"Croydon initial page request failed: {e}") from e

    payload = {
        "action": "firstPage",
        "searchType": "Application",
        "searchCriteria.caseStatus": "",
        "searchCriteria.simpleSearchString": address,
        "searchCriteria.simpleSearch": "true",
    }

    results = []
    current_url = RESULTS_URL
    page_num = 0

    while current_url and page_num < max_pages:
        try:
            if page_num == 0:
                # FIRST PAGE: Croydon likely expects POSTed form data
                resp = session.post(current_url, data=payload, timeout=10)
            else:
                # SUBSEQUENT PAGES: follow the pagination URL as GET
                resp = session.get(current_url, timeout=10)
        except Exception as e:
            raise RuntimeError(f"Croydon request failed on page {page_num+1}: {e}") from e

        if resp.status_code != 200:
            raise RuntimeError(
                f"Croydon returned HTTP {resp.status_code} on page {page_num+1}"
            )

        soup = BeautifulSoup(resp.text, "html.parser")

        # ---- extract results ----
        for li in soup.select("li.searchresult"):
            a = li.select_one("a")
            if not a:
                continue

            title = a.get_text(strip=True)
            href = a.get("href", "")
            full_url = urljoin(CROYDON_BASE, href)

            addr_el = li.select_one(".address")
            addr_text = addr_el.get_text(strip=True) if addr_el else ""

            results.append(
                {
                    "title": title,
                    "url": full_url,
                    "address": addr_text,
                }
            )

        # ---- pagination: <a class="next" href="..."> ----
        next_link = soup.select_one("a.next")
        if not next_link or not next_link.get("href"):
            break

        current_url = urljoin(CROYDON_BASE, next_link["href"])
        page_num += 1

    return results
