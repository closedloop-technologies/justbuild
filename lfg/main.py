import tempfile
from pathlib import Path

import pyperclip
import typer

from lfg.codediff.merging import merge_all, merge as merge_files
from lfg.config import load_config

config = load_config()
app = typer.Typer(name="lfg", help="LFG! 🚀 Chat Assisted Programming Tools")


@app.command()
def paste(file_path: str = typer.Argument(...)):
    """
    Paste new code from clipboard into the specified file, preserving existing code where indicated.
    """
    file_path = Path(file_path)
    file_type_suffix = str(file_path).split(".")[-1]

    tempfilename = Path(tempfile.mkstemp(prefix="lfg-", suffix=file_type_suffix)[1])
    new_code = pyperclip.paste()
    if not new_code:
        typer.echo("No code found in clipboard")
        raise typer.Exit()
    with open(tempfilename, "w") as file:
        file.write(new_code)

    if not file_path.exists():
        file_path.mkdir(parents=True, exist_ok=True)
        Path(file_path).touch()

    updates = merge_files(
        old_file=file_path, new_file=tempfilename, target_file=file_path
    )
    typer.echo(f"Code pasted and merged into {file_path} with updates:\n{updates}")


@app.command()
def merge(
    updated_file: str = typer.Argument(..., help="Path to the modified file"),
    old_file: str = typer.Option(..., help="Path to the original file"),
    target_file: str = typer.Option(
        ..., help="Path to the output file, defaults to `new_file`"
    ),
    auto_resolve: bool = typer.Option(
        False, "--auto-resolve", "-a", help="Automatically resolve conflicts using LLM"
    ),
):
    """
    Merge changes from new_file into old_file, or merge changes in the entire repo if no files are specified.
    """
    if not old_file and not updated_file and not target_file:
        typer.echo("No files specified to merge")
        merge_all()
        raise typer.Exit()

    old_file = Path(old_file) if old_file else None
    updated_file = Path(updated_file)
    target_file = Path(target_file) if target_file else updated_file

    updates = merge_files(
        old_file=old_file, new_file=updated_file, target_file=target_file
    )
    typer.echo(
        f"LFG 🚀! {len(updates.get('change_log',[]))} Code Omissions Corrected: {target_file}"
    )


# Entry point for the CLI is the `app` object loaded from __main__.py
@app.callback(invoke_without_command=True)
def banner():
    typer.echo("Welcome to LFG! 🚀")
