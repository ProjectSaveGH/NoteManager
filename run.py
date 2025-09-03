import os
import subprocess
import argparse
import importlib.util
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


# ----------------- Helper -----------------
def get_scripts(directory="."):
    return [f for f in os.listdir(directory) if f.endswith(".py")]


def get_flags(script_path):
    """
    Importiere das Skript dynamisch und lese argparse-Flags aus.
    """
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)  # pyright: ignore[type]
    try:
        spec.loader.exec_module(module)  # pyright: ignore[attribute]
    except SystemExit:
        # argparse ruft sys.exit() beim parse_args() auf
        pass
    parser = getattr(module, "parser", None)
    if parser:
        return [a.option_strings[0] for a in parser._actions if a.option_strings]
    return []


# ----------------- Main -----------------
console.print(Panel("🚀 Python Script Launcher", style="bold cyan"))

scripts = get_scripts()
if not scripts:
    console.print("[red]Keine Python-Skripte gefunden![/red]")
    exit()

# Skript auswählen
table = Table(title="Available Scripts")
table.add_column("Index", style="cyan")
table.add_column("Script", style="green")
for i, s in enumerate(scripts):
    table.add_row(str(i), s)
console.print(table)

idx = int(
    Prompt.ask("Select script by index", choices=[str(i) for i in range(len(scripts))])
)
script = scripts[idx]

# Flags auslesen
flags = get_flags(script)
selected_flags = []
if flags:
    console.print(f"Available flags for {script}:")
    for f in flags:
        if Confirm.ask(f"Enable flag {f}?"):
            selected_flags.append(f)

# Run script
cmd = ["python", script] + selected_flags
console.print(Panel(f"Running: {' '.join(cmd)}", style="magenta"))
subprocess.run(cmd)
