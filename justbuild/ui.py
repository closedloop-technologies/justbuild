import tempfile
from pathlib import Path
import typer
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import pyperclip
import typer
from justbuild import (
    __version__ as version,
    __description__ as short_description,
)


def display_banner(command: str = "justbuild"):
    """Pagga font from figlet."""
    banner = f"""[bold yellow]
  ░▀▀█░█░█░█▀▀░▀█▀  ░█▀▄░█░█░▀█▀░█░░░█▀▄
  ░░░█░█░█░▀▀█░░█░  ░█▀▄░█░█░░█░░█░░░█░█
  ░▀▀░░▀▀▀░▀▀▀░░▀░  ░▀▀░░▀▀▀░▀▀▀░▀▀▀░▀▀░
[/bold yellow]
🚀 [bold red]{command:9}[/bold red] Chat Assisted Programming 💬"""
    rprint(Panel(banner, border_style="bold green", expand=False))


def display_info():
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Description", short_description)
    table.add_row("Version", version)
    table.add_row("Author", "Sean Kruzel @ ClosedLoop.Tech")
    table.add_row("License", "MIT")

    rprint(table)


def display_commands():
    commands = [
        ("lfg", "Merge LLM-generated code into your repo"),
    ]

    table = Table(title="All Available Commands from JustBuild.ai", box=None)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    rprint(table)


def show_full_banner(command, show_commands=True):
    display_banner(command)
    display_info()
    if show_commands:
        rprint("")
        display_commands()
    rprint(
        f"\n[bold blue]Type '{command} --help' for more information on a specific command.[/bold blue]"
    )
