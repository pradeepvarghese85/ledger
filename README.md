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

### My monthly SIP went through

On the **SIP calendar** page, under **Instalments to confirm**. Each row shows the date, the amount and the price for that day, and works out the units. Change the date if your statement shows a different one, check the amount, then press **Confirm**. If an instalment bounced, press **Not taken**.

Nothing is added to your holdings until you press Confirm. The price box stays empty when the NAV for that day is not published yet, so either wait for the next run or type the figure from your statement.

### I want to bring in a CAMS or KFintech statement

**Data** page, the first section, **Detailed CAS, with every transaction**. Ask CAMS or KFintech for the *detailed* statement, not the monthly summary, and choose your own period.

What it does: units, cost and value are **replaced** by the statement's figures, redemptions are recorded **for tax only** so nothing is subtracted twice, and funds you have exited are marked rather than deleted. Purchases are never added again, because the closing balance already includes them. Your shares, PPF, EPF, gold, income and bills are untouched.

Before pressing the button: copy your backup, check the **In your list** column, and fix the name of anything that says *new* but is really something you already hold, or you will end up with two rows.

### A sale covers many SIP instalments and I cannot give one purchase date

In the sale, set **Tax treatment** to Short term or Long term instead of leaving it to work the dates out. Get the split from your **capital gains statement**, which CAMS and KFintech send for each financial year and which already applies first-in-first-out and the pre-2018 grandfathering. If a sale is part long term and part short, record it as two sales.

The **Tax** page has a year dropdown, so a redemption from last financial year goes under that year, not this one.

### I want to write down why I own something

Edit the holding. Three boxes at the bottom: **Why you own it**, **What would make you sell**, and **Review it on**. The first two show on the holding's card, and an overdue review is listed on the Check-up page. Nothing else uses them; they exist so that in a year you can judge the decision rather than the outcome.

### I want to set my own limits

On the **Sell or hold** page, under *Your own rules*: the most in any one holding, the most in any one group, and the least in cash. The page then names what is out of line and the smallest trade that fixes it.

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

The screen is rebuilt once a day at 03:00. News updates four times a day. Prices and NAVs update at 03:00 and again at 16:15, after the Indian close.

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
- **News:** Google News, searching the industries in `data/themes.json`. Free.
- **The Find ideas screen:** a year of daily prices for the names in `data/universe.json`, from Yahoo.
- **The index comparison:** the Nifty 50 and Nifty 500, priced like any other symbol.

## 8. Alerts

The 03:00 and 16:15 runs write `data/alerts.json` and raise a **GitHub issue** listing anything notable: a holding that moved more than 7% since the last run, a price that has gone stale, a 12-month high, or something more than 35% below its high. GitHub emails you when an issue is raised, so you hear about it without opening the dashboard. Close the issue once you have read it. The same list appears at the top of the Dashboard.
- **Exchange rates:** Yahoo, fetched every run, so US holdings convert to rupees.

Nothing here is live. NAVs are published once a day, and share prices are the last close.
