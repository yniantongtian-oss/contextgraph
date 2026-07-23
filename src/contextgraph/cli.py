from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .core import CodeContextGraph

app = typer.Typer(
    help="ContextGraph - focused code context for AI coding workflows",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _load_graph(project: Path) -> CodeContextGraph:
    graph = CodeContextGraph(console=console)
    try:
        graph.load_project(project)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise typer.BadParameter(str(exc), param_hint="project") from exc
    graph.build_graph()
    return graph


@app.command()
def scan(
    project: Path = typer.Argument(..., help="Project directory to scan"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write scan statistics to a JSON file",
    ),
) -> None:
    """Scan a project and print graph statistics."""
    graph = _load_graph(project)
    stats = graph.get_graph_stats()

    table = Table(title="ContextGraph scan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, value in stats.items():
        table.add_row(str(key), json.dumps(value) if isinstance(value, dict) else str(value))
    console.print(table)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(stats, indent=2), encoding="utf-8")
        console.print(f"Statistics written to {output}")


@app.command()
def query(
    query_text: str = typer.Argument(..., help="Question or code concept to retrieve"),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root"),
    budget: int = typer.Option(2_000, "--budget", min=1, help="Approximate token budget"),
    semantic: bool = typer.Option(
        False,
        "--semantic/--no-semantic",
        help="Enable optional local semantic search",
    ),
) -> None:
    """Retrieve relevant source context."""
    graph = _load_graph(project)
    if semantic and not graph.enable_semantic_search():
        raise typer.Exit(code=2)

    result = graph.query_context(
        query_text,
        max_tokens=budget,
        use_semantic=semantic,
    )
    console.print(f"[bold cyan]Query:[/] {query_text}")
    console.print(f"[bold]Estimated tokens:[/] {result['estimated_tokens']}")
    console.print(f"[bold]Scored candidates:[/] {result['total_candidates']}")
    if result.get("graph_summary"):
        console.print(f"[dim]{result['graph_summary']}[/]")
    console.print("\n[bold green]Relevant context[/]\n")
    console.print(result.get("context") or "No relevant code found.", markup=False)


@app.command()
def prompt(
    task: str = typer.Argument(..., help="Coding task or question"),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root"),
    max_tokens: int = typer.Option(
        1_500,
        "--max-tokens",
        min=1,
        help="Approximate token budget for source context",
    ),
    semantic: bool = typer.Option(False, "--semantic/--no-semantic"),
) -> None:
    """Create a reusable prompt containing retrieved code context."""
    graph = _load_graph(project)
    if semantic and not graph.enable_semantic_search():
        raise typer.Exit(code=2)

    result = graph.query_context(task, max_tokens=max_tokens, use_semantic=semantic)
    optimized = f"""You are an expert software engineer working in the supplied codebase.

## Task
{task}

## Retrieved code context
{result.get('context', '')}

## Requirements
- Ground the answer in the retrieved code.
- State assumptions when context is incomplete.
- Preserve existing public APIs unless the task explicitly requires a breaking change.
- Include focused tests for behavior that changes.
"""
    console.print(optimized, markup=False)


if __name__ == "__main__":  # pragma: no cover
    app()
