#!/usr/bin/env python3
"""Tek seferlik kontrol (GitHub Actions icin). Pickup acik olan config varsa ntfy'a push atar."""
import json
import os
import sys
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
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")


def notify(title, msg, priority="urgent"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
        headers={"Title": title, "Priority": priority,
                 "Tags": "iphone,rotating_light", "Click": PRODUCT_URL})
    urllib.request.urlopen(req, timeout=15)


def main():
    q = {"pl": "true", "mts.0": "regular", "location": "Dubai"}
    for i, pn in enumerate(PARTS):
        q[f"parts.{i}"] = pn
    req = urllib.request.Request(
        PICKUP_URL + "?" + urllib.parse.urlencode(q),
        headers={"User-Agent": UA, "Accept": "application/json",
                 "Accept-Language": "en-AE,en;q=0.9", "Referer": PRODUCT_URL})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
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
