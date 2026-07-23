import typer
 from rich.console import Console
 from rich.table import Table
 from pathlib import Path
 from .core import CodeContextGraph

 app = typer.Typer(
     help="ContextGraph - Intelligent code graphs for AI coding workflows",
     add_completion=False
 )
 console = Console()


 @app.command()
 def scan(
     project: str = typer.Argument(..., help="Path to the project directory"),
     output: str = typer.Option(None, "--output", "-o", help="Save stats to JSON")
 ):
     """Scan project and build code graph."""
     cg = CodeContextGraph()
     cg.load_project(project)
     cg.build_graph()
     stats = cg.get_graph_stats()
 
     table = Table(title="Scan Results")
     table.add_column("Metric", style="cyan")
     table.add_column("Value", style="green")
     for k, v in stats.items():
         table.add_row(str(k), str(v))
     console.print(table)
 
     if output:
         import json
         with open(output, "w") as f:
             json.dump(stats, f, indent=2)
         console.print(f"Stats saved to {output}")
 

 @app.command()
 def query(
     query_text: str = typer.Argument(..., help="Search query for code context"),
     project: str = typer.Option(".", "--project", "-p", help="Project root path"),
     budget: int = typer.Option(2000, "--budget", help="Max token budget"),
     semantic: bool = typer.Option(True, "--semantic/--no-semantic", help="Use semantic search if available")
 ):
     """Query relevant code context."""
     cg = CodeContextGraph()
     cg.load_project(project)
     cg.build_graph()
 
     if semantic:
         cg.enable_semantic_search()
 
     results = cg.query_context(query_text, max_tokens=budget, use_semantic=semantic)
 
     console.print(f"[bold cyan]Query:[/] {query_text}")
     console.print(f"[bold]Estimated tokens used:[/] {results.get('estimated_tokens', 0)}")
     console.print(f"[bold]Candidates found:[/] {results.get('total_candidates', 0)}")
 
     if results.get("graph_summary"):
         console.print(f"[dim]{results['graph_summary']}[/]")
 
     console.print("\n[bold green]Relevant Context:[/]\n")
     console.print(results.get("context", "No relevant code found.")[:3000])
 

 @app.command()
 def prompt(
     task: str = typer.Argument(..., help="Coding task or question for the LLM"),
     project: str = typer.Option(".", "--project", "-p"),
     max_tokens: int = typer.Option(1500, "--max-tokens"),
     semantic: bool = typer.Option(True, "--semantic/--no-semantic")
 ):
     """Generate an optimized prompt with relevant context."""
     cg = CodeContextGraph()
     cg.load_project(project)
     cg.build_graph()
 
     if semantic:
         cg.enable_semantic_search()
 
     results = cg.query_context(task, max_tokens=max_tokens, use_semantic=semantic)
 
     optimized = f"""You are an expert software engineer with deep understanding of the provided codebase.

## Task
{task}

## Relevant Code Context
{results.get('context', '')}

## Instructions
Provide a high-quality, production-ready solution. Explain key decisions.
"""
 
     console.print("[bold green]Optimized prompt (copy to your LLM):[/]\n")
     console.print(optimized)
