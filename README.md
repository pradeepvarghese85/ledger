# Ledger

Your own portfolio tracker. One web page, plus a job that fetches prices and news for you four times a day.

- **Your dashboard:** https://pradeepvarghese85.github.io/ledger/
- **Your holdings live in your browser**, not in this repository. Nothing here says what you own or what it is worth.

---

## 1. The files, and what each one does

| File | What it is | Do you edit it? |
|---|---|---|
| `index.html` | The dashboard itself | Only when I give you a new one |
| `update.py` | The script that fetches everything | Only when I give you a new one |
| `.github/workflows/update.yml` | The timetable | Only when I give you a new one |
| `data/watchlist.json` | What you own, so it can be priced | **Yes** |
| `data/universe.json` | The companies the Find ideas screen looks at | **Yes** |
| `data/themes.json` | The industries the news follows | **Yes** |
| `data/holidays.json` | Market holidays, used for SIP dates | **Yes** |
| `data/prices.json` | Prices, written by the job | Never |
| `data/screen.json` | Screen measures, written by the job | Never |
| `data/news.json` | Headlines, written by the job | Never |
| `data/fund-codes.json` | Remembered fund matches | Only to clear a wrong match |

**Never upload `my-holdings-backup.json` here.** That file has your real figures in it. Keep it on your computer.

---

## 2. How to edit any file: the only technique you need

1. Open the file in this repository, clicking through the folders.
2. Click the **pencil** icon at the top right.
3. Make your change in the box.
4. Scroll down and click the green **Commit changes** button.

That is all of it. Three rules for the files in `data`, which are all in a format called JSON:

- **Every line in a list ends with a comma, except the last one.**
- **Text goes in double quotes.** Numbers do not.
- **If you break it, the job says so.** Nothing is silently corrupted.

To undo a mistake: open the file, click **History**, open the version before your change, click the three dots, then **Revert**.

---

## 3. Recipes

### I bought a new share

Two steps, and both are needed.

**Step one, in `data/watchlist.json`.** Find the `"stocks"` list and add a line shaped like the others:

```json
{ "code": "TITAN.NS", "name": "Titan" },
```

The code is the Yahoo symbol. Find it by searching the company on finance.yahoo.com and copying the symbol shown beside its name. Indian shares end in `.NS`. US shares have no ending, such as `AAPL`.

**Step two, in the dashboard.** Portfolio, then Add a holding. Put `TITAN.NS` in the **Price feed code** box, written exactly as in the watchlist.

Then run the job, or wait for 3am.

### I bought a new mutual fund

**In `data/watchlist.json`**, in the `"funds"` list:

```json
{ "code": "MF:QUANT-SMALL", "search": "Quant Small Cap Fund Direct Growth", "name": "Quant Small Cap", "isin": "INF966L01986" },
```

- `code` is a label you invent. Anything short, starting with `MF:`, not already used.
- `isin` is what actually identifies the fund. Copy it from your CAS; it starts with `INF`. **With an ISIN the match is exact.** Without one it guesses from the name, and guesses go wrong.
- `search` is only the fallback if the ISIN cannot be found.

Then add the holding in the dashboard with the same code in its Price feed code box.

### I sold something completely

Record the sale on the Sales page, so the tax is right. Then remove its line from `data/watchlist.json`, or leave it, which costs nothing but a wasted request each run.

### I want a new company in the Find ideas screen

In `data/universe.json`, inside `"stocks"`:

```json
{ "code": "DIXON.NS", "name": "Dixon Technologies", "theme": "AI and IT" },
```

`theme` is yours to choose and becomes the **Industry** dropdown on the screen. Reuse an existing word to put the company in that group.

Keep the list under about 150 names so a run stays quick. Anything you hold is screened whether or not it is listed here.

### I want a new industry in the screen

Just use a new word in `theme` on any company. Writing `"theme": "Pharma"` on three companies creates a Pharma option in the dropdown. There is no separate list to maintain.

### I want the news to follow a new industry

In `data/themes.json`, inside `"themes"`:

```json
{
  "name": "Pharma",
  "query": "India pharma sector FDA approvals exports",
  "small": "pharma smallcap stocks India results orders"
},
```

- `name` becomes the Theme dropdown on the News page.
- `query` is the broad search, in plain English, as you would type it into a search engine.
- `small` is the same thing aimed at smaller companies. You can leave it out.

Keep it under about a dozen themes. Each theme is two searches on every run.

### I want to change what the news searches for

Edit the `query` wording. Think of it as a search box: more words means narrower results. `"India defence manufacturing contracts indigenisation"` returns different things from `"defence stocks India"`.

### Adding next year's market holidays

In `data/holidays.json`, inside the market you want, add lines in the form `"YYYY-MM-DD": "why"`:

```json
"2027-01-26": "Republic Day",
"2027-03-02": "Holi",
```

- **India** publishes one year at a time, usually in December, in the NSE trading holiday circular. The dashboard warns you when the calendar is running out, both on the SIP calendar page and in Check-up.
- **US** is already filled in to the end of 2027.
- Weekends are handled automatically and do not belong in this file.

A missing holiday only means a SIP date shows a day early. Nothing breaks.

### A fund matched the wrong scheme

1. Add its `isin` in `data/watchlist.json`, which fixes it permanently.
2. Open `data/fund-codes.json` and delete that fund's entry, so the wrong match is forgotten. Emptying the whole file to `{}` is also fine.
3. Run the job.
4. Check the Data page of the dashboard. Every fund should say **matched by ISIN**.

### My SIP amount changed, or I paused one

In the dashboard, not here. Portfolio, untick Combine, Edit the holding, then change the monthly amount, the day or the status.

### Something stopped updating

Look at the Check-up page first; it names what has no price. The usual causes:

- **The symbol changed.** Search the company on finance.yahoo.com and copy the current symbol.
- **The codes do not match.** The code in the watchlist and the code on the holding must be identical, including the `.NS`.
- **The source refused.** The run log says so, and the old price is kept rather than replaced with nonsense.

---

## 4. Running the job yourself

1. **Actions** tab at the top of this repository.
2. **Update prices and news** on the left.
3. **Run workflow** on the right. Choose what to fetch, then confirm.

| Choice | What it does |
|---|---|
| everything | Prices, NAVs, the screen and the news. About two minutes |
| live | News only |
| close | Prices and news |
| news | News only |
| prices | Prices and NAVs only |
| screen | Rebuilds the Find ideas measures |

It runs by itself on weekdays: **03:00** everything, **09:15** and **12:30** news, **16:15** prices and news, Indian time.

Do not edit files while a run is in progress, or the run cannot save its results.

**After a run,** open it and click into the Fetch step. That log is the only place a wrong fund match or a missing symbol shows up plainly.

---

## 5. After you replace `index.html`

Nothing else is needed. Reload the dashboard, and press **Ctrl+Shift+R** if it looks unchanged. GitHub takes a minute or two to publish.

You do **not** need to run the job after a page change. Only after changing `update.py` or `data/watchlist.json`.

---

## 6. Backups

Your holdings live only in the browser you use. Clearing your browsing data erases them.

- **To back up:** Data page, copy everything in the backup box, keep it somewhere safe.
- **To restore, or to set up another device:** Data page, paste it into the same box, press Restore.
- Each browser keeps its own copy, so a change on your laptop does not appear on your phone.

Do this after any large change, and every few months otherwise.

---

## 7. Where the data comes from

- **Fund NAVs:** AMFI's daily file, matched by ISIN, with mfapi.in as a second route. Free.
- **Share prices:** Yahoo Finance. Free and unofficial, so it can change without notice.
- **News:** Google News. Free.
- **Exchange rates:** Yahoo, fetched every run, so US holdings convert to rupees.

Nothing here is live. NAVs are published once a day, and share prices are the last close.
