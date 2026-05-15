"""CEORater CLI — command definitions."""

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from ceorater.client import CEORaterError, Client
from ceorater.config import load_key, save_key

console = Console()

SCORE_FIELDS = [
    ("ceoraterScore", "CEORaterScore", "0-100"),
    ("alphaScore", "AlphaScore", "0-100"),
    ("revenueCagrScore", "RevCAGR Score", "0-100"),
    ("compScore", "CompScore", "A-F"),
]

PERF_FIELDS = [
    ("tsrMultiple", "TSR Multiple"),
    ("avgAnnualTsrRatio", "Avg Annual TSR"),
    ("tsrVsSpyRatio", "TSR vs SPY"),
    ("avgAnnualVsSpyRatio", "Avg Annual vs SPY"),
]

COMP_FIELDS = [
    ("compensationMM", "Compensation ($M)"),
    ("compPer1PctTsrMM", "Cost/1% TSR ($M)"),
]


def _get_client() -> Client:
    key = load_key()
    if not key:
        console.print(
            "[red]No API key configured.[/red] Run [bold]ceorater configure[/bold] first."
        )
        sys.exit(1)
    return Client(key)


def _handle_error(e: CEORaterError) -> None:
    if e.status == 401:
        console.print("[red]Unauthorized.[/red] Check your API key with [bold]ceorater configure[/bold].")
    elif e.status == 403:
        console.print(f"[red]Subscription required.[/red] {e}")
    elif e.status == 404:
        console.print(f"[yellow]Not found.[/yellow] {e}")
    else:
        console.print(f"[red]Error {e.status}:[/red] {e}")
    sys.exit(1)


def _fmt_pct(val) -> str:
    if val is None:
        return "-"
    return f"{val * 100:,.0f}%"


def _fmt_score(val) -> str:
    if val is None:
        return "-"
    if isinstance(val, str):
        return val
    return str(round(val))


def _fmt_money(val) -> str:
    if val is None:
        return "-"
    return f"${val:,.1f}M"


def _fmt_years(val) -> str:
    if val is None:
        return "-"
    return f"{val:.1f} yrs"


def _print_ceo_card(ceo: dict) -> None:
    console.print()
    console.print(f"  [bold]{ceo.get('companyName', '')}[/bold] ({ceo.get('ticker', '')})")
    console.print(f"  CEO: {ceo.get('ceo', '')}  |  Founder: {'Yes' if ceo.get('founderCEO') else 'No'}  |  Tenure: {_fmt_years(ceo.get('tenureYears'))}")
    console.print(f"  Sector: {ceo.get('sector', '')}  |  Industry: {ceo.get('industry', '')}")
    console.print()

    t = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    t.add_column("Metric")
    t.add_column("Value", justify="right")

    for key, label, _ in SCORE_FIELDS:
        t.add_row(label, _fmt_score(ceo.get(key)))

    t.add_row("", "")
    for key, label in PERF_FIELDS:
        t.add_row(label, _fmt_pct(ceo.get(key)))

    t.add_row("", "")
    for key, label in COMP_FIELDS:
        t.add_row(label, _fmt_money(ceo.get(key)))

    rev_cagr = ceo.get("revenueCagr")
    if rev_cagr is not None:
        t.add_row("Revenue CAGR", f"{rev_cagr * 100:.1f}%")

    console.print(t)
    console.print()


def _print_ceo_table(items: list[dict]) -> None:
    t = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    t.add_column("Ticker", style="bold")
    t.add_column("Company")
    t.add_column("CEO")
    t.add_column("Score", justify="right")
    t.add_column("Alpha", justify="right")
    t.add_column("RevCAGR", justify="right")
    t.add_column("Comp", justify="center")
    t.add_column("Tenure", justify="right")

    for ceo in items:
        t.add_row(
            ceo.get("ticker", ""),
            (ceo.get("companyName") or "")[:30],
            (ceo.get("ceo") or "")[:25],
            _fmt_score(ceo.get("ceoraterScore")),
            _fmt_score(ceo.get("alphaScore")),
            _fmt_score(ceo.get("revenueCagrScore")),
            ceo.get("compScore") or "-",
            _fmt_years(ceo.get("tenureYears")),
        )

    console.print()
    console.print(t)
    console.print()


# ── CLI Group ────────────────────────────────────────────────────────────────


@click.group()
@click.version_option(package_name="ceorater")
def main():
    """CEORater — CEO performance analytics from the command line."""
    pass


@main.command()
def configure():
    """Save your CEORater API key."""
    key = click.prompt("Enter your CEORater API key", hide_input=True)
    key = key.strip()

    if not key:
        console.print("[red]No key entered.[/red]")
        return

    console.print("Testing connection...", end=" ")
    try:
        client = Client(key)
        meta = client.meta()
        save_key(key)
        count = meta.get("count", "?")
        version = meta.get("api_version", "?")
        console.print(f"[green]Connected.[/green] {count} CEOs available. API v{version}.")
    except CEORaterError as e:
        console.print(f"[red]Failed.[/red] {e}")
    except Exception as e:
        console.print(f"[red]Connection error.[/red] {e}")


@main.command()
@click.argument("ticker")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def lookup(ticker: str, as_json: bool):
    """Look up a CEO by ticker symbol."""
    client = _get_client()
    try:
        data = client.lookup(ticker.upper())
    except CEORaterError as e:
        _handle_error(e)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    if isinstance(data, list):
        for ceo in data:
            _print_ceo_card(ceo)
    else:
        _print_ceo_card(data)


@main.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def search(query: str, as_json: bool):
    """Search by company name, ticker, CEO, sector, or industry."""
    client = _get_client()
    try:
        data = client.search(query)
    except CEORaterError as e:
        _handle_error(e)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    items = data.get("items", [])
    count = data.get("count", len(items))
    console.print(f"\n  [bold]{count}[/bold] result(s) for \"{query}\"")
    if items:
        _print_ceo_table(items)


@main.command("list")
@click.option("--limit", default=20, show_default=True, help="Number of results")
@click.option("--offset", default=0, show_default=True, help="Starting position")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def list_ceos(limit: int, offset: int, as_json: bool):
    """List CEOs (paginated)."""
    client = _get_client()
    try:
        data = client.list_ceos(limit=limit, offset=offset)
    except CEORaterError as e:
        _handle_error(e)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    items = data.get("items", [])
    total = data.get("total", "?")
    console.print(f"\n  Showing {offset + 1}-{offset + len(items)} of [bold]{total}[/bold]")
    if items:
        _print_ceo_table(items)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def meta(as_json: bool):
    """Show API metadata and data freshness."""
    client = _get_client()
    try:
        data = client.meta()
    except CEORaterError as e:
        _handle_error(e)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    console.print()
    console.print(f"  CEOs available : [bold]{data.get('count', '?')}[/bold]")
    console.print(f"  Last updated   : {data.get('last_loaded', '?')}")
    console.print(f"  API version    : {data.get('api_version', '?')}")
    console.print(f"  Base URL       : {data.get('base_url', '?')}")
    console.print()
