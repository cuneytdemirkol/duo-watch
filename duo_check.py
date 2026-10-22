#!/usr/bin/env python3
"""
GitHub Actions icin iPhone Duo pickup takibi.
LOOP_MINUTES=0  -> tek sorgu (elle test / eski davranis)
LOOP_MINUTES=55 -> 55 dakika boyunca CHECK_EVERY saniyede bir sorgula
Pickup acik olan config varsa ntfy'a push atar.
"""
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
LOOP_MINUTES = int(os.environ.get("LOOP_MINUTES", "0") or 0)
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "90") or 90)

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
_warmed_at = 0.0


def _get(url, accept, referer=None):
    h = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9",
         "sec-ch-ua-platform": '"macOS"', "sec-fetch-site": "same-origin",
         "sec-fetch-mode": "cors" if referer else "navigate",
         "sec-fetch-dest": "empty" if referer else "document"}
    if referer:
        h["Referer"] = referer
    with _opener.open(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def warm():
    global _warmed_at
    _jar.clear()
    _get(WARM_URL, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    _warmed_at = time.time()


def notify(title, msg, priority="urgent"):
    if not NTFY_TOPIC:
        print(f"[ntfy yok] {title}: {msg}")
        return
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
    if time.time() - _warmed_at > 20 * 60:
        warm()
    for attempt in (1, 2):
        try:
            return json.loads(_get(url, "*/*", referer=WARM_URL))
        except Exception:
            if attempt == 1:
                time.sleep(5)
                warm()
                continue
            raise


def check_once(last):
    """last: {(store,label): True} onceki turda acik olanlar. Yeni acilanlar icin bildirim atar."""
    data = fetch()
    stores = data.get("body", {}).get("stores", [])
    hits, quotes, now_open = [], set(), {}
    for st in stores:
        pa = st.get("partsAvailability", {})
        for pn, lbl in PARTS.items():
            info = pa.get(pn, {})
            quote = info.get("pickupSearchQuote") or ""
            quotes.add(quote)
            if str(info.get("pickupDisplay", "")).lower() == "available":
                key = (st.get("storeName"), lbl)
                now_open[key] = True
                if not last.get(key):
                    hits.append(f"{st.get('storeName')} | {lbl} | {quote}")
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts} UTC] {len(stores)} magaza -> "
          f"{'ACIK: ' + str(len(now_open)) if now_open else 'musait degil'} ({' / '.join(sorted(quotes))})",
          flush=True)
    if hits:
        notify("iPhone Duo PICKUP ACILDI (GitHub)", "\n".join(hits))
    if not stores:
        raise RuntimeError("magaza listesi bos")
    return now_open, len(stores)


def main():
    last, fails, n_stores = {}, 0, 0
    deadline = time.time() + LOOP_MINUTES * 60
    while True:
        try:
            last, n_stores = check_once(last)
            fails = 0
        except Exception as e:
            fails += 1
            print(f"HATA ({fails}): {e}", flush=True)
            if LOOP_MINUTES == 0:
                sys.exit(1)
        if LOOP_MINUTES == 0 or time.time() >= deadline:
            break
        time.sleep(CHECK_EVERY if fails < 3 else 240)
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        notify("duo_check test OK", f"GitHub -> ntfy hatti calisiyor ({n_stores} magaza okundu)", "default")


if __name__ == "__main__":
    main()
