from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

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
    project: Annotated[Path, typer.Argument(help="Project directory to scan")],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write scan statistics to a JSON file",
        ),
    ] = None,
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
    query_text: Annotated[
        str,
        typer.Argument(help="Question or code concept to retrieve"),
    ],
    project: Annotated[
        Path,
        typer.Option("--project", "-p", help="Project root"),
    ] = Path("."),
    budget: Annotated[
        int,
        typer.Option("--budget", min=1, help="Approximate token budget"),
    ] = 2_000,
    semantic: Annotated[
        bool,
        typer.Option(
            "--semantic/--no-semantic",
            help="Enable optional local semantic search",
        ),
    ] = False,
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
def bundle(
    task: Annotated[str, typer.Argument(help="Development task or code concept")],
    project: Annotated[
        Path,
        typer.Option("--project", "-p", help="Project root"),
    ] = Path("."),
    max_tokens: Annotated[
        int,
        typer.Option(
            "--max-tokens",
            min=1,
            help="Approximate maximum source token budget",
        ),
    ] = 1_500,
    semantic: Annotated[
        bool,
        typer.Option("--semantic/--no-semantic"),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write the retrieved source bundle to JSON"),
    ] = None,
) -> None:
    """Export relevant source context and retrieval metadata as structured JSON."""
    graph = _load_graph(project)
    if semantic and not graph.enable_semantic_search():
        raise typer.Exit(code=2)

    result = graph.query_context(task, max_tokens=max_tokens, use_semantic=semantic)
    payload = {
        "task": task,
        "context": result.get("context", ""),
        "relevant_files": result.get("relevant_files", []),
        "estimated_tokens": result.get("estimated_tokens", 0),
        "total_candidates": result.get("total_candidates", 0),
    }
    document = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if output is None:
        console.print(document, markup=False, highlight=False, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document, encoding="utf-8")
        console.print(f"Source bundle written to {output}")


if __name__ == "__main__":  # pragma: no cover
    app()
