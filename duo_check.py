#!/usr/bin/env python3
"""Tek seferlik kontrol (GitHub Actions icin). Pickup acik olan config varsa ntfy'a push atar."""
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "duo-cuneyt-83kz")

PARTS = {
    "MK244AH/A": "256GB Star White",
    "MK254AH/A": "256GB Night Sky",
    "MK264AH/A": "512GB Star White",
    "MK274AH/A": "512GB Night Sky",
    "MK284AH/A": "1TB Star White",
    "MK294AH/A": "1TB Night Sky",
    "MK2A4AH/A": "2TB Star White",
    "MK2C4AH/A": "2TB Night Sky",
}
PICKUP_URL = "https://www.apple.com/ae/shop/retail/pickup-message"
PRODUCT_URL = "https://www.apple.com/ae/shop/buy-iphone/iphone-duo"
WARM_URL = PRODUCT_URL + "/7.6-inch-display-256gb-night-sky"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))


def _get(url, accept, referer=None):
    h = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9",
         "sec-ch-ua-platform": '"macOS"', "sec-fetch-site": "same-origin",
         "sec-fetch-mode": "cors" if referer else "navigate",
         "sec-fetch-dest": "empty" if referer else "document"}
    if referer:
        h["Referer"] = referer
    with _opener.open(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def notify(title, msg, priority="urgent"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
        headers={"Title": title, "Priority": priority,
                 "Tags": "iphone,rotating_light", "Click": PRODUCT_URL})
    urllib.request.urlopen(req, timeout=15)


def fetch():
    q = {"pl": "true", "mts.0": "regular", "location": "Dubai"}
    for i, pn in enumerate(PARTS):
        q[f"parts.{i}"] = pn
    url = PICKUP_URL + "?" + urllib.parse.urlencode(q)
    for attempt in (1, 2):
        try:
            _jar.clear()
            _get(WARM_URL, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            return json.loads(_get(url, "*/*", referer=WARM_URL))
        except Exception as e:
            if attempt == 1:
                time.sleep(5)
                continue
            raise


def main():
    try:
        data = fetch()
    except Exception as e:
        print(f"HATA: Apple'a ulasilamadi ({e})")
        sys.exit(1)

    stores = data.get("body", {}).get("stores", [])
    hits, quotes = [], set()
    for st in stores:
        pa = st.get("partsAvailability", {})
        for pn, lbl in PARTS.items():
            info = pa.get(pn, {})
            quote = info.get("pickupSearchQuote") or ""
            quotes.add(quote)
            if str(info.get("pickupDisplay", "")).lower() == "available":
                hits.append(f"{st.get('storeName')} | {lbl} | {quote}")

    print(f"{len(stores)} magaza, {len(PARTS)} config -> "
          f"{'ACIK: ' + str(len(hits)) if hits else 'musait degil'} ({' / '.join(sorted(quotes))})")
    if hits:
        notify("iPhone Duo PICKUP ACILDI (GitHub)", "\n".join(hits))
    elif not stores:
        notify("duo_check UYARI", "Apple magaza listesi bos dondu, format degismis olabilir", "high")
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        notify("duo_check test OK", f"GitHub -> ntfy hatti calisiyor ({len(stores)} magaza okundu)", "default")


if __name__ == "__main__":
    main()
