#!/usr/bin/env python3
"""
Fetches a price for everything in data/watchlist.json and writes data/prices.json.
Runs on a schedule in GitHub Actions. Uses only the Python standard library.

Sources
  Mutual funds : mfapi.in  (AMFI NAV data, free, no key)
  Stocks       : Yahoo Finance chart endpoint (free, unofficial, may change)

Nothing here can fail the run: anything that cannot be fetched keeps its previous
price and is listed under "stale" in the output, so the dashboard can say so.
"""

import json, os, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
WATCH = os.path.join(DATA, "watchlist.json")
OUT = os.path.join(DATA, "prices.json")
CACHE = os.path.join(DATA, "fund-codes.json")
UA = "Mozilla/5.0 (compatible; personal-portfolio-tracker/1.0)"
IST = timezone(timedelta(hours=5, minutes=30))


def get(url, tries=3):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if n == tries - 1:
                print("   failed:", type(e).__name__, str(e)[:120])
                return None
            time.sleep(2 * (n + 1))


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def score(name, want):
    """Rough match score between a scheme name and what we asked for."""
    n, w = name.lower(), want.lower()
    s = sum(2 for t in w.replace("&", " ").split() if len(t) > 2 and t in n)
    if "direct" in n:
        s += 6
    if "growth" in n:
        s += 4
    for bad in ("idcw", "dividend", "payout", "reinvest", "regular plan", "bonus"):
        if bad in n:
            s -= 8
    return s


def find_scheme(search):
    res = get("https://api.mfapi.in/mf/search?q=" + urllib.parse.quote(search))
    if not res:
        return None, None
    best = max(res, key=lambda r: score(r.get("schemeName", ""), search))
    if score(best.get("schemeName", ""), search) < 6:
        return None, None
    return best.get("schemeCode"), best.get("schemeName")


def main():
    w = load(WATCH, {})
    old = load(OUT, {"prices": {}})
    oldp = old.get("prices", {})
    codes = load(CACHE, {})
    prices, stale, notes = {}, [], []

    print("Funds")
    for f in w.get("funds", []):
        code, sch = f["code"], codes.get(f["code"])
        if not sch:
            sc, name = find_scheme(f["search"])
            if sc:
                sch = {"scheme": sc, "matched": name}
                codes[code] = sch
                notes.append("Matched %s to: %s" % (f["name"], name))
                print("   matched %s -> %s (%s)" % (f["name"], name, sc))
            else:
                print("   NO MATCH for", f["name"])
                notes.append("Could not find a scheme for %s. Edit its 'search' text in watchlist.json." % f["name"])
        if sch:
            d = get("https://api.mfapi.in/mf/%s/latest" % sch["scheme"])
            row = (d or {}).get("data") or []
            if row:
                prices[code] = {
                    "price": float(row[0]["nav"]),
                    "date": row[0]["date"],
                    "name": f["name"],
                    "matched": sch.get("matched", ""),
                    "kind": "nav",
                }
                print("   %-34s %10s  %s" % (f["name"], row[0]["nav"], row[0]["date"]))
                continue
        if code in oldp:
            prices[code] = oldp[code]
        stale.append(f["name"])

    print("Stocks")
    for s in w.get("stocks", []):
        code = s["code"]
        d = get("https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1d&range=5d" % urllib.parse.quote(code))
        meta = (((d or {}).get("chart") or {}).get("result") or [{}])[0].get("meta") or {}
        px = meta.get("regularMarketPrice")
        if px:
            ts = meta.get("regularMarketTime")
            prices[code] = {
                "price": float(px),
                "date": datetime.fromtimestamp(ts, IST).strftime("%d-%m-%Y") if ts else "",
                "name": s["name"],
                "currency": meta.get("currency", ""),
                "kind": "price",
            }
            print("   %-34s %10.2f" % (s["name"], px))
        else:
            if code in oldp:
                prices[code] = oldp[code]
            stale.append(s["name"])
            print("   %-34s  no price" % s["name"])

    out = {
        "updated": datetime.now(IST).strftime("%d-%m-%Y %H:%M IST"),
        "count": len(prices),
        "stale": stale,
        "notes": notes,
        "prices": prices,
    }
    os.makedirs(DATA, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    with open(CACHE, "w") as f:
        json.dump(codes, f, indent=1, sort_keys=True)
    print("\nWrote %d prices. %d could not be fetched." % (len(prices), len(stale)))


if __name__ == "__main__":
    main()
