# CEORater CLI

CEO performance from the command line. Total stock return over each CEO's
tenure, the S&P 500's return over that same tenure, how long they have been in
the job, and what they were paid — for 500+ companies.

**Free. No account, no API key, no signup.**

```
pip install ceorater
```

---

## Use it

```
ceorater lookup NVDA
```

```
  NVIDIA (NVDA)
  CEO                   Jensen Huang
  Founder               Yes
  Sector                Information Technology
  Industry              Semiconductors
  Tenure                27.6 yrs
  Total Stock Return    545,800%
  S&P 500 Return        892%
  Compensation          $36.3M
```

Run `ceorater` with no arguments for an interactive session.

### Every CEO

```
ceorater list
```

### Filter

```
ceorater list --sector Energy
ceorater list --industry Semiconductors
ceorater list --founder
ceorater list --sector "Information Technology" --founder
```

Sectors and industries are exact and case-insensitive. To see the valid values:

```
ceorater sectors
ceorater industries --sector "Health Care"
```

### Search

Loose substring match across company, ticker, CEO, sector and industry.

```
ceorater search huang
```

### Get the data out

```
ceorater export ceorater.csv
ceorater list --json > ceorater.json
```

`export` writes all 513 CEOs and all ten fields. Every command takes `--json`.

### Freshness

```
ceorater meta
```

---

## The fields

Exactly the ten www.ceorater.com displays — no more, no less.

| Field | Meaning |
|---|---|
| `ticker` | Exchange ticker |
| `company` | Registrant name as filed |
| `ceo` | Chief executive |
| `founder` | Whether this CEO founded the company |
| `sector` | GICS sector |
| `industry` | GICS sub-industry |
| `tenure_years` | Years in the role |
| `total_return_pct` | Total stock return across the tenure, as a percentage |
| `spy_return_pct` | The S&P 500 over that same period |
| `compensation_musd` | Reported compensation, in millions of USD |

Returns are already percentages: `545800` means +545,800%, the same figure the
website prints. Nothing to convert.

**Sectors and industries are S&P's own GICS values**, matched company by company
on SEC CIK rather than on ticker, because tickers get reassigned and CIKs do
not. Eleven sectors, 128 sub-industries, no second spelling of anything.

**Co-CEOs get a record each.** Oracle, KKR, Globe Life, Lululemon and Netflix
each return two people with their own start dates and their own returns, so
`lookup` prints a card per person and `items` is always a list.

---

## Upgrading from 1.x

Version 1 required a `CEORATER_API_KEY` and called a paid API that no longer
exists — every command in it now fails. Version 2 needs no key and is not
configurable; delete `~/.ceorater/config.json` if you have one.

The scores are gone. CEORaterScore, AlphaScore, RevCAGR Score and CompScore have
been retired from the product, and so has Avg Annual TSR, which was computed as
total return divided by tenure rather than compounded and overstated every
multi-year record. What remains is reported figures only.

---

## API

The CLI is a thin client over a public HTTP API you can call directly:

```
curl -s https://api.ceorater.com/api/v1/ceo/NVDA
```

Documented at https://www.ceorater.com/api-docs.html

Rate limit is 100 requests per 15 minutes per IP. One call to
`/api/v1/ceos` returns every CEO, which is kinder than 513 lookups.

---

## Licence

Proprietary. Free to use, including commercially. Attribution appreciated.
See https://www.ceorater.com/terms.html
