#!/usr/bin/env python3
"""
PDF Autofiller CLI

Command-line interface for PDF Autofiller operations.

Usage:
    pdf-autofiller extract <pdf_path> [--output OUTPUT]
    pdf-autofiller map <pdf_path> <input_json> [--mapper-type TYPE]
    pdf-autofiller embed <pdf_path> <mapping_json>
    pdf-autofiller fill <embedded_pdf> <input_json> [--output OUTPUT]
    pdf-autofiller make-embed <pdf_path> [--use-rag] [--output OUTPUT]
    pdf-autofiller run-all <pdf_path> <input_json> [--output OUTPUT]
    pdf-autofiller check-embed <pdf_path>
    
Examples:
    # Extract fields from PDF
    pdf-autofiller extract input.pdf --output extracted.json
    
    # Create embedded PDF (extract + map + embed)
    pdf-autofiller make-embed input.pdf --use-rag --output embedded.pdf
    
    # Fill embedded PDF with data
    pdf-autofiller fill embedded.pdf data.json --output filled.pdf
    
    # Complete pipeline
    pdf-autofiller run-all input.pdf data.json --output filled.pdf
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint


console = Console()


class CLIClient:
    """CLI client for PDF Autofiller API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize CLI client.
        
        Args:
            base_url: API base URL
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers["X-API-Key"] = api_key
        self.session.headers["Content-Type"] = "application/json"
    
    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make API request."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]API Error:[/red] {e}")
            sys.exit(1)


def format_result(result: Dict[str, Any], operation: str) -> None:
    """Format and display API result."""
    
    # Status indicator
    status = result.get("status", "unknown")
    status_emoji = "✅" if status == "success" else "❌"
    
    # Header panel
    console.print(Panel(
        f"{status_emoji} {operation.upper()} - {status.upper()}",
        style="bold green" if status == "success" else "bold red"
    ))
    
    # Execution time
    exec_time = result.get("execution_time_seconds", result.get("timing", {}).get("total_pipeline_seconds"))
    if exec_time:
        console.print(f"⏱️  Execution time: {exec_time:.2f}s")
    
    # Cache hit
    if "cache_hit" in result:
        cache_status = "🎯 CACHE HIT" if result["cache_hit"] else "🔄 CACHE MISS"
        console.print(cache_status)
    
    # PDF hash
    if "pdf_hash" in result:
        console.print(f"🔑 PDF Hash: {result['pdf_hash'][:16]}...")
    
    # Dual mapper info
    if "dual_mapper_info" in result:
        info = result["dual_mapper_info"]
        console.print(f"\n📊 Mapper: {info.get('mapper_used', 'N/A')}")
        if info.get("rag_api_failed"):
            console.print(f"[yellow]⚠️  RAG API: {info.get('rag_failure_reason')}[/yellow]")
    
    # Outputs
    if "outputs" in result:
        console.print("\n📤 Outputs:")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("File Type", style="dim")
        table.add_column("Path")
        
        outputs = result["outputs"]
        for key, value in outputs.items():
            if value and isinstance(value, str):
                # Truncate long paths
                display_path = value if len(value) < 80 else f"...{value[-77:]}"
                table.add_row(key.replace("_", " ").title(), display_path)
        
        console.print(table)
    
    # Output file (for simple operations)
    elif "output_file" in result:
        console.print(f"\n📤 Output: {result['output_file']}")
    
    # Analysis (for form fields)
    if "analysis" in result:
        analysis = result["analysis"]
        console.print("\n📊 Analysis:")
        console.print(f"   Total fields: {analysis.get('total_fields', 0)}")
        console.print(f"   Total headers: {analysis.get('total_headers', 0)}")
        console.print(f"   Total pages: {analysis.get('total_pages', 0)}")


def cmd_extract(args: argparse.Namespace, client: CLIClient) -> None:
    """Extract fields from PDF."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task("Extracting PDF fields...", total=None)
        
        result = client.request(
            "POST",
            "/mapper/extract",
            json={
                "pdf_path": str(args.pdf_path),
                "session_id": args.session_id
            }
        )
    
    format_result(result, "extract")
    
    # Save output if requested
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(result, indent=2))
        console.print(f"\n💾 Saved to: {output_path}")


def cmd_map(args: argparse.Namespace, client: CLIClient) -> None:
    """Map fields to target schema."""
    
    # Load input JSON
    input_json_path = Path(args.input_json)
    if not input_json_path.exists():
        console.print(f"[red]Error:[/red] Input JSON not found: {input_json_path}")
        sys.exit(1)
    
    with input_json_path.open() as f:
        input_data = json.load(f)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task("Mapping fields...", total=None)
        
        result = client.request(
            "POST",
            "/mapper/map",
            json={
                "pdf_path": str(args.pdf_path),
                "input_json": input_data,
                "mapper_type": args.mapper_type,
                "session_id": args.session_id
            }
        )
    
    format_result(result, "map")
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(result, indent=2))
        console.print(f"\n💾 Saved to: {output_path}")


def cmd_embed(args: argparse.Namespace, client: CLIClient) -> None:
    """Embed metadata into PDF."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task("Embedding metadata...", total=None)
        
        result = client.request(
            "POST",
            "/mapper/embed",
            json={
                "pdf_path": str(args.pdf_path),
                "mapping_json": str(args.mapping_json),
                "session_id": args.session_id
            }
        )
    
    format_result(result, "embed")


def cmd_fill(args: argparse.Namespace, client: CLIClient) -> None:
    """Fill PDF with data."""
    
    # Load input JSON
    input_json_path = Path(args.input_json)
    if not input_json_path.exists():
        console.print(f"[red]Error:[/red] Input JSON not found: {input_json_path}")
        sys.exit(1)
    
    with input_json_path.open() as f:
        input_data = json.load(f)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task("Filling PDF...", total=None)
        
        result = client.request(
            "POST",
            "/mapper/fill",
            json={
                "embedded_pdf": str(args.embedded_pdf),
                "input_json": input_data,
                "session_id": args.session_id
            }
        )
    
    format_result(result, "fill")
    
    if args.output:
        output_path = Path(args.output)
        # In a real scenario, you'd download the filled PDF
        console.print(f"\n📥 Download filled PDF from: {result.get('outputs', {}).get('filled_pdf', 'N/A')}")


def cmd_make_embed(args: argparse.Namespace, client: CLIClient) -> None:
    """Create embedded PDF (extract + map + embed)."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing pipeline...", total=None)
        
        result = client.request(
            "POST",
            "/mapper/make-embed-file",
            json={
                "pdf_path": str(args.pdf_path),
                "use_second_mapper": args.use_rag,
                "session_id": args.session_id
            },
            timeout=300
        )
        
        progress.update(task, completed=True)
    
    format_result(result, "make-embed-file")


def cmd_run_all(args: argparse.Namespace, client: CLIClient) -> None:
    """Run complete pipeline (extract + map + embed + fill)."""
    
    # Load input JSON
    input_json_path = Path(args.input_json)
    if not input_json_path.exists():
        console.print(f"[red]Error:[/red] Input JSON not found: {input_json_path}")
        sys.exit(1)
    
    with input_json_path.open() as f:
        input_data = json.load(f)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running complete pipeline...", total=None)
        
        result = client.request(
            "POST",
            "/mapper/run-all",
            json={
                "pdf_path": str(args.pdf_path),
                "input_json": input_data,
                "session_id": args.session_id
            },
            timeout=600
        )
        
        progress.update(task, completed=True)
    
    format_result(result, "run-all")


def cmd_check_embed(args: argparse.Namespace, client: CLIClient) -> None:
    """Check if PDF has embedded metadata."""
    
    result = client.request(
        "POST",
        "/mapper/check-embed-file",
        json={
            "pdf_path": str(args.pdf_path)
        }
    )
    
    exists = result.get("exists", False)
    
    if exists:
        console.print("✅ [green]Embedded PDF found[/green]")
        console.print(f"   Path: {result.get('embedded_pdf_path', 'N/A')}")
    else:
        console.print("❌ [red]Embedded PDF not found[/red]")
        console.print("   Run 'make-embed' first to create an embedded PDF")


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description="PDF Autofiller CLI - Extract, map, embed, and fill PDF forms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Global options
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication"
    )
    parser.add_argument(
        "--session-id",
        help="Session ID for tracking"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract command
    parser_extract = subparsers.add_parser("extract", help="Extract fields from PDF")
    parser_extract.add_argument("pdf_path", help="Path to PDF file")
    parser_extract.add_argument("-o", "--output", help="Output JSON file")
    
    # Map command
    parser_map = subparsers.add_parser("map", help="Map fields to target schema")
    parser_map.add_argument("pdf_path", help="Path to PDF file")
    parser_map.add_argument("input_json", help="Input JSON with data")
    parser_map.add_argument(
        "--mapper-type",
        choices=["semantic", "rag", "headers", "ensemble"],
        default="ensemble",
        help="Mapper type to use (default: ensemble)"
    )
    parser_map.add_argument("-o", "--output", help="Output JSON file")
    
    # Embed command
    parser_embed = subparsers.add_parser("embed", help="Embed metadata into PDF")
    parser_embed.add_argument("pdf_path", help="Path to PDF file")
    parser_embed.add_argument("mapping_json", help="Mapping JSON file")
    
    # Fill command
    parser_fill = subparsers.add_parser("fill", help="Fill PDF with data")
    parser_fill.add_argument("embedded_pdf", help="Path to embedded PDF")
    parser_fill.add_argument("input_json", help="Input JSON with data")
    parser_fill.add_argument("-o", "--output", help="Output PDF file")
    
    # Make embed command
    parser_make = subparsers.add_parser(
        "make-embed",
        help="Create embedded PDF (extract + map + embed)"
    )
    parser_make.add_argument("pdf_path", help="Path to PDF file")
    parser_make.add_argument(
        "--use-rag",
        action="store_true",
        help="Use dual mapper with RAG predictions"
    )
    parser_make.add_argument("-o", "--output", help="Output embedded PDF")
    
    # Run all command
    parser_all = subparsers.add_parser(
        "run-all",
        help="Run complete pipeline (extract + map + embed + fill)"
    )
    parser_all.add_argument("pdf_path", help="Path to PDF file")
    parser_all.add_argument("input_json", help="Input JSON with data")
    parser_all.add_argument("-o", "--output", help="Output filled PDF")
    
    # Check embed command
    parser_check = subparsers.add_parser(
        "check-embed",
        help="Check if PDF has embedded metadata"
    )
    parser_check.add_argument("pdf_path", help="Path to PDF file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Create client
    client = CLIClient(base_url=args.api_url, api_key=args.api_key)
    
    # Route to command handlers
    commands = {
        "extract": cmd_extract,
        "map": cmd_map,
        "embed": cmd_embed,
        "fill": cmd_fill,
        "make-embed": cmd_make_embed,
        "run-all": cmd_run_all,
        "check-embed": cmd_check_embed,
    }
    
    handler = commands.get(args.command)
    if handler:
        try:
            handler(args, client)
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled by user[/yellow]")
            sys.exit(130)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
