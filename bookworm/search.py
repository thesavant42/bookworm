"""Search command implementation for Bookworm CLI."""

from typing import Dict, List, Optional

from .client import CalibreClient


PAGE_SIZE = 50  # HARD LIMIT - Calibre servers will crash if exceeded


def search_books(
    client: CalibreClient,
    query: str,
    limit: int = 50,
    fetch_all: bool = False,
    sort: str = None,
    order: str = "desc",
    format_filter: str = None
) -> Dict[str, Dict]:
    """
    Search for books with transparent pagination.
    
    Args:
        client: CalibreClient instance
        query: Search string
        limit: Max results to DISPLAY (default 50)
        fetch_all: If True, fetch ALL results by iterating through all pages
        sort: Sort field (optional)
        order: Sort order (asc/desc)
        format_filter: Filter by format (optional)
        
    Returns:
        Dict of book metadata keyed by book ID, limited to `limit` count
    """
    total = None
    offset = 0
    all_books = {}
    
    # Step 1: Initial request (books-init) - returns first 50
    response = client.get_books_init(query, sort, order)
    
    total = response["search_result"]["total_num"]
    all_books.update(response["metadata"])
    offset = response["search_result"]["num"]
    
    print(f"Found {total} results")
    
    # Step 2: Fetch remaining pages if --all is specified
    if fetch_all and total > PAGE_SIZE:
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE  # Ceiling division
        print(f"Fetching {pages} pages ({total} results)...")
        
        while offset < total:
            response = client.get_more_books(query, offset, sort, order)
            all_books.update(response["metadata"])
            offset += PAGE_SIZE
    
    # Step 3: Apply format filter if specified
    if format_filter:
        filtered_books = {}
        for book_id, metadata in all_books.items():
            if format_filter.lower() in [f.lower() for f in metadata.get("formats", [])]:
                filtered_books[book_id] = metadata
        all_books = filtered_books
    
    # Step 4: Apply display limit
    limited_books = dict(list(all_books.items())[:limit])
    
    return limited_books


def format_result(book_id: str, metadata: Dict) -> Dict:
    """
    Format book metadata for display.
    
    Args:
        book_id: Book ID
        metadata: Book metadata dict
        
    Returns:
        Formatted book data
    """
    authors = metadata.get("authors", ["Unknown"])
    author_str = ", ".join(authors) if authors else "Unknown"
    
    formats = metadata.get("formats", [])
    format_str = formats[0] if formats else "N/A"
    
    size_bytes = metadata.get("size", 0)
    size_mb = size_bytes / (1024 * 1024)
    
    return {
        "id": book_id,
        "title": metadata.get("title", "Unknown Title"),
        "author": author_str,
        "format": format_str,
        "size": size_mb
    }


def display_results(books: Dict[str, Dict], limit: int, total: int = None) -> None:
    """
    Display search results in a formatted table.
    
    Args:
        books: Dict of formatted book data
        limit: Display limit
        total: Total number of results (optional)
    """
    book_list = list(books.values())
    
    if total is None:
        total = len(book_list)
    
    # Print header
    print(f"\nFound {total} results" + (f" (showing first {limit})" if limit < total else "") + ":")
    print()
    
    # Calculate column widths
    id_width = max(len("ID"), max((len(str(b["id"])) for b in book_list), default=4))
    title_width = max(len("Title"), max((len(b["title"]) for b in book_list), default=20))
    author_width = max(len("Author"), max((len(b["author"]) for b in book_list), default=10))
    format_width = max(len("Format"), max((len(b["format"]) for b in book_list), default=4))
    
    # Print header row
    header = f"{'ID':<{id_width}}  {'Title':<{title_width}}  {'Author':<{author_width}}  {'Format':<{format_width}}  Size (MB)"
    print(header)
    print("-" * len(header))
    
    # Print book rows
    for book in book_list:
        row = f"{book['id']:<{id_width}}  {book['title']:<{title_width}}  {book['author']:<{author_width}}  {book['format']:<{format_width}}  {book['size']:.2f}"
        print(row)
