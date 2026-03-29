#!/usr/bin/env python3
"""
bookworm.py - A command-line utility for downloading books from Calibre OPDS servers.

Usage examples:
    python bookworm.py --target="http://69.144.163.41:8080/opds"
    python bookworm.py --target="http://69.144.163.41:8080/opds" --search="haunted mansion"
    python bookworm.py --target="http://69.144.163.41:8080/opds" --save="94190"
    python bookworm.py --target="http://69.144.163.41:8080/opds" --search="haunt" --save-all --output-folder="./books"
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from models import Book, BookFormat
from opds_client import OpdsClient
from config import config


def load_env_file(env_path: Path) -> dict:
    """Load environment variables from a .env file"""
    env_vars = {}
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        env_vars[key.strip()] = value.strip().strip('"\'')
        except Exception:
            pass
    return env_vars


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


def format_book_list(books: List[Book], max_display: int = 10) -> str:
    """Format a list of books for display"""
    output = []
    display_count = min(len(books), max_display)

    for i, book in enumerate(books[:display_count], 1):
        authors = ', '.join(a.name for a in book.authors) if book.authors else 'Unknown'
        formats = ', '.join(f.format_type.upper() for f in book.formats)
        output.append(f"  {i:3d}. [{book.id}] {book.title} by {authors}")
        output.append(f"       Formats: {formats}")
        if book.tags:
            output.append(f"       Tags: {', '.join(book.tags[:5])}")

    if len(books) > max_display:
        output.append(f"\n  ... and {len(books) - max_display} more books")

    return '\n'.join(output)


def select_format(books: List[Book], format_type: Optional[str] = None) -> Optional[str]:
    """Interactive format selection for a book"""
    if not books:
        return None

    book = books[0]
    if not book.formats:
        print("  No formats available for this book")
        return None

    if len(book.formats) == 1:
        return book.formats[0].url

    if format_type:
        for fmt in book.formats:
            if fmt.format_type.lower() == format_type.lower():
                return fmt.url

    print("\n  Available formats:")
    for i, fmt in enumerate(book.formats, 1):
        print(f"    {i}. {fmt.format_type.upper()}")

    while True:
        try:
            choice = input("\n  Select format (number or format name): ").strip().lower()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(book.formats):
                    return book.formats[idx].url
            else:
                for fmt in book.formats:
                    if fmt.format_type.lower() == choice:
                        return fmt.url
            print("  Invalid choice, try again")
        except (ValueError, IndexError):
            print("  Invalid choice, try again")


def download_book(client: OpdsClient, book: Book, output_dir: str,
                  format_type: Optional[str] = None, cover: bool = False) -> bool:
    """Download a single book"""
    url = book.get_download_url(format_type)
    if not url:
        print(f"  No download URL available for: {book.title}")
        return False

    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)

    # Determine filename - use short title (before colon if present)
    book_title = book.title
    if ':' in book_title:
        book_title = book_title.split(':')[0].strip()
    title = sanitize_filename(book_title)
    author = sanitize_filename(book.authors[0].name) if book.authors else 'Unknown'

    # Get format extension
    fmt = book.get_best_format()
    ext = fmt.format_type if fmt else 'epub'

    filename = f"{title} - {author}.{ext}"
    filepath = os.path.join(output_dir, filename)

    # Handle duplicate filenames
    if os.path.exists(filepath):
        base, extension = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}{extension}"
            counter += 1

    print(f"  Downloading: {book.title}")
    print(f"  URL: {url}")

    # Use requests directly if no client provided
    try:
        import requests
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"  Saved to: {filepath}")

        # Download cover if requested
        if cover and book.cover_url:
            cover_path = os.path.join(output_dir, f"{title}_cover.jpg")
            if not os.path.exists(cover_path):
                cover_response = requests.get(book.cover_url)
                if cover_response.status_code == 200:
                    with open(cover_path, 'wb') as f:
                        f.write(cover_response.content)
                    print(f"  Cover saved to: {cover_path}")

        return True
    except requests.exceptions.RequestException as e:
        print(f"  Failed to download: {book.title}")
        print(f"  Error: {e}")
        return False


def cmd_browse(args):
    """Browse available libraries and catalogs"""
    print(f"Connecting to: {args.target}")

    client = OpdsClient(args.target, library_id=args.library_id)

    try:
        first_title, catalogs = client.get_root_catalog()

        print("\nAvailable catalogs:")
        for i, (title, url) in enumerate(catalogs.items(), 1):
            print(f"  {i}. {title}")

        if args.library_id:
            print(f"\nUsing library: {args.library_id}")

            # Get books from the catalog
            if catalogs:
                catalog_url = list(catalogs.values())[0]
                print(f"\nFetching books from: {catalog_url}")
                books = client.get_catalog_books(catalog_url)
                print(f"\nFound {len(books)} books")
                print(format_book_list(books))

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_search(args):
    """Search for books by keyword"""
    print(f"Searching: {args.target}")
    print(f"Query: {args.search}")

    client = OpdsClient(args.target, library_id=args.library_id)

    try:
        books = client.search(
            query=args.search,
            num=args.num,
            sort=args.sort,
            order=args.order
        )

        if not books:
            print("No books found matching your search.")
            return 0

        print(f"\nFound {len(books)} books:")
        print(format_book_list(books))

        if args.save_all:
            print(f"\nDownloading all {len(books)} books...")
            output_dir = args.output_folder or config.output_directory
            success_count = 0
            for i, book in enumerate(books, 1):
                print(f"\n[{i}/{len(books)}] {book.title}")
                if download_book(client, book, output_dir, args.format, args.cover):
                    success_count += 1
                if args.delay:
                    time.sleep(args.delay)

            print(f"\nDownloaded {success_count}/{len(books)} books successfully")

        elif args.save:
            # Save specific book by index
            try:
                idx = int(args.save) - 1
                if 0 <= idx < len(books):
                    output_dir = args.output_folder or config.output_directory
                    download_book(client, books[idx], output_dir, args.format, args.cover)
                else:
                    print(f"Invalid book index: {args.save}")
            except ValueError:
                # Try to find book by ID
                for book in books:
                    if book.id == args.save:
                        output_dir = args.output_folder or config.output_directory
                        download_book(client, book, output_dir, args.format, args.cover)
                        break
                else:
                    print(f"Book not found: {args.save}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_download(args):
    """Download a specific book by ID"""
    print(f"Downloading book: {args.book_id}")

    client = OpdsClient(args.target, library_id=args.library_id)

    # Get book by ID
    book = client.get_book_by_id(args.book_id)

    if not book or not book.formats:
        print(f"  Book not found: {args.book_id}")
        return 1

    print(f"  Found: {book.title}")

    output_dir = args.output_folder or config.output_directory
    success = download_book(None, book, output_dir, args.format, args.cover)

    return 0 if success else 1


def cmd_list_servers(args):
    """List configured OPDS servers"""
    print("Configured OPDS servers:")
    for i, server in enumerate(config.opds_servers, 1):
        marker = " (default)" if server == config.default_server else ""
        print(f"  {i}. {server}{marker}")

    if not config.opds_servers:
        print("  (no servers configured)")

    return 0


def cmd_add_server(args):
    """Add a new OPDS server"""
    config.add_server(args.url)
    if args.set_default:
        config.default_server = args.url
    print(f"Added server: {args.url}")
    return 0


def cmd_remove_server(args):
    """Remove an OPDS server"""
    config.remove_server(args.url)
    print(f"Removed server: {args.url}")
    return 0


def cmd_set_default_server(args):
    """Set a saved server as the default"""
    servers = config.opds_servers
    
    if not servers:
        print("No servers configured. Use 'add-server' command first.")
        return 1
    
    # If index provided, use that server
    try:
        idx = int(args.index) - 1
        if 0 <= idx < len(servers):
            config.default_server = servers[idx]
            server = servers[idx]
            print(f"Set default server: {server}")
            print(f"\nTo use this server for the current session, set the environment variable:")
            print(f"  PowerShell: $env:BOOKWORM_SERVER=\"{server}\"")
            print(f"  CMD:        set BOOKWORM_SERVER={server}")
            print(f"  Linux/macOS:  export BOOKWORM_SERVER=\"{server}\"")
            print(f"\nOr create a .env file in your project directory with:")
            print(f"  BOOKWORM_SERVER={server}")
            return 0
        else:
            print(f"Invalid index. Valid range: 1-{len(servers)}")
            return 1
    except ValueError:
        print("Index must be a number")
        return 1


def cmd_dotenv(args):
    """Create or update .env file with the server configuration"""
    servers = config.opds_servers
    
    if not servers:
        print("No servers configured. Use 'add-server' command first.")
        return 1
    
    # If index provided, use that server
    try:
        idx = int(args.index) - 1
        if 0 <= idx < len(servers):
            server = servers[idx]
            env_file = Path.cwd() / '.env'
            
            # Read existing .env file if it exists
            env_vars = load_env_file(env_file)
            env_vars['BOOKWORM_SERVER'] = server
            
            # Write to .env file
            with open(env_file, 'w') as f:
                f.write(f"# Bookworm configuration\n")
                f.write(f"BOOKWORM_SERVER={server}\n")
            
            print(f"Created/updated .env file with server: {server}")
            print(f"File: {env_file}")
            return 0
        else:
            print(f"Invalid index. Valid range: 1-{len(servers)}")
            return 1
    except ValueError:
        print("Index must be a number")
        return 1


def get_server_url(args) -> Optional[str]:
    """
    Get the server URL with the following priority:
    1. --target flag (explicit override)
    2. BOOKWORM_SERVER environment variable
    3. .env file (BOOKWORM_SERVER)
    4. Config default server
    """
    # Highest priority: explicit --target flag
    if args.target:
        return args.target
    
    # Medium priority: environment variable
    env_server = os.environ.get('BOOKWORM_SERVER')
    if env_server:
        return env_server
    
    # Check .env file in current directory
    env_file = Path.cwd() / '.env'
    env_vars = load_env_file(env_file)
    if 'BOOKWORM_SERVER' in env_vars:
        return env_vars['BOOKWORM_SERVER']
    
    # Lowest priority: config default server
    return config.default_server
    """
    Get the server URL with the following priority:
    1. --target flag (explicit override)
    2. BOOKWORM_SERVER environment variable
    3. config.default_server
    """
    # Highest priority: explicit --target flag
    if args.target:
        return args.target
    
    # Medium priority: environment variable
    env_server = os.environ.get('BOOKWORM_SERVER')
    if env_server:
        return env_server
    
    # Lowest priority: config default server
    return config.default_server


def main():
    parser = argparse.ArgumentParser(
        description='Bookworm - Download books from Calibre OPDS servers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --target="http://69.144.163.41:8080/opds"
  %(prog)s --target="http://69.144.163.41:8080/opds" --search="haunted mansion"
  %(prog)s --target="http://69.144.163.41:8080/opds" --save="94190"
  %(prog)s --target="http://69.144.163.41:8080/opds" --search="haunt" --save-all --output-folder="./books"
        """
    )

    # Global options
    parser.add_argument('--target', '-t',
                        help='OPDS server URL (e.g., http://example.com:8080/opds)')
    parser.add_argument('--library-id', '-l',
                        help='Library ID for multi-library servers')
    parser.add_argument('--download', '-D',
                        help='Download book by ID')
    parser.add_argument('--format', '-f',
                        choices=['epub', 'pdf', 'mobi', 'azw3'],
                        help='Book format to download')
    parser.add_argument('--output-folder', '-O',
                        help='Output directory for downloads')
    parser.add_argument('--cover', '-c', action='store_true',
                        help='Download book cover image')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Browse command
    browse_parser = subparsers.add_parser('browse', help='Browse available catalogs')
    browse_parser.set_defaults(func=cmd_browse)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for books')
    search_parser.add_argument('search', help='Search query')
    search_parser.add_argument('--num', '-n', type=int, default=25,
                               help='Number of results per page (default: 25)')
    search_parser.add_argument('--sort', '-s',
                               choices=['date', 'author', 'title', 'rating', 'size', 'tags', 'series'],
                               default='date', help='Sort field (default: date)')
    search_parser.add_argument('--order', '-o',
                               choices=['ascending', 'descending'],
                               default='descending', help='Sort order (default: descending)')
    search_parser.add_argument('--save', '-S',
                               help='Download book by index or ID')
    search_parser.add_argument('--save-all', '-A', action='store_true',
                               help='Download all search results')
    search_parser.add_argument('--format', '-f',
                               choices=['epub', 'pdf', 'mobi', 'azw3'],
                               help='Book format to download')
    search_parser.add_argument('--output-folder', '-O',
                               help='Output directory for downloads')
    search_parser.add_argument('--cover', '-c', action='store_true',
                               help='Download book cover images')
    search_parser.add_argument('--delay', '-d', type=float, default=0,
                               help='Delay between downloads in seconds')
    search_parser.set_defaults(func=cmd_search)

    # Download command
    download_parser = subparsers.add_parser('download', help='Download a specific book')
    download_parser.add_argument('book_id', help='Book ID to download')
    download_parser.add_argument('--format', '-f',
                                 choices=['epub', 'pdf', 'mobi', 'azw3'],
                                 help='Book format to download')
    download_parser.add_argument('--output-folder', '-O',
                                 help='Output directory for downloads')
    download_parser.add_argument('--cover', '-c', action='store_true',
                                 help='Download book cover image')
    download_parser.set_defaults(func=cmd_download)

    # Server management commands
    list_parser = subparsers.add_parser('list-servers', help='List configured servers')
    list_parser.set_defaults(func=cmd_list_servers)

    add_parser = subparsers.add_parser('add-server', help='Add a new server')
    add_parser.add_argument('url', help='Server URL to add')
    add_parser.add_argument('--set-default', '-d', action='store_true',
                            help='Set as default server')
    add_parser.set_defaults(func=cmd_add_server)

    remove_parser = subparsers.add_parser('remove-server', help='Remove a server')
    remove_parser.add_argument('url', help='Server URL to remove')
    remove_parser.set_defaults(func=cmd_remove_server)

    # Set default server command
    set_default_parser = subparsers.add_parser('set-default-server', help='Set a saved server as default')
    set_default_parser.add_argument('index', help='Server index (1-based) to set as default')
    set_default_parser.set_defaults(func=cmd_set_default_server)

    # Dotenv command
    dotenv_parser = subparsers.add_parser('dotenv', help='Create/update .env file with server')
    dotenv_parser.add_argument('index', help='Server index (1-based) to use for .env file')
    dotenv_parser.set_defaults(func=cmd_dotenv)

    args = parser.parse_args()

    # Handle legacy mode (no subcommand)
    if not args.command and args.target:
        # Check for --download flag
        if args.download:
            args.book_id = args.download
            return cmd_download(args)
        return cmd_browse(args)

    if not args.command:
        parser.print_help()
        return 0

    # Commands that require a target
    target_required_commands = ['browse', 'search', 'download']
    
    if args.command in target_required_commands:
        # Get server URL using priority chain
        server_url = get_server_url(args)
        if server_url:
            args.target = server_url
            print(f"Using server: {args.target}")
            if os.environ.get('BOOKWORM_SERVER'):
                print("  (from BOOKWORM_SERVER environment variable)")
        else:
            print("Error: No target specified.")
            print("Set BOOKWORM_SERVER environment variable or use --target flag.")
            print("Example: set BOOKWORM_SERVER=http://69.144.163.41:8080/opds")
            return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
