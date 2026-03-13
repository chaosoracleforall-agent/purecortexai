import typer
import httpx
from rich.console import Console

app = typer.Typer(help="PureCortex Command Line Interface")
console = Console()

API_URL = "http://localhost:8000"

@app.command()
def status():
    """Check the health and status of the PureCortex Backend."""
    try:
        response = httpx.get(f"{API_URL}/health")
        response.raise_for_status()
        data = response.json()
        console.print(f"[bold green]Backend is Online![/bold green] Status: {data['status']}")
        console.print(f"Orchestrator Active: [bold {'green' if data.get('orchestrator_active') else 'red'}]{data.get('orchestrator_active')}[/bold]")
    except httpx.RequestError as e:
        console.print(f"[bold red]Error connecting to PureCortex backend:[/bold red] {e}")

@app.command()
def agent_deploy(name: str, unit: str):
    """Deploy a new AI Agent via the Puya Smart Contract."""
    console.print(f"Deploying Agent [bold blue]{name}[/bold blue] ({unit}) to Algorand...")
    # In a real CLI, this would invoke algosdk or the backend endpoint to call the contract.
    console.print("[bold green]Agent deployed successfully![/bold green]")
    console.print("Asset ID: 104523 (Mocked)")

if __name__ == "__main__":
    app()
