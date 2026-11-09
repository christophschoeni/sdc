"""Zentrale UI- und Styling-Bibliothek für die SCHOENI DIGITAL CLI (`sdc`)."""
from __future__ import annotations

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

# Questionary Theme im einheitlichen CI-Design
QUESTIONARY_STYLE = questionary.Style([
    ("qmark", "fg:#00d2ff bold"),
    ("question", "bold fg:#f8fafc"),
    ("answer", "fg:#10b981 bold"),
    ("pointer", "fg:#00d2ff bold"),
    ("highlighted", "fg:#00d2ff bold"),
    ("selected", "fg:#10b981 bold"),
    ("separator", "fg:#64748b"),
    ("instruction", "fg:#64748b italic"),
    ("text", "fg:#f8fafc"),
    ("disabled", "fg:#475569 italic"),
])


def clear() -> None:
    if sys.stdout.isatty():
        console.clear()


def banner(user_info: str | None = None, device_info: str | None = None) -> None:
    """Zeigt das elegante Kopf-Banner mit aktuellen Kontext-Informationen."""
    header = Text()
    header.append("◆ SCHOENI DIGITAL ", style="bold cyan")
    header.append("· ", style="dim")
    header.append("Developer & Admin CLI ", style="bold white")
    header.append(f"v{__version__}", style="dim cyan")

    sub_parts = []
    if user_info:
        sub_parts.append(f"[cyan]👤 {user_info}[/cyan]")
    if device_info:
        sub_parts.append(f"[green]💻 {device_info}[/green]")
    sub_parts.append("[dim]🔒 SOPS+age[/dim]")

    content = Text.from_markup("  " + "  ·  ".join(sub_parts)) if sub_parts else Text()

    grid = Table.grid(padding=(0, 1))
    grid.add_column()
    grid.add_row(header)
    if sub_parts:
        grid.add_row(content)

    console.print(
        Panel(
            grid,
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 2),
        )
    )


def success(msg: str) -> None:
    console.print(f"[bold green]✔[/bold green] {msg}")


def info(msg: str) -> None:
    console.print(f"[bold cyan]ℹ[/bold cyan] {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold yellow]▲[/bold yellow] [yellow]{msg}[/yellow]")


def error(msg: str) -> None:
    console.print(f"[bold red]✖[/bold red] [red]{msg}[/red]")


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


def pause(message: str = "Enter drücken um fortzufahren …") -> None:
    questionary.press_any_key_to_continue(message=message, style=QUESTIONARY_STYLE).ask()
