import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://egy.voxcinemas.com"
PAGES = {
    "whatson": (BASE + "/movies/whatson", "🎬 نزل في السينما"),
    "comingsoon": (BASE + "/movies/comingsoon", "⏳ قريباً"),
}
TOKEN = os.environ["TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
FILE = "seen.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SKIP = {"whatson", "comingsoon"}


def get_movies(url):
    html = requests.get(url, timeout=20, headers=HEADERS).text
    soup = BeautifulSoup(html, "html.parser")
    movies = {}
    for a in soup.find_all("a", href=True):
        path = urlparse(urljoin(BASE, a["href"])).path
        m = re.fullmatch(r"/movies/([^/]+)", path)
        if not m or m.group(1) in SKIP:
            continue
        slug = m.group(1)
        # الاسم: من عنوان h3 لو موجود، وإلا من نص اللينك
        h3 = a.find("h3")
        name = h3.get_text(strip=True) if h3 else a.get_text(strip=True)
        if name and (slug not in movies or len(name) > len(movies[slug])):
            movies[slug] = name
        elif slug not in movies:
            movies[slug] = slug.replace("-", " ").title()
    return movies


def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )
    print("telegram:", r.status_code)


current = {}  # key -> (name, url, label)
for kind, (url, label) in PAGES.items():
    movies = get_movies(url)
    print(kind, "لقيت", len(movies), "فيلم")
    if kind == "whatson" and not movies:
        print("مفيش أفلام اتقرأت من صفحة What's On")
        sys.exit(1)
    for slug, name in movies.items():
        current[f"{kind}:{slug}"] = (name, f"{BASE}/movies/{slug}", label)

seen = set(json.load(open(FILE))) if os.path.exists(FILE) else None

if seen is not None:
    for key in sorted(current.keys() - seen):
        name, link, label = current[key]
        send(f"{label}\n{name}\n{link}")

json.dump(
    sorted((seen or set()) | set(current)),
    open(FILE, "w"),
    ensure_ascii=False,
    indent=0,
)
