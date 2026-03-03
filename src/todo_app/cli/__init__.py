import typer

from todo_app.cli import roles

app = typer.Typer(help="Lakebase CLI for managing database roles and permissions.")
app.add_typer(roles.app, name="roles")
