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
    library: Optional[str] = None,
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
        sort: Sort field (timestamp, title, author, size, rating, pubdate, pages)
        order: Sort order (asc, desc) - default: desc
        limit: Max results to display (default: 50)
        fetch_all: Fetch ALL results by iterating through all pages
    
    Returns:
        Formatted search results
    """
    try:
        logger.info(f"search_books: query='{query}', server={server}, library={library}, limit={limit}")
        
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
            order=order
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
        
        result = "\n".join(result_lines)
        logger.info(f"search_books result: {result[:200]}...")
        return result
        
    except Exception as e:
        logger.error(f"Error searching books: {e}", exc_info=True)
        return f"Error searching books: {str(e)}"


@mcp.tool()
async def download_books(
    book_ids: list,
    server: Optional[str] = None,
    library: Optional[str] = None,
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
                    logger.info(f"Connected to server for download: {server_url}")
                    break
                except Exception as e:
                    logger.debug(f"Server {server_url} failed for download: {e}")
                    # Try default library if specified library fails
                    try:
                        client = CalibreClient(server_url, None)  # Let client auto-detect library from /ajax/library-info
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
        
        result = "\n".join(result_lines)
        logger.info(f"download_books result: {result[:200]}...")
        logger.info(f"Download complete: {len(downloaded)} success, {len(failed)} failed")
        return result
        
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
        logger.info(f"add_server result: Added {server_url} to configuration")
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
        logger.info(f"remove_server result: Removed {server_url} from configuration")
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
            result = "Configured servers:\n" + "\n".join(f"  - {s}" for s in servers)
            logger.info(f"list_servers result: {result[:200]}...")
            return result
        else:
            logger.info("list_servers result: No servers configured")
            return "No servers configured. Use add_server to add servers."
    except Exception as e:
        return f"Error listing servers: {str(e)}"


@mcp.tool()
def list_libraries(server: Optional[str] = None) -> str:
    """
    List all available libraries from a Calibre server.
    
    Args:
        server: Calibre server URL (optional, uses configured servers if not provided)
    
    Returns:
        Formatted list of available libraries
    """
    import json
    import urllib.request
    
    # Get server URL
    if server:
        server_url = server
    else:
        servers = config.load_servers()
        if not servers:
            logger.warning("No servers configured")
            return "Error: No servers configured. Use add_server to add servers."
        server_url = servers[0]
    
    try:
        # Direct HTTP request to /ajax/library-info endpoint
        with urllib.request.urlopen(f"{server_url.rstrip('/')}/ajax/library-info", timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            library_map = data.get("library_map", {})
            
            if library_map:
                result_lines = [f"Available libraries on {server_url}:\n"]
                for lib_id, lib_name in library_map.items():
                    result_lines.append(f"  - {lib_name} (ID: {lib_id})")
                result = "\n".join(result_lines)
                logger.info(f"list_libraries result: {result[:200]}...")
                return result
            else:
                logger.info("list_libraries result: No libraries found")
                return "No libraries found"
                
    except Exception as e:
        logger.error(f"Error listing libraries: {e}", exc_info=True)
        return f"Error listing libraries: {str(e)}"


@mcp.tool()
async def get_book_metadata(
    book_id: int,
    server: Optional[str] = None,
    library: Optional[str] = None
) -> str:
    """
    Get metadata for a specific book by ID.
    
    Args:
        book_id: Book ID - REQUIRED
        server: Calibre server URL (optional, uses configured servers if not provided)
        library: Library ID (default: "books")
    
    Returns:
        Formatted book metadata including title, author, publisher, published date, format, tags, ISBN
    """
    try:
        logger.info(f"get_book_metadata: book_id={book_id}, server={server}, library={library}")
        
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
                    logger.info(f"Connected to server: {server_url}")
                    break
                except Exception as e:
                    logger.debug(f"Server {server_url} failed: {e}")
                    # Try default library if specified library fails
                    try:
                        client = CalibreClient(server_url, None)  # Let client auto-detect library from /ajax/library-info
                        library = client.library_id
                        logger.info(f"Auto-detected library '{library}' from server {server_url}")
                        break
                    except Exception:
                        continue
            
            if not client:
                return "Error: All configured servers failed to respond"
        
        # Fetch metadata
        metadata = client.get_book_metadata(book_id)
        logger.info(f"Got metadata for book {book_id} from {client.base_url}, library={client.library_id}")
        
        # Format metadata as human-readable string
        result_lines = []
        result_lines.append(f"Book ID: {book_id}")
        result_lines.append("")
        
        # Extract and display metadata fields - using correct Calibre API field names
        # Note: Calibre API returns fields like "authors" (list), "formats" (list), etc.
        
        title = metadata.get("title", "Unknown")
        result_lines.append(f"Title: {title}")
        
        # Authors is a list in Calibre API
        authors = metadata.get("authors", [])
        if isinstance(authors, list):
            author_str = " & ".join(authors) if authors else "Unknown"
        else:
            author_str = authors if authors else "Unknown"
        result_lines.append(f"Authors: {author_str}")
        
        publisher = metadata.get("publisher", "Unknown")
        result_lines.append(f"Publisher: {publisher}")
        
        # Formats is a list in Calibre API
        formats = metadata.get("formats", [])
        if isinstance(formats, list) and formats:
            format_str = formats[0]
            result_lines.append(f"Formats: {format_str}")
        elif isinstance(formats, str) and formats:
            result_lines.append(f"Formats: {formats}")
        
        # Tags
        tags = metadata.get("tags", [])
        if isinstance(tags, list) and tags:
            tags_str = ", ".join(tags)
            result_lines.append(f"Tags: {tags_str}")
        
        # Size in MB
        size_bytes = metadata.get("size", 0)
        if size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            result_lines.append(f"Size: {size_mb:.1f} MB")
        
        # Published date (pubdate from Calibre API)
        pubdate = metadata.get("pubdate", None)
        if pubdate:
            # Handle datetime object or ISO string - format as "Jan 2026"
            if hasattr(pubdate, 'strftime'):
                # It's a datetime object
                published_str = pubdate.strftime("%b %Y")
            else:
                # It's a string (ISO format like "2026-01-20T08:00:00+00:00")
                try:
                    from datetime import datetime
                    if isinstance(pubdate, str):
                        dt = datetime.fromisoformat(pubdate.replace('Z', '+00:00'))
                        published_str = dt.strftime("%b %Y")
                    else:
                        published_str = str(pubdate)
                except:
                    published_str = str(pubdate)
            result_lines.append(f"Published: {published_str}")
        
        # Pages from Calibre API
        pages = metadata.get("pages", None)
        if pages:
            result_lines.append(f"Pages: {pages}")
        
        # Notes/Comments (comments from Calibre API)
        notes = metadata.get("comments", "")
        if notes:
            result_lines.append("")
            result_lines.append(notes)
        
        # Languages
        languages = metadata.get("languages", [])
        if isinstance(languages, list) and languages:
            result_lines.append(f"Languages: {', '.join(languages)}")
        
        # Identifiers (ISBN, etc.)
        identifiers = metadata.get("identifiers", {})
        if identifiers:
            id_pairs = []
            isbn_list = []
            for id_type, id_val in identifiers.items():
                id_str = str(id_val)
                if id_type == "isbn" or id_str.startswith("978") or id_str.startswith("979"):
                    isbn_list.append(id_str)
                else:
                    id_pairs.append(f"{id_type}: {id_str}")
            
            if isbn_list:
                result_lines.append(f"Identifiers: {', '.join(isbn_list)}")
            if id_pairs:
                result_lines.append(f"Identifiers: {', '.join(id_pairs)}")
        
        result = "\n".join(result_lines)
        logger.info(f"get_book_metadata result: {result[:200]}...")
        return result
        
    except Exception as e:
        logger.error(f"Error getting book metadata: {e}", exc_info=True)
        return f"Error getting book metadata: {str(e)}"


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
                # Auto-detect library from /ajax/library-info
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
        logger.info("Starting MCP server run()")
        mcp.run()
    except Exception as e:
        logger.error(f"FATAL ERROR starting MCP server: {e}", exc_info=True)
