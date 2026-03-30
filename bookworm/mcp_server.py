"""FastMCP server for Bookworm - Calibre ebook search and download service."""

import logging
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from bookworm.client import CalibreClient
from bookworm import config
from bookworm.download import download_book
from bookworm.search import search_books as search_books_module, format_result

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler - writes to bookworm.log in user's home directory
log_file_path = Path.home() / ".bookworm" / "mcp_server.log"
log_file_path.parent.mkdir(parents=True, exist_ok=True)

file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Aliases for config functions
config_add_server = config.add_server
config_list_servers = config.load_servers
config_remove_server = config.remove_server


# Create the FastMCP server instance
mcp = FastMCP("Bookworm MCP Server")


# =============================================================================
# TOOLS
# =============================================================================

@mcp.tool()
async def search_books(
    query: str,
    server: Optional[str] = None,
    library: str = None,
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
        logger.info(f"search_books: query='{query}', server={server}, library={library}, format={format_filter}, limit={limit}")
        
        # Get client
        if server:
            logger.debug(f"Using provided server: {server}")
            client = CalibreClient(server, library)
        else:
            servers = config.load_servers()
            if not servers:
                logger.warning("No servers configured")
                return "Error: No servers configured. Use add_server tool or configure ~/.bookworm/servers"
            
            client = None
            for server_url in servers:
                logger.debug(f"Trying server: {server_url}")
                try:
                    client = CalibreClient(server_url, library)
                    client.get_books_init("test")
                    logger.info(f"Connected to server: {server_url}")
                    break
                except Exception as e:
                    logger.debug(f"Server {server_url} failed: {e}")
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
        
        logger.info(f"Search found {len(formatted_books)} results")
        
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
        logger.error(f"Error searching books: {e}", exc_info=True)
        return f"Error searching books: {str(e)}"


@mcp.tool()
async def download_books(
    book_ids: list,
    server: Optional[str] = None,
    library: str = None,
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
        logger.info(f"download_books: book_ids={book_ids}, server={server}, library={library}, format={format}")
        
        # Get client
        if server:
            logger.debug(f"Using provided server: {server}")
            client = CalibreClient(server, library)
        else:
            servers = config.load_servers()
            if not servers:
                logger.warning("No servers configured for download")
                return "Error: No servers configured. Use add_server tool or configure ~/.bookworm/servers"
            
            client = None
            for server_url in servers:
                logger.debug(f"Trying server for download: {server_url}")
                try:
                    client = CalibreClient(server_url, library)
                    # Try with the specified library ID
                    client.get_books_init("test")
                    logger.info(f"Connected to server for download: {server_url}")
                    break
                except Exception as e:
                    logger.debug(f"Server {server_url} failed for download: {e}")
                    # Try default library if specified library fails
                    try:
                        client = CalibreClient(server_url, None)  # Let client auto-detect library from OPDS
                        client.get_books_init("test")
                        library = client.library_id
                        logger.info(f"Auto-detected library '{library}' from server {server_url}")
                        break
                    except Exception:
                        continue
            
            if not client:
                logger.error("All configured servers failed to respond for download")
                return "Error: All configured servers failed to respond"
        
        # Download books
        downloaded = []
        failed = []
        
        for book_id in book_ids:
            try:
                logger.info(f"Downloading book ID: {book_id}")
                # Convert to int if string
                if isinstance(book_id, str):
                    book_id = int(book_id)
                
                path = download_book(client, book_id, output, format)
                downloaded.append(path)
                logger.info(f"Successfully downloaded book {book_id} to {path}")
            except Exception as e:
                logger.error(f"Failed to download book {book_id}: {e}", exc_info=True)
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
        
        logger.info(f"Download complete: {len(downloaded)} success, {len(failed)} failed")
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error downloading books: {e}", exc_info=True)
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
                # Auto-detect library from /opds
                client = CalibreClient(server_url, None)
                metadata = client.get_book_metadata(int(book_id))
                logger.info(f"Got metadata for book {book_id} from {server_url}, library={client.library_id}")
                return json.dumps(metadata, indent=2)
            except Exception as e:
                logger.debug(f"Failed to get metadata from {server_url}: {e}")
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


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        log("Starting MCP server run()")
        mcp.run()
    except Exception as e:
        log_fatal(f"FATAL ERROR starting MCP server: {e}")
