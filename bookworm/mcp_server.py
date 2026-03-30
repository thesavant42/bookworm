"""FastMCP server for Bookworm - Calibre ebook search and download service."""

from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from bookworm.client import CalibreClient
from bookworm import config
from bookworm.download import download_book
from bookworm.search import search_books as search_books_module, format_result

# Aliases for config functions
config_add_server = config.add_server
config_list_servers = config.load_servers
config_remove_server = config.remove_server


# Create the FastMCP server instance
mcp = FastMCP(
    name="Bookworm MCP Server",
    description="Search and download ebooks from Calibre content servers",
)


# =============================================================================
# TOOLS
# =============================================================================

@mcp.tool()
async def search_books(
    query: str,
    server: Optional[str] = None,
    library: str = "books",
    format_filter: Optional[str] = None,
    sort: Optional[str] = None,
    order: str = "desc",
    limit: int = 50,
    fetch_all: bool = False
) -> str:
    """
    Search for books on Calibre servers.
    
    Args:
        query: Search string (title, author, tags) - REQUIRED
        server: Calibre server URL (optional, uses configured servers if not provided)
        library: Library ID (default: "books")
        format_filter: Filter by format (epub, pdf, mobi, etc.)
        sort: Sort field (timestamp, title, author, size, rating, pubdate, pages)
        order: Sort order (asc, desc) - default: desc
        limit: Max results to display (default: 50)
        fetch_all: Fetch ALL results by iterating through all pages
    
    Returns:
        Formatted search results
    """
    try:
        # Get client
        if server:
            client = CalibreClient(server, library)
        else:
            servers = config.load_servers()
            if not servers:
                return "Error: No servers configured. Use add_server tool or configure ~/.bookworm/servers"
            
            client = None
            for server_url in servers:
                try:
                    client = CalibreClient(server_url, library)
                    client.get_books_init("test")
                    break
                except Exception:
                    continue
            
            if not client:
                return "Error: All configured servers failed to respond"
        
        # Search for books
        books = search_books_module(
            client=client,
            query=query,
            limit=limit,
            fetch_all=fetch_all,
            sort=sort,
            order=order,
            format_filter=format_filter
        )
        
        # Format results
        formatted_books = {bid: format_result(str(bid), meta) for bid, meta in books.items()}
        
        # Build result string
        result_lines = []
        result_lines.append(f"Found {len(formatted_books)} results:")
        result_lines.append("")
        
        for book in formatted_books.values():
            result_lines.append(
                f"ID: {book['id']} | Title: {book['title']} | Author: {book['author']} | "
                f"Format: {book['format']} | Size: {book['size']:.2f} MB"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"Error searching books: {str(e)}"


@mcp.tool()
async def download_books(
    book_ids: list,
    server: Optional[str] = None,
    library: str = "books",
    format: Optional[str] = None,
    output: Optional[str] = None
) -> str:
    """
    Download books by ID from Calibre servers.
    
    Args:
        book_ids: One or more book IDs from search results - REQUIRED
        server: Calibre server URL (optional, uses configured servers if not provided)
        library: Library ID (default: "books")
        format: Format to download (auto-detect if not specified)
        output: Output path (directory or filename)
    
    Returns:
        Download status and file paths
    """
    try:
        # Get client
        if server:
            client = CalibreClient(server, library)
        else:
            servers = config.load_servers()
            if not servers:
                return "Error: No servers configured. Use add_server tool or configure ~/.bookworm/servers"
            
            client = None
            for server_url in servers:
                try:
                    client = CalibreClient(server_url, library)
                    client.get_books_init("test")
                    break
                except Exception:
                    continue
            
            if not client:
                return "Error: All configured servers failed to respond"
        
        # Download books
        downloaded = []
        failed = []
        
        for book_id in book_ids:
            try:
                # Convert to int if string
                if isinstance(book_id, str):
                    book_id = int(book_id)
                
                path = download_book(client, book_id, output, format)
                downloaded.append(path)
            except Exception as e:
                failed.append(f"{book_id}: {str(e)}")
        
        # Build result
        result_lines = []
        if downloaded:
            result_lines.append(f"Successfully downloaded {len(downloaded)} book(s):")
            for path in downloaded:
                result_lines.append(f"  - {path}")
        
        if failed:
            result_lines.append(f"\nFailed to download {len(failed)} book(s):")
            for failure in failed:
                result_lines.append(f"  - {failure}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"Error downloading books: {str(e)}"


@mcp.tool()
def add_server(server_url: str) -> str:
    """
    Add a Calibre server URL to the configuration.
    
    Args:
        server_url: The server URL to add (e.g., http://69.144.163.41:8080)
    
    Returns:
        Status message
    """
    try:
        config_add_server(server_url)
        return f"Added {server_url} to configuration"
    except Exception as e:
        return f"Error adding server: {str(e)}"


@mcp.tool()
def remove_server(server_url: str) -> str:
    """
    Remove a Calibre server URL from the configuration.
    
    Args:
        server_url: The server URL to remove
    
    Returns:
        Status message
    """
    try:
        config_remove_server(server_url)
        return f"Removed {server_url} from configuration"
    except Exception as e:
        return f"Error removing server: {str(e)}"


@mcp.tool()
def list_servers() -> str:
    """
    List all configured Calibre server URLs.
    
    Returns:
        List of configured servers
    """
    try:
        servers = config_list_servers()
        if servers:
            return "Configured servers:\n" + "\n".join(f"  - {s}" for s in servers)
        else:
            return "No servers configured. Use add_server to add servers."
    except Exception as e:
        return f"Error listing servers: {str(e)}"


# =============================================================================
# RESOURCES
# =============================================================================

@mcp.resource("config://servers", mime_type="text/plain")
def get_configured_servers() -> str:
    """List all configured Calibre server URLs."""
    servers = config_list_servers()
    if servers:
        return "\n".join(servers)
    return "No servers configured."


@mcp.resource("config://bookworm/settings", mime_type="application/json")
def get_bookworm_settings() -> str:
    """Get Bookworm configuration settings."""
    import json
    from pathlib import Path
    
    settings = {
        "config_path": str(get_config_path()),
        "servers": config_list_servers()
    }
    return json.dumps(settings, indent=2)


def get_config_path() -> Path:
    """Get the path to the Bookworm config file."""
    return config.get_config_path()


@mcp.resource("book://{book_id}", mime_type="application/json")
def get_book_metadata(book_id: str) -> str:
    """Get metadata for a specific book by ID."""
    import json
    try:
        # Try configured servers
        servers = config.load_servers()
        
        if not servers:
            return json.dumps({"error": "No servers configured"})
        
        for server_url in servers:
            try:
                client = CalibreClient(server_url, "books")
                metadata = client.get_book_metadata(int(book_id))
                return json.dumps(metadata, indent=2)
            except Exception:
                continue
        
        return json.dumps({"error": "Could not fetch book metadata from any server"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# PROMPTS
# =============================================================================

@mcp.prompt()
def search_guide() -> str:
    """Guide for searching books on Calibre servers."""
    return """
You are helping a user search for ebooks on Calibre content servers.

Available search options:
- query: The search term (required) - can be title, author, or tags
- format_filter: Filter by format (epub, pdf, mobi, etc.)
- sort: Sort by timestamp, title, author, size, rating, pubdate, or pages
- order: asc or desc (default: desc)
- limit: Maximum number of results (default: 50)
- fetch_all: Set to true to fetch all results

Tips:
- Use specific search terms for better results
- Filter by format if you need a specific ebook format
- Use sort and order to organize results by relevance
- Set a reasonable limit to avoid overwhelming results

Example search: "fantasy novels" with format_filter="epub" and sort="timestamp"
"""


@mcp.prompt()
def download_guide() -> str:
    """Guide for downloading books from Calibre servers."""
    return """
You are helping a user download ebooks from Calibre content servers.

Before downloading:
1. Make sure servers are configured (use list_servers to check)
2. Search for the book you want and note its ID
3. Decide if you need a specific format

Download options:
- book_ids: One or more book IDs from search results (required)
- format: Specific format to download (optional, auto-detects if not specified)
- output: Directory or filename for the download (optional)

Tips:
- Book IDs are shown in search results
- If no format is specified, the first available format is used
- You can download multiple books at once by providing multiple IDs
- Specify output as a directory to save with original filenames

Example: Download book ID 12345 in EPUB format to ~/downloads/
"""


@mcp.prompt()
def server_setup() -> str:
    """Guide for setting up Calibre servers."""
    return """
You are helping a user set up Calibre server connections for Bookworm.

To use Bookworm, you need to configure at least one Calibre server:

1. Add a server URL:
   - Use add_server tool with the server URL
   - Example: http://69.144.163.41:8080

2. Verify configuration:
   - Use list_servers to see configured servers
   - Bookworm will try each server until one responds

3. Server configuration file:
   - Location: ~/.bookworm/servers
   - Format: One URL per line
   - Lines starting with # are comments

Tips:
- You can add multiple servers for redundancy
- Bookworm automatically tries each configured server
- Use the server parameter in search/download to override configured servers

Common Calibre server URLs:
- Public servers often follow patterns like http://IP:8080 or http://IP:8980
- Some servers require authentication (not currently supported)
"""
