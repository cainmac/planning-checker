import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

EALING_BASE = "https://pam.ealing.gov.uk"
EALING_RESULTS_URL = EALING_BASE + "/online-applications/simpleSearchResults.do"


def scrape(address: str, max_pages: int = 10):
    """
    Fetch ALL planning applications for an address from Ealing,
    following the "Next" link (class='next') up to max_pages.
    """
    session = requests.Session()

    payload = {
        "action": "firstPage",
        "searchType": "Application",
        "searchCriteria.caseStatus": "",
        "searchCriteria.simpleSearchString": address,
        "searchCriteria.simpleSearch": "true",
    }

    results = []
    current_url = EALING_RESULTS_URL
    page_num = 0

    while current_url and page_num < max_pages:
        if page_num == 0:
            resp = session.get(current_url, params=payload, timeout=10)
        else:
            resp = session.get(current_url, timeout=10)

        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        for li in soup.select("li.searchresult"):
            a = li.select_one("a")
            if not a:
                continue

            title = a.get_text(strip=True)
            href = a.get("href", "")
            full_url = urljoin(EALING_BASE, href)

            addr_el = li.select_one(".address")
            addr_text = addr_el.get_text(strip=True) if addr_el else ""

            results.append(
                {
                    "title": title,
                    "url": full_url,
                    "address": addr_text,
                }
            )

        next_link = soup.select_one("a.next")

        if not next_link or not next_link.get("href"):
            break

        current_url = urljoin(EALING_BASE, next_link["href"])
        page_num += 1

    return results
