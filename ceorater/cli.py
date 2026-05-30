"""CEORater CLI — command definitions."""

import io
import json
import math
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

COMMAND_MENU = (
    ("/ticker", "CEO Analytics by ticker"),
    ("/list", "List CEOs"),
    ("/status", "Dataset freshness and API status"),
    ("/help", "Show this menu"),
    ("/exit", "Quit"),
)

BRAND_ART = """██████╗███████╗ ██████╗ ██████╗  █████╗ ████████╗███████╗██████╗
██╔═══╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
██║    █████╗  ██║   ██║██████╔╝███████║   ██║   █████╗  ██████╔╝
██║    ██╔══╝  ██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  ██╔══██╗
██████╗███████╗╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗██║  ██║
╚═════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"""


def _print_home() -> None:
    brand_width = max(len(line) for line in BRAND_ART.splitlines())
    brand = Text(BRAND_ART, style="bold white")
    brand.append("\n")
    brand.append("CEORater".center(brand_width), style="bold green")
    brand.append("\n")
    brand.append("CEO Analytics from the command line".center(brand_width), style="green")
    brand.append("\n")
    brand.append(f"v{__version__}".center(brand_width), style="grey70")

    menu = Table(show_header=True, header_style="bold", box=None, padding=(0, 3))
    menu.add_column("Command", style="bold green", no_wrap=True)
    menu.add_column("Description", style="white")
    for command, description in COMMAND_MENU:
        menu.add_row(command, description)

    console.print()
    console.print(Panel(Align.center(brand), border_style="green", padding=(0, 3)))
    console.print(menu)
    console.print()


def _get_client(exit_on_missing: bool = True) -> Optional[Client]:
    key = load_key()
    if not key:
        console.print(
            "[red]No API key found.[/red] Set [bold]CEORATER_API_KEY[/bold] in your environment and try again."
        )
        if exit_on_missing:
            sys.exit(1)
        return None
    return Client(key)


def _handle_error(e: CEORaterError, exit_on_error: bool = True) -> None:
    if e.status == 401:
        console.print("[red]Unauthorized.[/red] Check your [bold]CEORATER_API_KEY[/bold] environment variable.")
    elif e.status == 403:
        console.print(f"[red]Subscription required.[/red] {e}")
    elif e.status == 404:
        console.print(f"[yellow]Not found.[/yellow] {e}")
    else:
        console.print(f"[red]Error {e.status}:[/red] {e}")
    if exit_on_error:
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
    return str(math.floor(val + 0.5))


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


def _run_lookup(ticker: str, as_json: bool = False, exit_on_error: bool = True) -> None:
    client = _get_client(exit_on_missing=exit_on_error)
    if client is None:
        return

    try:
        data = client.lookup(ticker.upper())
    except CEORaterError as e:
        _handle_error(e, exit_on_error=exit_on_error)
        return

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    if isinstance(data, list):
        for ceo in data:
            _print_ceo_card(ceo)
    else:
        _print_ceo_card(data)


def _run_list_ceos(
    limit: int = 20,
    offset: int = 0,
    as_json: bool = False,
    exit_on_error: bool = True,
) -> None:
    client = _get_client(exit_on_missing=exit_on_error)
    if client is None:
        return

    try:
        data = client.list_ceos(limit=limit, offset=offset)
    except CEORaterError as e:
        _handle_error(e, exit_on_error=exit_on_error)
        return

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    items = data.get("items", [])
    total = data.get("total", "?")
    console.print(f"\n  Showing {offset + 1}-{offset + len(items)} of [bold]{total}[/bold]")
    if items:
        _print_ceo_table(items)


def _run_meta(as_json: bool = False, exit_on_error: bool = True) -> None:
    client = _get_client(exit_on_missing=exit_on_error)
    if client is None:
        return

    try:
        data = client.meta()
    except CEORaterError as e:
        _handle_error(e, exit_on_error=exit_on_error)
        return

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    console.print()
    console.print(f"  CEOs available : [bold]{data.get('count', '?')}[/bold]")
    console.print(f"  Last updated   : {data.get('last_loaded', '?')}")
    console.print(f"  API version    : {data.get('api_version', '?')}")
    console.print(f"  Base URL       : {data.get('base_url', '?')}")
    console.print()


def _interactive_loop() -> None:
    _print_home()

    while True:
        try:
            raw = console.input("[bold green]ceorater>[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            console.print()
            return

        line = raw.strip()
        if not line:
            continue

        if not line.startswith("/"):
            console.print("[yellow]Commands start with /.[/yellow] Type [bold]/help[/bold].")
            continue

        command = line[1:].strip()
        if not command:
            continue

        parts = command.split()
        verb = parts[0].lower()

        if verb in ("exit", "quit", "q"):
            console.print("[grey70]Goodbye.[/grey70]")
            return

        if verb == "help":
            _print_home()
            continue

        if verb == "status":
            if len(parts) > 1:
                console.print("[yellow]Usage:[/yellow] /status")
                continue
            _run_meta(exit_on_error=False)
            continue

        if verb == "list":
            limit = 20
            if len(parts) > 1:
                try:
                    limit = int(parts[1])
                except ValueError:
                    console.print("[yellow]Usage:[/yellow] /list")
                    continue
            _run_list_ceos(limit=limit, exit_on_error=False)
            continue

        if len(parts) == 1:
            _run_lookup(parts[0].upper(), exit_on_error=False)
            continue

        console.print("[yellow]Unknown command.[/yellow] Type [bold]/help[/bold].")


# ── CLI Group ────────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True, no_args_is_help=False)
@click.version_option(version=__version__, prog_name="ceorater")
@click.pass_context
def main(ctx: click.Context):
    """CEORater — CEO performance analytics from the command line."""
    if ctx.invoked_subcommand is None:
        _interactive_loop()


@main.command(hidden=True)
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
    _run_lookup(ticker, as_json=as_json)


@main.command(hidden=True)
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
    _run_list_ceos(limit=limit, offset=offset, as_json=as_json)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def meta(as_json: bool):
    """Show API metadata and data freshness."""
    _run_meta(as_json=as_json)
