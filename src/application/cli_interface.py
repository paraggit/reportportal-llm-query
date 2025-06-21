import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..utils.config import Config
from ..utils.logger import setup_logger
from .response_generator import ResponseGenerator
from .session_manager import SessionManager

console = Console()


class CLIInterface:
    """Command-line interface for the Report Portal LLM Query system."""

    def __init__(self, config_path: str = "config/config.yaml"):
        # Load configuration from YAML file
        self.config = Config.from_yaml(config_path)

        # Setup logger with the loaded config
        setup_logger(self.config)

        # Pass the config object (not config_path) to other components
        self.response_generator = ResponseGenerator(self.config)
        self.session_manager = SessionManager(self.config)
        self.session_id = None

    async def start_interactive_session(self):
        """Start an interactive query session."""
        console.print(
            Panel.fit(
                "[bold blue]Report Portal LLM Query Interface[/bold blue]\n"
                "Type your questions about test executions. Type 'exit' to quit.",
                border_style="blue",
            )
        )

        self.session_id = self.session_manager.create_session()

        while True:
            try:
                # Get user input
                query = console.input("\n[bold green]Query>[/bold green] ")

                if query.lower() in ["exit", "quit", "q"]:
                    break

                if query.strip() == "":
                    continue

                # Process query with progress indicator
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Processing query...", total=None)

                    response = await self.response_generator.generate_response(
                        query, session_id=self.session_id
                    )

                    progress.update(task, completed=True)

                # Display response
                console.print("\n[bold cyan]Response:[/bold cyan]")
                console.print(Markdown(response.answer))

                # Display additional metadata if available
                if response.metadata:
                    self._display_metadata(response.metadata)

            except KeyboardInterrupt:
                console.print("\n[yellow]Session interrupted[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")

        console.print("\n[blue]Thank you for using Report Portal LLM Query Interface![/blue]")
        if self.session_id:
            self.session_manager.close_session(self.session_id)

    def _display_metadata(self, metadata: dict):
        """Display query metadata in a formatted table."""
        if "statistics" in metadata:
            stats = metadata["statistics"]
            table = Table(title="Query Statistics", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            for key, value in stats.items():
                table.add_row(key.replace("_", " ").title(), str(value))

            console.print(table)

    async def single_query(self, query: str):
        """Execute a single query and return."""
        try:
            response = await self.response_generator.generate_response(query)
            console.print(Markdown(response.answer))
            return response
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            raise


@click.group()
def cli():
    """Report Portal LLM Query Interface CLI."""
    pass


@cli.command()
@click.option("--config", "-c", default="config/config.yaml", help="Path to configuration file")
def interactive(config):
    """Start interactive query session."""
    try:
        interface = CLIInterface(config)
        asyncio.run(interface.start_interactive_session())
    except Exception as e:
        console.print(f"[red]Failed to initialize interface: {str(e)}[/red]")
        console.print(f"[yellow]Please check your configuration file: {config}[/yellow]")


@cli.command()
@click.argument("query")
@click.option("--config", "-c", default="config/config.yaml", help="Path to configuration file")
def query(query, config):
    """Execute a single query."""
    try:
        interface = CLIInterface(config)
        asyncio.run(interface.single_query(query))
    except Exception as e:
        console.print(f"[red]Failed to execute query: {str(e)}[/red]")
        console.print(f"[yellow]Please check your configuration file: {config}[/yellow]")


if __name__ == "__main__":
    cli()
