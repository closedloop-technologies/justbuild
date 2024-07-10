import typer
import typer
from justbuild import (
    __version__ as version,
    __description__ as short_description,
    lfg_cli,
)
from justbuild.config import load_config
from justbuild.ui import show_full_banner

config = load_config()
app = typer.Typer(name="justbuild", help="💬 Chat Assisted Programming 💻")

app.add_typer(
    lfg_cli.app, name="lfg", short_help="Merge LLM-generated code into your repo"
)


@app.callback(invoke_without_command=True)
def banner(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        show_full_banner("justbuild")
