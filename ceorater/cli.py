"""CEORater CLI — command definitions.

Every command prints the ten fields www.ceorater.com displays and nothing else.
The scores this CLI was built around -- CEORaterScore, AlphaScore, RevCAGR Score
and CompScore -- have been retired from the product, along with Avg Annual TSR,
which was computed as total return divided by tenure rather than compounded and
overstated every multi-year record.

Returns arrive from the API already as percentages: total_return_pct 545800
means +545,800%, the same figure the website prints.
"""

import csv
import io
import json
import sys
from typing import Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import click
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ceorater import __version__
from ceorater.client import CEORaterError, Client

console = Console()

# The ten fields, in the order the site presents them.
FIELDS = [
    ("ticker", "Ticker"),
    ("company", "Company"),
    ("ceo", "CEO"),
    ("founder", "Founder"),
    ("sector", "Sector"),
    ("industry", "Industry"),
    ("tenure_years", "Tenure"),
    ("total_return_pct", "Total Stock Return"),
    ("spy_return_pct", "S&P 500 Return"),
    ("compensation_musd", "Compensation"),
]

COMMAND_MENU = (
    ("/ticker", "One CEO, every field — e.g. /NVDA"),
    ("/list", "Every CEO"),
    ("/sectors", "The 11 GICS sectors and their counts"),
    ("/search TEXT", "Find by company, ticker, CEO, sector or industry"),
    ("/status", "Row count and data freshness"),
    ("/help", "Show this menu"),
    ("/exit", "Quit"),
)

BRAND_ART = """██████╗███████╗ ██████╗ ██████╗  █████╗ ████████╗███████╗██████╗
██╔═══╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
██║    █████╗  ██║   ██║██████╔╝███████║   ██║   █████╗  ██████╔╝
██║    ██╔══╝  ██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  ██╔══██╗
██████╗███████╗╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗██║  ██║
╚═════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"""


# ----------------------------------------------------------------- formatting

def _pct(v) -> str:
    return "-" if v is None else f"{v:,.0f}%"


def _money(v) -> str:
    return "-" if v is None else f"${v:,.1f}M"


def _years(v) -> str:
    return "-" if v is None else f"{v:.1f} yrs"


def _val(ceo: dict, key: str) -> str:
    v = ceo.get(key)
    if key in ("total_return_pct", "spy_return_pct"):
        return _pct(v)
    if key == "compensation_musd":
        return _money(v)
    if key == "tenure_years":
        return _years(v)
    if key == "founder":
        return "Yes" if v else "No"
    return "-" if v in (None, "") else str(v)


def _print_ceo_card(ceo: dict) -> None:
    """One CEO. Same block layout every command uses, so the field list never
    differs between a lookup, a list and a search."""
    _print_block(ceo)


def _print_block(c: dict) -> None:
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column("Field", style="grey70", no_wrap=True)
    t.add_column("Value", style="white", overflow="fold")
    for key, label in FIELDS:
        style = ""
        if key == "total_return_pct" and isinstance(c.get(key), (int, float)):
            style = "green" if c[key] >= 0 else "red"
        v = _val(c, key)
        t.add_row(label, f"[{style}]{v}[/{style}]" if style else v)
    console.print()
    console.print(t)


def _print_ceo_list(items: list[dict]) -> None:
    """Many CEOs, one block each, in the column order the site uses.

    Not a table. Ten columns need about 185 characters before they are legible;
    below that a table either wraps every column to two letters or drops the
    ones on the right. A block per CEO carries all ten fields at any width,
    which is the same reason the API docs tell PowerShell users Format-List
    rather than Format-Table.
    """
    for c in items:
        _print_block(c)
    console.print()
    console.print(f"  [grey70]{len(items)} CEO(s). --json for raw output, or 'ceorater export' for a CSV.[/grey70]")
    console.print()


# kept so older call sites keep working
_print_ceo_table = _print_ceo_list


def _handle_error(e: CEORaterError, exit_on_error: bool = True) -> None:
    if e.status == 0:
        console.print(f"[red]Could not reach the API.[/red] {e}")
    elif e.status == 404:
        console.print(f"[yellow]Not found.[/yellow] {e}")
    elif e.status == 429:
        console.print("[yellow]Rate limited.[/yellow] 100 requests per 15 minutes. Wait for the window to roll.")
    elif e.status == 503:
        console.print(f"[red]CEO data is temporarily unavailable.[/red] {e}")
    else:
        console.print(f"[red]Error {e.status}:[/red] {e}")
    if exit_on_error:
        sys.exit(1)


def _client() -> Client:
    return Client()


# ----------------------------------------------------------------- runners

def _run_lookup(ticker: str, as_json: bool = False, exit_on_error: bool = True) -> None:
    try:
        data = _client().lookup(ticker)
    except CEORaterError as e:
        _handle_error(e, exit_on_error)
        return
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    items = data.get("items", [])
    if len(items) > 1:
        console.print(f"\n  [grey70]{data.get('ticker')} has {len(items)} co-CEOs.[/grey70]")
    for ceo in items:
        _print_ceo_card(ceo)


def _run_list(limit=None, offset=0, sector=None, industry=None, founder=None,
              as_json=False, exit_on_error=True) -> None:
    try:
        data = _client().list_ceos(limit=limit, offset=offset, sector=sector,
                                   industry=industry, founder=founder)
    except CEORaterError as e:
        _handle_error(e, exit_on_error)
        return
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    items = data.get("items", [])
    bits = [f"{data.get('total', len(items))} CEO(s)"]
    if sector:
        bits.append(f"sector={sector}")
    if industry:
        bits.append(f"industry={industry}")
    if founder is not None:
        bits.append(f"founder={str(founder).lower()}")
    console.print(f"\n  [bold]{' · '.join(bits)}[/bold]")
    if not items:
        console.print("  [yellow]Nothing matched.[/yellow] Try 'ceorater sectors' for the valid values.\n")
        return
    _print_ceo_table(items)


def _run_meta(as_json: bool = False, exit_on_error: bool = True) -> None:
    try:
        data = _client().meta()
    except CEORaterError as e:
        _handle_error(e, exit_on_error)
        return
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column("k", style="grey70", no_wrap=True)
    t.add_column("v", style="white")
    t.add_row("CEOs", str(data.get("count", "-")))
    t.add_row("Last updated", str(data.get("last_updated", "-")))
    t.add_row("Cache age", f"{data.get('cache_age_seconds', '-')}s")
    t.add_row("API version", str(data.get("api_version", "-")))
    t.add_row("Fields", ", ".join(data.get("fields", [])))
    console.print()
    console.print(t)
    console.print()


def _run_sectors(as_json: bool = False, exit_on_error: bool = True) -> None:
    try:
        data = _client().sectors()
    except CEORaterError as e:
        _handle_error(e, exit_on_error)
        return
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    t = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    t.add_column("Sector")
    t.add_column("Companies", justify="right")
    for row in data.get("items", []):
        t.add_row(row.get("sector", "-"), str(row.get("companies", "-")))
    console.print()
    console.print(t)
    console.print(f"  [grey70]{data.get('standard', '')}[/grey70]\n")


# ----------------------------------------------------------------- interactive

def _print_home() -> None:
    width = max(len(l) for l in BRAND_ART.splitlines())
    brand = Text(BRAND_ART, style="bold white")
    brand.append("\n")
    brand.append("CEORater".center(width), style="bold green")
    brand.append("\n")
    brand.append("CEO performance from the command line".center(width), style="green")
    brand.append("\n")
    brand.append(f"v{__version__} · free · no API key".center(width), style="grey70")

    menu = Table(show_header=True, header_style="bold", box=None, padding=(0, 3))
    menu.add_column("Command", style="bold green", no_wrap=True)
    menu.add_column("Description", style="white")
    for c, d in COMMAND_MENU:
        menu.add_row(c, d)

    console.print()
    console.print(Panel(Align.center(brand), border_style="green", padding=(0, 3)))
    console.print(menu)
    console.print()


def _interactive_loop() -> None:
    _print_home()
    while True:
        try:
            raw = console.input("[bold green]ceorater[/bold green] > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if not raw:
            continue
        cmd = raw[1:] if raw.startswith("/") else raw
        low = cmd.lower()
        if low in ("exit", "quit"):
            return
        if low == "help":
            _print_home()
        elif low == "list":
            _run_list(exit_on_error=False)
        elif low == "sectors":
            _run_sectors(exit_on_error=False)
        elif low == "status":
            _run_meta(exit_on_error=False)
        elif low.startswith("search "):
            q = cmd[7:].strip()
            try:
                data = _client().search(q)
                console.print(f"\n  [bold]{data.get('count', 0)}[/bold] result(s) for \"{q}\"")
                if data.get("items"):
                    _print_ceo_table(data["items"])
            except CEORaterError as e:
                _handle_error(e, exit_on_error=False)
        else:
            _run_lookup(cmd, exit_on_error=False)


# ----------------------------------------------------------------- commands

@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ceorater")
@click.pass_context
def main(ctx: click.Context):
    """CEORater — CEO performance from the command line. Free, no API key."""
    if ctx.invoked_subcommand is None:
        _interactive_loop()


@main.command()
@click.argument("ticker")
@click.option("--json", "as_json", is_flag=True, help="Raw JSON")
def lookup(ticker: str, as_json: bool):
    """One CEO by ticker. Co-CEOs return a card each."""
    _run_lookup(ticker, as_json=as_json)


@main.command("list")
@click.option("--limit", type=int, default=None, help="Default: every CEO")
@click.option("--offset", type=int, default=0, show_default=True)
@click.option("--sector", default=None, help="Exact GICS sector, e.g. 'Energy'")
@click.option("--industry", default=None, help="Exact GICS sub-industry")
@click.option("--founder/--no-founder", "founder", default=None, help="Founder-led only")
@click.option("--json", "as_json", is_flag=True, help="Raw JSON")
def list_ceos(limit, offset, sector, industry, founder, as_json):
    """Every CEO. Filter with --sector, --industry or --founder."""
    _run_list(limit=limit, offset=offset, sector=sector, industry=industry,
              founder=founder, as_json=as_json)


@main.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Raw JSON")
def search(query: str, as_json: bool):
    """Substring search across company, ticker, CEO, sector and industry."""
    try:
        data = _client().search(query)
    except CEORaterError as e:
        _handle_error(e)
        return
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    console.print(f"\n  [bold]{data.get('count', 0)}[/bold] result(s) for \"{query}\"")
    if data.get("items"):
        _print_ceo_table(data["items"])


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Raw JSON")
def sectors(as_json: bool):
    """The 11 GICS sectors, with a company count for each."""
    _run_sectors(as_json=as_json)


@main.command()
@click.option("--sector", default=None, help="Only this sector's sub-industries")
@click.option("--json", "as_json", is_flag=True, help="Raw JSON")
def industries(sector, as_json):
    """GICS sub-industries, with a company count for each."""
    try:
        data = _client().industries(sector=sector)
    except CEORaterError as e:
        _handle_error(e)
        return
    if as_json:
        click.echo(json.dumps(data, indent=2))
        return
    t = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    t.add_column("Industry", overflow="fold")
    t.add_column("Sector", overflow="fold")
    t.add_column("Companies", justify="right")
    for row in data.get("items", []):
        t.add_row(row.get("industry", "-"), row.get("sector", "-"), str(row.get("companies", "-")))
    console.print()
    console.print(t)
    console.print(f"  [grey70]{data.get('standard', '')}[/grey70]\n")


@main.command()
@click.argument("path", type=click.Path(dir_okay=False, writable=True), default="ceorater.csv")
@click.option("--sector", default=None, help="Only this sector")
def export(path: str, sector):
    """Write every CEO and every field to a CSV."""
    try:
        data = _client().list_ceos(sector=sector)
    except CEORaterError as e:
        _handle_error(e)
        return
    items = data.get("items", [])
    if not items:
        console.print("[yellow]Nothing to write.[/yellow]")
        return
    cols = [k for k, _ in FIELDS]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(items)
    console.print(f"  Wrote [bold]{len(items)}[/bold] CEOs and {len(cols)} fields to [bold]{path}[/bold]")


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Raw JSON")
def meta(as_json: bool):
    """Row count and data freshness."""
    _run_meta(as_json=as_json)
