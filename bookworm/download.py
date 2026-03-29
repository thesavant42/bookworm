"""Download command implementation for Bookworm CLI."""

import os
from pathlib import Path
from typing import Optional

from .client import CalibreClient
from .search import search_books


def download_book(
    client: CalibreClient,
    book_id: int,
    output: Optional[str] = None,
    format: str = None
) -> str:
    """
    Download a book by ID.
    
    Args:
        client: CalibreClient instance
        book_id: Book ID to download
        output: Output path (directory or filename)
        format: Format to download (auto-detect if not specified)
        
    Returns:
        Path to downloaded file
    """
    # Step 1: Get book metadata to determine available formats
    print(f"\nGetting metadata for book {book_id}...")
    metadata = client.get_book_metadata(book_id)
    
    book_metadata = metadata.get(str(book_id), metadata)
    
    # Step 2: Select format
    available_formats = book_metadata.get("formats", [])
    
    if not available_formats:
        raise RuntimeError(f"No formats available for book {book_id}")
    
    if format:
        # Validate format is available
        if format.upper() not in [f.upper() for f in available_formats]:
            raise RuntimeError(f"Format {format} not available for book {book_id}. Available: {available_formats}")
        selected_format = format.upper()
    else:
        # Auto-select first available format
        selected_format = available_formats[0].upper()
    
    print(f"Selected format: {selected_format}")
    
    # Step 3: Download file
    print(f"\nDownloading {selected_format}...")
    # Get book title for proper filename
    book_title = book_metadata.get("title", None)
    filename, content = client.download_book(selected_format, book_id, book_title)
    
    # Step 4: Determine output path
    if output:
        output_path = Path(output)
        if output_path.is_dir():
            # Output is a directory - save with original filename
            final_path = output_path / filename
        else:
            # Output is a filename - use as-is
            final_path = output_path
    else:
        # Save to current directory with original filename
        final_path = Path.cwd() / filename
    
    # Create parent directories if needed
    final_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file
    with open(final_path, 'wb') as f:
        f.write(content)
    
    file_size = len(content)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"\nDownload complete: {final_path}")
    print(f"File size: {file_size_mb:.2f} MB")
    
    return str(final_path)


def download_books(
    server_url: str,
    book_ids: list,
    library_id: str = "books",
    output: str = None,
    format: str = None
) -> list:
    """
    Download multiple books.
    
    Args:
        server_url: Calibre server URL
        book_ids: List of book IDs to download
        library_id: Library ID
        output: Output path
        format: Format to download
        
    Returns:
        List of downloaded file paths
    """
    client = CalibreClient(server_url, library_id)
    
    downloaded = []
    
    for book_id in book_ids:
        try:
            path = download_book(client, book_id, output, format)
            downloaded.append(path)
        except Exception as e:
            print(f"Failed to download book {book_id}: {e}")
    
    return downloaded
