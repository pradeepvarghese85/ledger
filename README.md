# Ledger

A private portfolio tracker. One web page, plus a job that fetches prices every weeknight.

## What is in here

| File | What it does |
|---|---|
| `index.html` | The dashboard. Open it in a browser. Your holdings live in that browser only. |
| `data/watchlist.json` | The list of things to price. Edit this when you buy or sell. |
| `data/prices.json` | Written by the job each night. The page reads it. Do not edit. |
| `data/fund-codes.json` | Remembers which scheme each fund name matched. Delete a line to force a fresh match. |
| `update.py` | Fetches the prices. Plain Python, no libraries to install. |
| `.github/workflows/update.yml` | Runs `update.py` on a schedule. |

## When it runs

18:30 UTC, which is midnight in India, Monday to Friday. AMFI publishes NAVs late in the evening, so a midnight run picks up the same day's values. You can also run it yourself from the Actions tab at any time.

## Where prices come from

- **Mutual funds:** mfapi.in, which publishes AMFI's daily NAVs. Free, no key, no sign-up.
- **Shares and ETFs:** Yahoo Finance's chart endpoint. Free and unofficial, so it can change without notice.

Neither is live. Funds publish one NAV a day. Share prices are the last close.

## Adding a holding

1. Add a line to `data/watchlist.json`:
   - a share, using its Yahoo symbol: `{ "code": "TITAN.NS", "name": "Titan" }`
   - a fund, with any code you like and the scheme name to search for:
     `{ "code": "MF:MY-FUND", "search": "Quant Small Cap Fund Direct Growth", "name": "Quant Small Cap" }`
2. In the dashboard, add the holding and put the same `code` in its **Price feed code** box.
3. Run the job, or wait for the night.

PPF, EPF, NPS, gold and deposits have no free feed. Leave their feed code blank and type the balance in yourself.

## If something stops updating

The dashboard says which holdings did not get a price. Usual causes:

- **The symbol changed.** Search the company on finance.yahoo.com and copy the symbol shown there.
- **The fund matched the wrong scheme.** The page shows what each name matched to. Make the `search` text more exact, delete that fund's line from `data/fund-codes.json`, and run the job again.
- **The code does not match.** The code in the watchlist and the code on the holding must be identical.
- **Yahoo changed its endpoint.** Nothing in the file will fix that; the page keeps showing the last prices it had.

A failed fetch never wipes a price. The previous one is kept and flagged as stale.
