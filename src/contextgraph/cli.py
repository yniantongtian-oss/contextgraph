import typer
 from rich.console import Console
 from rich.table import Table
 from pathlib import Path
 from .core import CodeContextGraph

 app = typer.Typer(help="ContextGraph - Intelligent code graphs for AI coding workflows")
 console = Console()


 @app.command()
 def scan(
     project: str = typer.Argument(..., help="Path to the project directory"),
     output: str = typer.Option(None, "--output", "-o", help="Save graph to JSON file")
 ):
     """Scan a project and build the code graph."""
     cg = CodeContextGraph()
     cg.load_project(project)
     cg.build_graph()
     stats = cg.get_graph_stats()
     console.print(f"[bold green]Scan complete![/]")
     console.print(f"Nodes: {stats['nodes']}, Edges: {stats['edges']}")
 
     if output:
         import json
         with open(output, "w") as f:
             json.dump({"stats": stats}, f, indent=2)
         console.print(f"Graph stats saved to {output}")
 

 @app.command()
 def query(
     query_text: str = typer.Argument(..., help="What to search for in the code"),
     project: str = typer.Option(".", "--project", "-p", help="Project path"),
     budget: int = typer.Option(2000, "--budget", help="Max tokens budget"),
 ):
     """Query the code graph for relevant context."""
     cg = CodeContextGraph()
     cg.load_project(project)
     cg.build_graph()
     results = cg.query_context(query_text, max_tokens=budget)
 
     console.print(f"[bold]Query:[/] {query_text}")
     console.print(f"[bold]Estimated tokens:[/] {results['estimated_tokens']}")
     console.print("\n[bold green]Relevant Context:[/]\n")
     console.print(results["context"][:2000] if results["context"] else "No relevant code found.")
 
     if results.get("graph_summary"):
         console.print(f"\n[dim]{results['graph_summary']}[/]")
 

 @app.command()
 def prompt(
     task: str = typer.Argument(..., help="The coding task or question"),
     project: str = typer.Option(".", "--project", "-p"),
     max_tokens: int = typer.Option(1500, "--max-tokens", help="Token budget for context")
 ):
     """Generate an optimized prompt with relevant context for an LLM."""
     cg = CodeContextGraph()
     cg.load_project(project)
     cg.build_graph()
     results = cg.query_context(task, max_tokens=max_tokens)
 
     optimized_prompt = f"""You are an expert software engineer.

Task: {task}

Relevant code context:
{results['context']}

Please provide a high-quality implementation or answer."""
 
     console.print("[bold green]Optimized prompt ready to copy:[/]\n")
     console.print(optimized_prompt)
