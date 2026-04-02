"""Download command implementation for Bookworm CLI."""

import logging
import os
from pathlib import Path
from typing import Optional

from bookworm.client import CalibreClient
from bookworm.search import search_books

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler - writes to bookworm.log in user's home directory
log_file_path = Path.home() / ".bookworm" / "download.log"
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
    logger.info(f"Getting metadata for book {book_id} from library '{client.library_id}'")
    metadata = client.get_book_metadata(book_id)
    
    book_metadata = metadata.get(str(book_id), metadata)
    
    # Log actual metadata content
    title = book_metadata.get("title", "Unknown")
    author = book_metadata.get("author", "Unknown")
    available_formats = book_metadata.get("formats", [])
    logger.info(f"Book {book_id}: '{title}' by {author}, available formats: {available_formats}")
    
    # Step 2: Select format
    
    if not available_formats:
        logger.error(f"No formats available for book {book_id}")
        raise RuntimeError(f"No formats available for book {book_id}")
    
    if format:
        # Validate format is available
        if format.upper() not in [f.upper() for f in available_formats]:
            logger.error(f"Format {format} not available for book {book_id}. Available: {available_formats}")
            raise RuntimeError(f"Format {format} not available for book {book_id}. Available: {available_formats}")
        selected_format = format.upper()
    else:
        # Auto-select first available format
        selected_format = available_formats[0].upper()
    
    logger.info(f"Selected format: {selected_format} for book {book_id}")
    
    # Step 3: Download file
    logger.info(f"Downloading {selected_format} for book {book_id}")
    # Get book title for proper filename
    book_title = book_metadata.get("title", None)
    filename, content = client.download_book(selected_format, book_id, book_title)
    
    # Step 4: Determine output path
    if output:
        output_path = Path(output)
        # Check if it's explicitly a directory (ends with / or \) or exists as directory
        if output.endswith(os.sep) or output.endswith('/') or output.endswith('\\') or output_path.is_dir():
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
    
    logger.info(f"Download complete: {final_path} ({file_size_mb:.2f} MB)")
    
    return str(final_path)


def download_books(
    server_url: str,
    book_ids: list,
    library_id: str = None,
    output: str = None,
    format: str = None
) -> list:
    """
    Download multiple books.
    
    Args:
        server_url: Calibre server URL
        book_ids: List of book IDs to download
        library_id: Library ID (fetched from /ajax/library-info if None)
        output: Output path
        format: Format to download
        
    Returns:
        List of downloaded file paths
    """
    logger.info(f"download_books: server={server_url}, book_ids={book_ids}, library={library_id}, format={format}")
    
    client = CalibreClient(server_url, library_id)
    logger.info(f"Initialized CalibreClient for {server_url} - library ID: '{client.library_id}'")
    logger.debug(f"Client base_url: {client.base_url}")
    
    downloaded = []
    
    for book_id in book_ids:
        try:
            logger.info(f"Processing book ID: {book_id}")
            path = download_book(client, book_id, output, format)
            downloaded.append(path)
            logger.info(f"Successfully downloaded book {book_id}")
        except Exception as e:
            logger.error(f"Failed to download book {book_id}: {e}", exc_info=True)
    
    logger.info(f"download_books complete: {len(downloaded)} succeeded, {len(book_ids) - len(downloaded)} failed")
    return downloaded
