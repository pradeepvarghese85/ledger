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
NEWS = os.path.join(DATA, "news.json")
THEMES = os.path.join(DATA, "themes.json")
CACHE = os.path.join(DATA, "fund-codes.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
IST = timezone(timedelta(hours=5, minutes=30))


def get(url, tries=3, as_json=True):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/plain,application/json,*/*",
                "Accept-Language": "en-IN,en;q=0.9",
                "Connection": "close",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
            return json.loads(body) if as_json else body
        except Exception as e:
            if n == tries - 1:
                print("   failed:", type(e).__name__, str(e)[:120])
                return None
            time.sleep(2 * (n + 1))


def to_iso(d):
    """'01-Oct-2026' or '05-10-2026' -> '2026-10-01'. Returns '' if it cannot tell."""
    d = (d or "").strip()
    m = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
         "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    p = d.replace("/", "-").split("-")
    if len(p) != 3:
        return ""
    try:
        day = int(p[0])
        mon = m.get(p[1][:3].lower()) or int(p[1])
        return "%04d-%02d-%02d" % (int(p[2]), mon, day)
    except Exception:
        return ""


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
    by_isin, by_code, rows = {}, {}, []
    txt = None
    for url in ("https://www.amfiindia.com/spages/NAVAll.txt",
                "https://portal.amfiindia.com/spages/NAVAll.txt",
                "http://portal.amfiindia.com/spages/NAVAll.txt"):
        print("   trying", url)
        txt = get(url, tries=2, as_json=False)
        if txt and ";" in txt:
            break
        txt = None
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


def mfapi(f, codes):
    """Second route when AMFI's file will not download.

    mfapi.in has no ISIN search, so we search by name, then open each candidate
    and keep the one whose ISIN matches the one in the watchlist. That keeps the
    lookup exact even though the search itself is by name.
    """
    code, want, isin = f["code"], f.get("search") or f.get("name", ""), (f.get("isin") or "").upper()
    sc = codes.get(code, {}).get("scheme") or f.get("scheme")
    if not sc:
        res = get("https://api.mfapi.in/mf/search?q=" + urllib.parse.quote(want))
        if not isinstance(res, list):
            return None, ""
        cands = [r for r in res if isinstance(r, dict) and r.get("schemeName")]
        cands.sort(key=lambda r: score(r["schemeName"], want), reverse=True)
        for r in cands[:6]:
            d = get("https://api.mfapi.in/mf/%s" % r["schemeCode"])
            meta = (d or {}).get("meta") or {}
            got = [str(meta.get(k, "")).upper() for k in ("isin_growth", "isin_div_reinvestment")]
            if isin and isin in got:
                sc = r["schemeCode"]
                codes[code] = {"scheme": sc, "matched": r["schemeName"]}
                print("      ISIN confirmed against mfapi: %s" % r["schemeName"])
                break
        if not sc and cands and not isin and score(cands[0]["schemeName"], want) >= 6:
            sc = cands[0]["schemeCode"]
            codes[code] = {"scheme": sc, "matched": cands[0]["schemeName"]}
    if not sc:
        return None, ""
    d = get("https://api.mfapi.in/mf/%s/latest" % sc)
    row = (d or {}).get("data") or []
    if not row:
        return None, ""
    name = ((d or {}).get("meta") or {}).get("scheme_name") or codes.get(code, {}).get("matched", "")
    return ({"scheme": str(sc), "name": name, "nav": row[0]["nav"], "date": row[0]["date"]},
            "matched by ISIN (mfapi)" if isin and codes.get(code) else "matched by name (mfapi)")


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


def past_navs(scheme):
    """The last few weeks of NAVs for one scheme, so a late confirmation finds its own day."""
    if not scheme:
        return {}
    d = get("https://api.mfapi.in/mf/%s" % scheme)
    rows = (d or {}).get("data") or []
    out = {}
    for row in rows[:45]:
        iso = to_iso(row.get("date"))
        if iso:
            try:
                out[iso] = float(row["nav"])
            except Exception:
                pass
    return out


def past_closes(code):
    """A month of daily closes, from the same chart request that gives the latest price."""
    d = get("https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1d&range=1mo"
            % urllib.parse.quote(code))
    res = (((d or {}).get("chart") or {}).get("result") or [{}])[0]
    ts = res.get("timestamp") or []
    closes = (((res.get("indicators") or {}).get("quote") or [{}])[0].get("close")) or []
    out = {}
    for i, t in enumerate(ts):
        if i < len(closes) and closes[i]:
            out[datetime.fromtimestamp(t, IST).strftime("%Y-%m-%d")] = float(closes[i])
    return out, res.get("meta") or {}


def headlines(query, limit=4):
    """Headlines from Google News. Titles and links only, nothing more."""
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query + " when:10d")
           + "&hl=en-IN&gl=IN&ceid=IN:en")
    xml = get(url, tries=2, as_json=False)
    if not xml or "<item" not in xml:
        return []
    out = []
    for block in xml.split("<item>")[1:limit + 1]:
        def field(tag):
            a = block.find("<%s>" % tag)
            b = block.find("</%s>" % tag)
            if a < 0 or b < 0:
                return ""
            t = block[a + len(tag) + 2:b]
            t = t.replace("<![CDATA[", "").replace("]]>", "")
            for k, v in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
                t = t.replace(k, v)
            return t.strip()
        title, link = field("title"), field("link")
        if not title:
            continue
        src = field("source") or ""
        if " - " in title and not src:                 # Google appends the source
            title, src = title.rsplit(" - ", 1)
        out.append({"title": title[:180], "link": link, "source": src[:60], "when": field("pubDate")[:16]})
    return out


def news(w, holdings=True):
    """One file of headlines: the markets, your themes, small-company angles, and your own holdings."""
    t = load(THEMES, {})
    data = {"updated": datetime.now(IST).strftime("%d-%m-%Y %H:%M IST"),
            "market": [], "themes": {}, "small": {}, "items": {}}
    seen = set()

    def fresh(arts):
        out = []
        for a in arts:
            key = a["title"].lower()[:70]
            if key in seen:
                continue
            seen.add(key)
            out.append(a)
        return out

    print("News")
    for row in t.get("market", []):
        for a in fresh(headlines(row.get("query", ""), 3)):
            a["scope"] = row.get("name", "Markets")
            data["market"].append(a)
        time.sleep(0.3)
    print("   markets: %d" % len(data["market"]))

    for th in t.get("themes", []):
        name = th.get("name") or ""
        if not name:
            continue
        data["themes"][name] = fresh(headlines(th.get("query", name), 5))
        time.sleep(0.3)
        if th.get("small"):
            data["small"][name] = fresh(headlines(th["small"], 4))
            time.sleep(0.3)
        print("   %-34s %d broad, %d small company" % (name, len(data["themes"][name]), len(data["small"].get(name, []))))

    if holdings:
        hit = 0
        for group in ("stocks", "funds"):
            for row in w.get(group, []):
                name = row.get("name") or ""
                if not name:
                    continue
                arts = fresh(headlines(name, 3))
                if arts:
                    data["items"][row["code"]] = {"name": name, "articles": arts}
                    hit += 1
                time.sleep(0.4)
        print("   holdings with news: %d" % hit)
    else:
        old = load(NEWS, {})
        data["items"] = old.get("items", {})
        print("   holdings: kept from the last full run")
    return data


def main(news_only=False):
    w = load(WATCH, {})
    if news_only:
        print("News-only run")
        n = news(w, holdings=False)
        if n["market"] or n["themes"] or n["items"]:
            with open(NEWS, "w") as f:
                json.dump(n, f, indent=1, sort_keys=True)
            print("Wrote news only. Prices were not touched.")
        else:
            print("Nothing came back, so the old news file is kept.")
        return
    old = load(OUT, {"prices": {}})
    oldp = old.get("prices", {})
    codes = load(CACHE, {})
    prices, stale, notes, back = {}, [], [], {}

    print("Funds")
    by_isin, by_code, rows = amfi()
    if not rows:
        print("   AMFI's file would not download. Falling back to mfapi.in.")
        notes.append("AMFI's file would not download, so NAVs came from mfapi.in instead.")
    for f in w.get("funds", []):
      try:
          code = f["code"]
          r, how = pick(f, by_isin, by_code, rows) if rows else mfapi(f, codes)
          if r:
              prices[code] = {"price": float(r["nav"]), "date": r["date"], "name": f["name"],
                              "matched": r["name"], "how": how, "scheme": r["scheme"], "kind": "nav"}
              back[code] = past_navs(r.get("scheme"))
              print("   %-30s %10s  %s  (%s: %s)" % (f["name"], r["nav"], r["date"], how, r["name"]))
              if how == "matched by name":
                  notes.append("%s matched by name to: %s" % (f["name"], r["name"]))
              continue
          print("   NO MATCH for", f["name"])
          notes.append("Could not find %s from either source." % f["name"])
          if code in oldp:
              prices[code] = oldp[code]
          stale.append(f["name"])
      except Exception:
          print("   error on", f.get("name", "?"))
          traceback.print_exc()
          stale.append(f.get("name", "?"))

    print("Exchange rates")
    for pair in ("USDINR", "HKDINR", "CNYINR"):
        d = get("https://query1.finance.yahoo.com/v8/finance/chart/%s=X?interval=1d&range=5d" % pair)
        meta = (((d or {}).get("chart") or {}).get("result") or [{}])[0].get("meta") or {}
        px = meta.get("regularMarketPrice")
        key = "FX:" + pair
        if px:
            prices[key] = {"price": float(px), "name": pair[:3] + " to INR", "kind": "fx",
                           "date": datetime.now(IST).strftime("%d-%m-%Y")}
            print("   %-10s %10.4f" % (pair, px))
        elif key in oldp:
            prices[key] = oldp[key]
            print("   %-10s  kept the previous rate" % pair)

    print("Stocks")
    for s in w.get("stocks", []):
      try:
          code = s["code"]
          closes, meta = past_closes(code)
          back[code] = closes
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

    # keep a rolling 120 days of prices, so a SIP confirmed late still uses the
    # right day's NAV rather than today's
    hist = old.get("history", {})
    for code, past in back.items():
        if past:
            hist.setdefault(code, {}).update(past)
    cutoff = (datetime.now(IST) - timedelta(days=120)).strftime("%Y-%m-%d")
    for code, p in prices.items():
        iso = to_iso(p.get("date"))
        if not iso:
            continue
        hist.setdefault(code, {})[iso] = p["price"]
    for code in list(hist):
        hist[code] = dict((d, v) for d, v in hist[code].items() if d >= cutoff)
        if not hist[code]:
            del hist[code]

    out = {
        "updated": datetime.now(IST).strftime("%d-%m-%Y %H:%M IST"),
        "history": hist,
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

    try:
        n = news(w)
        if n["market"] or n["items"]:
            with open(NEWS, "w") as f:
                json.dump(n, f, indent=1, sort_keys=True)
        else:
            print("   nothing came back, so the old news file is kept")
    except Exception:
        print("   news step failed, the rest of the run is unaffected")
        traceback.print_exc()
    print("\nWrote %d prices. %d could not be fetched." % (len(prices), len(stale)))
    if not prices:
        print("\nNOTHING was fetched. Both sources failed, or watchlist.json did not load.")
        print("watchlist has %d stocks and %d funds" % (len(w.get("stocks", [])), len(w.get("funds", []))))


if __name__ == "__main__":
    try:
        main(news_only=(len(sys.argv) > 1 and sys.argv[1] == "news"))
    except Exception:
        print("\nThe script stopped with an error. The line that matters is the last one:")
        traceback.print_exc()
        sys.exit(1)
