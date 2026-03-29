"""Click-based CLI entry point for Bookworm."""

import sys
from typing import List, Optional

import click

from . import __version__
from .client import CalibreClient
from .config import load_servers
from .download import download_book, download_books
from .search import search_books, display_results, format_result


def get_client(server: Optional[str], library: str, debug: bool = False) -> CalibreClient:
    """
    Get a CalibreClient instance.
    
    If server is not provided, try servers from config file until one responds.
    """
    if server:
        return CalibreClient(server, library, debug)
    
    # Try servers from config
    servers = load_servers()
    
    if not servers:
        raise RuntimeError("No servers configured. Use --server or add servers to ~/.bookworm/servers")
    
    click.echo("Trying configured servers...")
    
    for server_url in servers:
        try:
            client = CalibreClient(server_url, library)
            # Test connection with a simple request
            client.get_books_init("test")
            click.echo(f"Connected to {server_url}")
            return client
        except Exception as e:
            click.echo(f"Failed to connect to {server_url}: {e}")
            continue
    
    raise RuntimeError("All configured servers failed to respond")


@click.group()
@click.version_option(version=__version__)
def cli():
    """Bookworm - A minimalist CLI utility for searching and downloading ebooks from Calibre content servers."""
    pass


@cli.command()
@click.option("--query", "-q", required=True, help="Search string (title, author, tags)")
@click.option("--server", "-s", help="Calibre server URL")
@click.option("--library", "-l", default="books", help="Library ID (default: books)")
@click.option("--format", "-f", "format_filter", help="Filter by format (epub, pdf, mobi, etc.)")
@click.option("--sort", "-S", type=click.Choice(["timestamp", "title", "author", "size", "rating", "pubdate", "pages"]), help="Sort field")
@click.option("--order", "-O", type=click.Choice(["asc", "desc"]), default="desc", help="Sort order")
@click.option("--limit", "-n", default=50, help="Max results to display (default: 50)")
@click.option("--all", "fetch_all", is_flag=True, help="Fetch ALL results by iterating through all pages")
@click.option("--debug", is_flag=True, help="Enable verbose HTTP debugging")
def search(query: str, server: Optional[str], library: str, format_filter: Optional[str],
           sort: Optional[str], order: str, limit: int, fetch_all: bool, debug: bool):
    """Search for books on Calibre servers."""
    try:
        client = get_client(server, library, debug)
        
        books = search_books(
            client=client,
            query=query,
            limit=limit,
            fetch_all=fetch_all,
            sort=sort,
            order=order,
            format_filter=format_filter
        )
        
        # Format results for display
        formatted_books = {bid: format_result(str(bid), meta) for bid, meta in books.items()}
        
        # Display results
        display_results(formatted_books, limit)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("book_ids", nargs=-1, required=True)
@click.option("--server", "-s", help="Calibre server URL")
@click.option("--library", "-l", default="books", help="Library ID (default: books)")
@click.option("--format", "-f", help="Format to download (auto-detect if not specified)")
@click.option("--output", "-o", help="Output path (directory or filename)")
@click.option("--debug", is_flag=True, help="Enable verbose HTTP debugging")
def download(book_ids: List[str], server: Optional[str], library: str,
             format: Optional[str], output: Optional[str], debug: bool):
    """Download books by ID."""
    try:
        client = get_client(server, library, debug)
        
        # Convert book_ids to integers
        book_id_list = [int(bid) for bid in book_ids]
        
        downloaded = []
        for book_id in book_id_list:
            path = download_book(client, book_id, output, format)
            downloaded.append(path)
        
        click.echo(f"\nDownloaded {len(downloaded)} book(s)")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """Manage server configuration."""
    pass


@config.command()
@click.argument("server_url")
def add(server_url: str):
    """Add a server URL to the config."""
    from .config import add_server
    add_server(server_url)
    click.echo(f"Added {server_url} to config")


@config.command()
@click.argument("server_url")
def remove(server_url: str):
    """Remove a server URL from the config."""
    from .config import remove_server
    remove_server(server_url)
    click.echo(f"Removed {server_url} from config")


@config.command()
def list():
    """List configured servers."""
    from .config import load_servers
    servers = load_servers()
    if servers:
        click.echo("Configured servers:")
        for server in servers:
            click.echo(f"  {server}")
    else:
        click.echo("No servers configured. Use 'bookworm config add <url>' to add servers.")


if __name__ == "__main__":
    cli()
