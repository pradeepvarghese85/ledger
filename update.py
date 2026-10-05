#!/usr/bin/env python3
"""
Fetches a price for everything in data/watchlist.json and writes data/prices.json.
Runs on a schedule in GitHub Actions. Uses only the Python standard library.

Sources
  Mutual funds : AMFI's own daily NAV file, matched by ISIN (exact, no guessing)
  Stocks       : Yahoo Finance chart endpoint (free, unofficial, may change)

Nothing here can fail the run: anything that cannot be fetched keeps its previous
price and is listed under "stale" in the output, so the dashboard can say so.
"""

import json, os, sys, time, traceback, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
WATCH = os.path.join(DATA, "watchlist.json")
OUT = os.path.join(DATA, "prices.json")
UA = "Mozilla/5.0 (compatible; personal-portfolio-tracker/1.0)"
IST = timezone(timedelta(hours=5, minutes=30))


def get(url, tries=3, as_json=True):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
            return json.loads(body) if as_json else body
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


STOP = {"fund", "scheme", "plan", "direct", "regular", "growth", "option", "the", "and"}


def words(s):
    s = s.lower().replace("&", " and ")
    s = "".join(c if c.isalnum() else " " for c in s)
    return [t for t in s.split() if len(t) > 2 and t not in STOP]


def flat(s):
    return "".join(c for c in s.lower() if c.isalnum())      # so "mid cap" == "midcap"


def score(name, want):
    """Every word asked for must appear; every extra word counts against it.
    That is what stops 'Kotak Nifty Midcap 50 Index Fund' beating 'Kotak Mid Cap Fund'."""
    n, nf, af = name.lower(), flat(name), flat(want)
    s = 0
    for t in words(want):
        s += 3 if t in nf else -6
    for t in words(name):
        if t not in af:
            s -= 6
    if "direct" in n:
        s += 6
    if "growth" in n:
        s += 4
    for bad in ("idcw", "dividend", "payout", "reinvest", "bonus"):
        if bad in n:
            s -= 12
    if "regular plan" in n or n.rstrip().endswith("regular"):
        s -= 12
    return s


def amfi():
    """AMFI's daily file: every scheme, its ISIN, its NAV. Returns (by ISIN, by code, all rows).

    Each line is: code ; ISIN growth ; ISIN reinvest ; name ; NAV ; date
    """
    txt = get("https://www.amfiindia.com/spages/NAVAll.txt", as_json=False)
    by_isin, by_code, rows = {}, {}, []
    if not txt:
        return by_isin, by_code, rows
    for line in txt.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        row = {"scheme": parts[0], "name": parts[3], "nav": parts[4], "date": parts[5]}
        try:
            float(row["nav"])
        except ValueError:
            continue
        rows.append(row)
        by_code[parts[0]] = row
        for isin in (parts[1], parts[2]):
            if isin and isin != "-":
                by_isin[isin.upper()] = row
    print("AMFI file: %d schemes" % len(rows))
    return by_isin, by_code, rows


def pick(f, by_isin, by_code, rows):
    """Finds one fund's row. ISIN first, then a pinned code, then the name."""
    if f.get("isin"):
        r = by_isin.get(f["isin"].upper())
        if r:
            return r, "matched by ISIN"
        print("   ISIN %s is not in the AMFI file" % f["isin"])
    if f.get("scheme"):
        r = by_code.get(str(f["scheme"]))
        if r:
            return r, "pinned scheme code"
        print("   scheme code %s is not in the AMFI file" % f["scheme"])
    want = f.get("search") or f.get("name") or ""
    if not want or not rows:
        return None, ""
    ranked = sorted(rows, key=lambda r: score(r["name"], want), reverse=True)
    if score(ranked[0]["name"], want) < 6:
        return None, ""
    for r in ranked[1:3]:
        print("      runner-up: %s" % r["name"])
    return ranked[0], "matched by name"


def main():
    w = load(WATCH, {})
    old = load(OUT, {"prices": {}})
    oldp = old.get("prices", {})
    prices, stale, notes = {}, [], []

    print("Funds")
    by_isin, by_code, rows = amfi()
    if not rows:
        print("   AMFI's file could not be downloaded. Every fund keeps its previous NAV.")
        notes.append("AMFI's NAV file could not be downloaded on this run.")
    for f in w.get("funds", []):
      try:
          code = f["code"]
          r, how = pick(f, by_isin, by_code, rows) if rows else (None, "")
          if r:
              prices[code] = {"price": float(r["nav"]), "date": r["date"], "name": f["name"],
                              "matched": r["name"], "how": how, "scheme": r["scheme"], "kind": "nav"}
              print("   %-30s %10s  %s  (%s: %s)" % (f["name"], r["nav"], r["date"], how, r["name"]))
              if how == "matched by name":
                  notes.append("%s matched by name to: %s" % (f["name"], r["name"]))
              continue
          if rows:
              print("   NO MATCH for", f["name"])
              notes.append("Could not find %s. Add its ISIN to watchlist.json." % f["name"])
          if code in oldp:
              prices[code] = oldp[code]
          stale.append(f["name"])
      except Exception:
          print("   error on", f.get("name", "?"))
          traceback.print_exc()
          stale.append(f.get("name", "?"))

    print("Stocks")
    for s in w.get("stocks", []):
      try:
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
      except Exception:
        print("   error on", s.get("name", "?"))
        traceback.print_exc()
        stale.append(s.get("name", "?"))

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
    print("\nWrote %d prices. %d could not be fetched." % (len(prices), len(stale)))
    if not prices:
        print("\nNOTHING was fetched. Both sources failed, or watchlist.json did not load.")
        print("watchlist has %d stocks and %d funds" % (len(w.get("stocks", [])), len(w.get("funds", []))))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nThe script stopped with an error. The line that matters is the last one:")
        traceback.print_exc()
        sys.exit(1)
