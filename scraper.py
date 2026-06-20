"""
scraper.py
----------
Scrapes technology articles from BBC Technology and saves them to data/articles.json.

Usage:
    python scraper.py
    python scraper.py --max 60   (scrape more articles)
"""

import argparse
import json
import os
import time

import requests
from bs4 import BeautifulSoup

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL  = "https://www.bbc.com"
TECH_URL  = "https://www.bbc.com/technology"
HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY   = 1.0   # seconds between requests (be polite)
REQUEST_TIMEOUT = 12    # seconds


# ── Helpers ────────────────────────────────────────────────────────────────────

def fetch(url: str) -> BeautifulSoup | None:
    """GET a URL and return a BeautifulSoup object, or None on failure."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return None


def get_article_links(page_url: str) -> list[str]:
    """Return unique article URLs from a BBC Technology listing page."""
    soup = fetch(page_url)
    if not soup:
        return []

    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        # BBC article URLs look like /news/articles/<id>
        if "/news/articles/" in href:
            full = BASE_URL + href if href.startswith("/") else href
            if full not in links:
                links.append(full)

    print(f"  Found {len(links)} links on {page_url}")
    return links


def scrape_article(url: str) -> dict | None:
    """Scrape a single article. Returns structured dict or None if too thin."""
    soup = fetch(url)
    if not soup:
        return None

    # Title
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # Date
    time_tag = soup.find("time")
    date = time_tag.get_text(strip=True) if time_tag else "Unknown"
    if time_tag and time_tag.get("datetime"):
        date = time_tag["datetime"]

    # Author
    author = "BBC"

    # Body
    body = soup.find("article") or soup.find("main")
    if body:
        content = " ".join(
            p.get_text(strip=True)
            for p in body.find_all("p")
            if p.get_text(strip=True)
        )
    else:
        content = ""

    # Skip thin articles (ads, redirects, etc.)
    if not title or len(content) < 150:
        return None

    return {
        "title":   title,
        "url":     url,
        "author":  author,
        "date":    date,
        "content": content,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def run(max_articles: int = 50) -> None:
    os.makedirs("data", exist_ok=True)

    print("=" * 55)
    print("  BBC Technology Scraper")
    print("=" * 55)

    # Collect links across multiple pages
    all_links: list[str] = []
    for page in range(1, 2):
        url = TECH_URL if page == 1 else f"{TECH_URL}?page={page}"
        print(f"\n[Page {page}] {url}")
        all_links.extend(get_article_links(url))
        time.sleep(REQUEST_DELAY)

    # Deduplicate and cap
    all_links = list(dict.fromkeys(all_links))[:max_articles]
    print(f"\n[INFO] Scraping {len(all_links)} articles …\n")

    articles: list[dict] = []
    for i, url in enumerate(all_links, 1):
        print(f"[{i:>2}/{len(all_links)}] {url}")
        article = scrape_article(url)
        if article:
            articles.append(article)
            print(f"       ✓  {article['title'][:70]}")
        else:
            print(f"       ✗  skipped (thin content)")
        time.sleep(REQUEST_DELAY)

    # Save
    out = "data/articles.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 55}")
    print(f"  Done — {len(articles)} articles saved to {out}")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dawn Tech News Scraper")
    parser.add_argument("--max", type=int, default=50, help="Max articles to scrape")
    args = parser.parse_args()
    run(max_articles=args.max)
