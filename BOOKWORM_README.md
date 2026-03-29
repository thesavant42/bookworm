# Bookworm - Calibre OPDS Client CLI

A command-line utility for downloading books from Calibre book servers using the OPDS (Open Publication Distribution System) protocol.

## Features

- Browse available libraries and catalogs on Calibre servers
- Search for books by keyword
- Download single books or batch download entire search results
- Support for multiple book formats (EPUB, PDF, MOBI, AZW3)
- Cover image download
- Configurable server management
- Persistent configuration storage

## Installation

### Requirements

- Python 3.7 or higher
- `requests` library
- `feedparser` library

### Install Dependencies

```bash
pip install requests feedparser
```

## Usage

### Basic Commands

#### Browse Available Libraries

```bash
python bookworm.py --target="http://69.144.163.41:8080/opds"
```

This will list all available catalogs and libraries on the server.

#### Search for Books

```bash
python bookworm.py --target="http://69.144.163.41:8080/opds" --search "haunted mansion"
```

Search for books matching the query string.

#### Download a Specific Book

```bash
python bookworm.py --target="http://69.144.163.41:8080/opds" download 94190
```

Download a book by its ID.

#### Download All Search Results

```bash
python bookworm.py --target="http://69.144.163.41:8080/opds" search "haunt" --save-all --output-folder="./books"
```

Download all books matching the search query.

### Subcommands

#### `browse`

Browse available catalogs on an OPDS server.

```bash
python bookworm.py --target=<server_url> browse
```

#### `search`

Search for books by keyword.

```bash
python bookworm.py --target=<server_url> search <query> [options]
```

Options:
- `-n, --num <int>`: Number of results per page (default: 25)
- `-s, --sort <field>`: Sort field (date, author, title, rating, size, tags, series)
- `-o, --order <order>`: Sort order (ascending, descending)
- `-S, --save <id>`: Download book by index or ID
- `-A, --save-all`: Download all search results
- `-f, --format <format>`: Book format to download (epub, pdf, mobi, azw3)
- `-O, --output-folder <path>`: Output directory for downloads
- `-c, --cover`: Download book cover images
- `-d, --delay <seconds>`: Delay between downloads in seconds

#### `download`

Download a specific book by ID.

```bash
python bookworm.py --target=<server_url> download <book_id> [options]
```

Options:
- `-f, --format <format>`: Book format to download (epub, pdf, mobi, azw3)
- `-O, --output-folder <path>`: Output directory for downloads
- `-c, --cover`: Download book cover image

#### `list-servers`

List all configured OPDS servers.

```bash
python bookworm.py list-servers
```

#### `add-server`

Add a new OPDS server to the configuration.

```bash
python bookworm.py add-server <url> [--set-default]
```

Options:
- `-d, --set-default`: Set as default server

#### `remove-server`

Remove an OPDS server from the configuration.

```bash
python bookworm.py remove-server <url>
```

### Configuration

Bookworm stores configuration in `~/.bookworm/config.json`. The configuration includes:

- List of configured OPDS servers
- Default server URL
- Preferred download format
- Default output directory

## Examples

### Basic Search and Download

```bash
# Search for books
python bookworm.py --target="http://69.144.163.41:8080/opds" search "fantasy"

# Download a specific book from search results
python bookworm.py --target="http://69.144.163.41:8080/opds" search "fantasy" --save 1

# Download all results as EPUB
python bookworm.py --target="http://69.144.163.41:8080/opds" search "fantasy" --save-all --format epub --output-folder "./fantasy-books"
```

### Server Management

```bash
# Add a new server
python bookworm.py add-server "http://69.144.163.41:8080/opds" --set-default

# List all configured servers
python bookworm.py list-servers

# Remove a server
python bookworm.py remove-server "http://69.144.163.41:8080/opds"
```

### Download with Cover Images

```bash
# Download a book with its cover
python bookworm.py --target="http://69.144.163.41:8080/opds" download 94190 --cover --output-folder "./books"
```

## Architecture

The project consists of the following modules:

- [`bookworm.py`](bookworm.py): Main CLI entry point with argument parsing
- [`opds_client.py`](opds_client.py): OPDS client for interacting with Calibre servers
- [`models.py`](models.py): Data models (Book, Author, BookFormat)
- [`config.py`](config.py): Configuration management

## Testing

Run the test suite:

```bash
pip install pytest
pytest tests/
```

## License

This project is provided as-is for personal use in downloading books from Calibre OPDS servers.

## Acknowledgments

This project was inspired by the [calibre-opds-client](https://github.com/goodlibs/calibre-opds-client) plugin.