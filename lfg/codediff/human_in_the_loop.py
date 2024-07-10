from typing import Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


def _show_title(console):
    console.print(
        Panel(
            "[bold]Definition: Placeholder Comment[/bold]\n\n"
            "A placeholder comment is a descriptive note within the code that indicates "
            "a section of the code is intentionally omitted or remains unchanged, often "
            "represented by ellipsis or specific text.",
            title="Please Label these potential 'Placeholder Comments'",
            expand=False,
        )
    )


def labeling(
    samples: List[Dict],
    label="label",
    default_confidence=0.99,
    console: Optional[Console] = None,
) -> List[Dict]:
    """
    Allow the user to review and label code diffs for placeholder comments.
    """
    console = console or Console()
    labeled_inputs = []

    for index, input_dict in enumerate(samples, start=1):
        _show_title(console)
        console.print(f"\n[bold]Reviewing diff {index} of {len(samples)}[/bold]\n")

        # Display the diff using rich's Syntax highlighting
        diff_syntax = Syntax(
            input_dict["_diff"], "diff", theme="monokai", line_numbers=True
        )
        console.print(diff_syntax)

        # Ask the user for input
        contains_placeholder = typer.confirm(
            "Does this diff contain a Placeholder Comment to be reverted?",
            default=False,
        )

        # Add the user's label to the dictionary
        input_dict[label] = contains_placeholder
        input_dict["confidence"] = default_confidence
        labeled_inputs.append(input_dict)

        # Clear the screen for the next diff
        console.clear()

    return labeled_inputs


def print_changes(change_log: list[dict]):
    """
    Print the changes to the console.
    """
    console = Console()
    console.clear()

    console.print(
        Panel(
            "[bold]Placeholder Comments removed[/bold]\n\n",
            title="LFG Merge",
            expand=False,
        )
    )

    for i, change in enumerate(change_log):
        console.print(
            f"\n[bold]Approved diff to revert: {i+1} of {len(change_log)}[/bold]\n"
        )
        diff_syntax = Syntax(
            change["git_diff"], "diff", theme="monokai", line_numbers=True
        )
        console.print(diff_syntax)
        if i < len(change_log) - 1:
            typer.confirm(
                "Any key to continue:",
                default=False,
            )
