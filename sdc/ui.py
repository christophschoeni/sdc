"""Zentrale UI- und Styling-Bibliothek für die SCHOENI DIGITAL CLI (`sdc`).

Vollständig ohne Emojis — klares, minimalistisches Schweizer Ingenieursdesign.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Any, Generator, Sequence
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
import questionary

from . import __version__

# Haupt-Konsole mit UTF-8 & Farb-Unterstützung
console = Console(highlight=False)

# Questionary Theme im professionellen Design ohne Emojis
QUESTIONARY_STYLE = questionary.Style([
    ("qmark", "fg:#00d2ff bold"),
    ("question", "bold fg:#f8fafc"),
    ("answer", "fg:#10b981 bold"),
    ("pointer", "fg:#00d2ff bold"),
    ("highlighted", "fg:#00e5ff bold"),
    ("selected", "fg:#10b981 bold"),
    ("separator", "fg:#475569 bold"),
    ("instruction", "fg:#64748b italic"),
    ("text", "fg:#f8fafc"),
    ("disabled", "fg:#475569 italic"),
    ("cmd", "fg:#00d2ff bold"),
    ("dim", "fg:#64748b"),
    ("desc", "fg:#f8fafc"),
])

LOGO_LINES = [
    "   ____ _____ _   _  ___  _   _ ___    ____ ___ ____ ___ _____ _   _     ",
    "  / ___/ ____| | | |/ _ \\| \\ | |_ _|  |  _ \\_ _/ ___|_ _|_   _/ \\ | |    ",
    "  \\___ \\ |   | |_| | | | |  \\| || |   | | | | | |  _ | |  | |/ _ \\| |    ",
    "   ___) | |__|  _  | |_| | |\\  || |   | |_| | | |_| || |  | / ___ \\ |___ ",
    "  |____/ \\_____| |_|\\___/|_| \\_|___|  |____/___\\____|___| |_/_/   \\_\\_____|",
]


def clear() -> None:
    if sys.stdout.isatty():
        console.clear()


def banner(user_info: str | None = None, device_info: str | None = None) -> None:
    """Zeigt das offizielle SCHOENI DIGITAL ASCII-Logo mit aktuellen Statuszeilen."""
    console.print()
    width = console.width

    if width >= 78:
        # Volles ASCII-Art Logo
        for line in LOGO_LINES:
            console.print(f"[bold cyan]{line}[/bold cyan]")
    else:
        console.print("[bold cyan]SCHOENI DIGITAL[/bold cyan] [dim]· Developer & Admin CLI[/dim]")

    console.print(f"[dim]SCHÖNI DIGITAL · Entwickler- & Administrations-Zentrale · v{__version__}[/dim]")

    # Sub-Zeile mit aktuellem Kontext
    meta_parts = []
    if user_info:
        meta_parts.append(f"[white]Benutzer:[/white] [cyan]{user_info}[/cyan]")
    if device_info:
        meta_parts.append(f"[white]Gerät:[/white] [dim]{device_info}[/dim]")
    meta_parts.append("[dim]Secrets: SOPS+age[/dim]")

    console.print(" · ".join(meta_parts))
    console.print("[dim]" + "─" * min(width, 78) + "[/dim]\n")


def success(msg: str) -> None:
    console.print(f"[bold green]\\[ok][/bold green] {msg}")


def info(msg: str) -> None:
    console.print(f"[bold cyan]\\[info][/bold cyan] {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold yellow]\\[warn][/bold yellow] [yellow]{msg}[/yellow]")


def error(msg: str) -> None:
    console.print(f"[bold red]\\[fehlt][/bold red] [red]{msg}[/red]")


def step(label: str, current: int | None = None, total: int | None = None) -> None:
    prefix = f"[bold cyan][{current}/{total}][/bold cyan] " if current and total else "[bold cyan]›[/bold cyan] "
    console.print(f"\n{prefix}[bold white]{label}[/bold white]")


def panel(title: str, text: str | list[str], style: str = "cyan") -> None:
    body = "\n".join(text) if isinstance(text, list) else text
    console.print(
        Panel(
            body,
            title=f"[bold]{title}[/bold]",
            title_align="left",
            box=box.ROUNDED,
            border_style=style,
            padding=(1, 2),
        )
    )


def table(title: str, columns: Sequence[str | tuple[str, dict]], rows: Sequence[Sequence[Any]]) -> None:
    tbl = Table(
        title=f"[bold white]{title}[/bold white]",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="dim",
        title_style="bold cyan",
        padding=(0, 1),
    )
    for col in columns:
        if isinstance(col, tuple):
            name, kw = col
            tbl.add_column(name, **kw)
        else:
            tbl.add_column(str(col))

    for r in rows:
        tbl.add_row(*[str(c) for c in r])

    console.print(tbl)


@contextmanager
def spinner(text: str) -> Generator[None, None, None]:
    """Kontextmanager für Lade-Animation."""
    with console.status(f"[cyan]{text}[/cyan]", spinner="dots"):
        yield


def select(message: str, choices: list[Any], default: Any = None, instruction: str = "(Pfeiltasten, Enter zum Bestätigen)") -> Any:
    return questionary.select(
        message,
        choices=choices,
        default=default,
        style=QUESTIONARY_STYLE,
        instruction=instruction,
    ).ask()


def text(message: str, default: str = "", validate: Any = None) -> str:
    kw = {"validate": validate} if validate else {}
    return questionary.text(message, default=default, style=QUESTIONARY_STYLE, **kw).ask() or ""


def confirm(message: str, default: bool = True) -> bool:
    res = questionary.confirm(message, default=default, style=QUESTIONARY_STYLE).ask()
    return bool(res)


def pause(message: str = "Enter drücken um fortzufahren ...") -> None:
    questionary.press_any_key_to_continue(message=message, style=QUESTIONARY_STYLE).ask()


def choice_item(cmd: str, desc: str, value: Any, pad: int = 10) -> questionary.Choice:
    """Erzeugt eine formatierte Menü-Option: Variable/Befehl in Signalfarbe gefolgt vom Text."""
    return questionary.Choice(
        title=[
            ("class:cmd", cmd.ljust(pad)),
            ("class:dim", "›  "),
            ("class:desc", desc),
        ],
        value=value,
    )
