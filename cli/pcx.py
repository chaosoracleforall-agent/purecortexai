"""PURECORTEX CLI — Interact with sovereign AI agents on Algorand."""

import json
import os
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich import box
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="pcx",
    help="PURECORTEX CLI — Sovereign AI Agent Infrastructure on Algorand",
    no_args_is_help=True,
)
console = Console()

DEFAULT_API = "https://purecortex.ai"

DEFAULT_PROTOCOL_INFO = {
    "factory_app_id": 757172168,
    "cortex_asset_id": 757172171,
    "tge": "2026-03-31T00:00:00Z",
}


def load_protocol_info() -> dict:
    """Load protocol constants from the canonical deployment manifest when present."""
    config_path = Path(__file__).resolve().parents[1] / "deployment.testnet.json"
    if not config_path.exists():
        return DEFAULT_PROTOCOL_INFO.copy()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return {
            "factory_app_id": data["contracts"]["agentFactory"]["appId"],
            "cortex_asset_id": data["contracts"]["cortexToken"]["assetId"],
            "tge": data.get("tgeDate", DEFAULT_PROTOCOL_INFO["tge"]),
        }
    except Exception:
        return DEFAULT_PROTOCOL_INFO.copy()


PROTOCOL_INFO = load_protocol_info()


def get_api_url() -> str:
    return os.environ.get("PURECORTEX_API_URL", DEFAULT_API)


def get_api_key(required: bool = False) -> str | None:
    api_key = os.environ.get("PURECORTEX_API_KEY")
    if required and not api_key:
        console.print(
            "[bold red]PURECORTEX_API_KEY is required for this command.[/bold red]\n"
            "Export it first, for example:\n"
            "[dim]export PURECORTEX_API_KEY=ctx_your_key[/dim]"
        )
        raise typer.Exit(1)
    return api_key


# ── Status & Health ──────────────────────────────────────────────

@app.command()
def status():
    """Check the health and status of the PURECORTEX backend."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/health", timeout=10)
        r.raise_for_status()
        data = r.json()
        deps = data.get("dependencies", {})
        console.print(
            Panel(
                f"[bold green]Backend Online[/bold green]\n"
                f"Version: {data.get('version', '?')}\n"
                f"Overall status: {data.get('status', 'unknown')}\n"
                f"Redis: {deps.get('redis', 'unknown')}\n"
                f"Orchestrator: {deps.get('orchestrator', 'unknown')}\n"
                f"Agent loop: {deps.get('agent_loop', 'unknown')}",
                title="PURECORTEX Status",
                border_style="blue",
            )
        )
    except httpx.RequestError as e:
        console.print(f"[bold red]Connection failed:[/bold red] {e}")
        raise typer.Exit(1)


# ── Transparency ─────────────────────────────────────────────────

@app.command()
def supply():
    """Show CORTEX token supply breakdown."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/api/transparency/supply", timeout=10)
        r.raise_for_status()
        data = r.json()

        table = Table(title="CORTEX Supply", box=box.ROUNDED, border_style="blue")
        table.add_column("Category", style="bold")
        table.add_column("Amount", justify="right")
        table.add_column("Pct", justify="right", style="cyan")

        for item in data.get("allocation", []):
            table.add_row(
                item["label"],
                f"{item['amount']:,.0f}",
                f"{item['pct']}%",
            )

        console.print(table)
        console.print(f"\n  Total: [bold]{data.get('total_supply', 0):,.0f}[/bold] CORTEX")
        console.print(f"  Burned: [bold red]{data.get('burned', 0):,.0f}[/bold red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def treasury():
    """Show treasury fund balances."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/api/transparency/treasury", timeout=10)
        r.raise_for_status()
        data = r.json()
        console.print_json(json.dumps(data, indent=2))
    except httpx.RequestError as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def burns():
    """Show buyback-burn history."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/api/transparency/burns", timeout=10)
        r.raise_for_status()
        data = r.json()
        total = data.get("total_burned", 0)
        console.print(f"Total Burned: [bold red]{total:,.0f}[/bold red] CORTEX")
        history = data.get("burn_history", [])
        if not history:
            console.print("[dim]No burns yet. Burns begin after TGE.[/dim]")
        else:
            for entry in history:
                console.print(f"  {entry}")
    except httpx.RequestError as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Agents ───────────────────────────────────────────────────────

@app.command()
def agents():
    """List all registered AI agents."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/api/agents/registry", timeout=10)
        r.raise_for_status()
        data = r.json()

        table = Table(title="Protocol AI Agents", box=box.ROUNDED, border_style="blue")
        table.add_column("Name", style="bold")
        table.add_column("Role")
        table.add_column("Status", justify="center")
        table.add_column("Address")

        for agent in data.get("agents", []):
            status_style = "green" if agent.get("status") == "active" else "yellow"
            table.add_row(
                agent.get("name", "?"),
                agent.get("role", "?"),
                f"[{status_style}]{agent.get('status', '?')}[/]",
                (agent.get("algorand_address") or "TBD")[:16] + "...",
            )

        console.print(table)
    except httpx.RequestError as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def chat(
    agent_name: str = typer.Argument("senator", help="Agent to chat with: senator, curator, social"),
):
    """Chat with a PURECORTEX AI agent."""
    api = get_api_url()
    api_key = get_api_key(required=True)
    console.print(f"[bold blue]Connecting to {agent_name.title()} Agent...[/bold blue]")
    console.print("[dim]Type 'exit' to quit.[/dim]\n")

    while True:
        try:
            msg = console.input("[bold cyan]You:[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            break
        if msg.strip().lower() in ("exit", "quit", "q"):
            break

        try:
            r = httpx.post(
                f"{api}/api/agents/{agent_name}/chat",
                headers={"X-API-Key": api_key},
                json={"message": msg},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            response = data.get("response", data.get("message", "No response"))
            console.print(f"[bold green]{agent_name.title()}:[/bold green] {response}\n")
        except httpx.RequestError as e:
            console.print(f"[red]Error:[/red] {e}\n")


# ── Governance ───────────────────────────────────────────────────

@app.command()
def proposals():
    """List governance proposals."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/api/governance/proposals", timeout=10)
        r.raise_for_status()
        data = r.json()
        props = data.get("proposals", [])
        if not props:
            console.print("[dim]No active proposals. Governance launches at TGE.[/dim]")
        else:
            for p in props:
                console.print(f"  #{p['id']} — {p['title']} [{p['status']}]")
    except httpx.RequestError as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def constitution():
    """Display the PURECORTEX Constitution preamble."""
    api = get_api_url()
    try:
        r = httpx.get(f"{api}/api/governance/constitution", timeout=10)
        r.raise_for_status()
        data = r.json()
        console.print(Panel(
            data.get("preamble", "")[:2000] + "\n\n[dim]Full text at https://purecortex.ai/governance[/dim]",
            title="PURECORTEX Constitution — Preamble",
            border_style="blue",
        ))
    except httpx.RequestError as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Info ─────────────────────────────────────────────────────────

@app.command()
def info():
    """Show PURECORTEX protocol information."""
    console.print(
        Panel(
            "[bold]PURECORTEX[/bold] — Sovereign AI Agent Infrastructure\n\n"
            "Chain: Algorand Testnet\n"
            f"Factory App ID: {PROTOCOL_INFO['factory_app_id']}\n"
            f"CORTEX Asset ID: {PROTOCOL_INFO['cortex_asset_id']}\n"
            "Total Supply: 10,000,000,000,000,000 CORTEX\n"
            f"TGE: {PROTOCOL_INFO['tge']}\n\n"
            "Website: https://purecortex.ai\n"
            "API: https://purecortex.ai/api\n"
            "Docs: https://purecortex.ai/docs/api",
            title="Protocol Info",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    app()
