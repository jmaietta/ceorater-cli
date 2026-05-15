# CEORater CLI

Command-line interface for [CEORater](https://www.ceorater.com) — institutional-grade CEO performance analytics covering 500+ S&P 500 CEOs.

## Install

```bash
pip install ceorater
```

## Setup

Get your API key at [ceorater.com/api-docs.html](https://www.ceorater.com/api-docs.html), then:

```bash
ceorater configure
```

Or set the `CEORATER_API_KEY` environment variable.

## Commands

### Look up a CEO by ticker

```bash
ceorater lookup NVDA
```

```
  NVIDIA (NVDA)
  CEO: Jensen Huang  |  Founder: Yes  |  Tenure: 27.3 yrs
  Sector: Technology  |  Industry: Semiconductors

  Metric                  Value
  CEORaterScore              98
  AlphaScore                100
  RevCAGR Score             100
  CompScore                   A

  TSR Multiple         589,250%
  Avg Annual TSR        21,578%
  TSR vs SPY           588,370%
  Avg Annual vs SPY     21,546%

  Compensation ($M)      $49.9M
  Cost/1% TSR ($M)        $0.0M
  Revenue CAGR            69.3%
```

### Search by company, CEO, sector, or industry

```bash
ceorater search "technology"
```

### List all CEOs (paginated)

```bash
ceorater list --limit 50
```

### Check data freshness

```bash
ceorater meta
```

### JSON output for agents and scripts

Every data command supports `--json` for raw, machine-readable output:

```bash
ceorater lookup AAPL --json
```

```json
{
  "companyName": "Apple Inc.",
  "ticker": "AAPL",
  "ceoraterScore": 76.2,
  "alphaScore": 93.9,
  "compScore": "C",
  ...
}
```

## Metrics

| Metric | Description |
|--------|-------------|
| CEORaterScore | Composite CEO effectiveness rating (0-100) |
| AlphaScore | Market outperformance score (0-100) |
| RevCAGR Score | Tenure-adjusted revenue growth percentile (0-100) |
| CompScore | Compensation efficiency grade (A-F) |
| TSR Multiple | Total Shareholder Return during tenure |
| Cost/1% TSR | CEO compensation cost per 1% of average annual TSR |

## Requirements

- Python 3.9+
- CEORater API subscription ($99/month) — [subscribe here](https://www.ceorater.com/api-docs.html)

## License

Proprietary. See [terms of service](https://www.ceorater.com/terms.html).
