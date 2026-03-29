# Bookworm

A minimalist CLI utility for searching and downloading ebooks from Calibre content servers.

## Installation

### From GitHub Releases

```bash
# Install specific version
uv install https://github.com/thesavant42/bookworm/releases/download/v1.0.0/bookworm-1.0.0-py3-none-any.whl

# Or using pip
pip install https://github.com/thesavant42/bookworm/releases/download/v1.0.0/bookworm-1.0.0-py3-none-any.whl
```

### From Source

```bash
# Clone the repository
git clone https://github.com/thesavant42/bookworm.git
cd bookworm
pip install -e .
```

---

## Quick Start

### Configure Servers

Add server URLs to the configuration:

```bash
bookworm config add http://69.144.163.41:8080
bookworm config add http://66.110.246.39:8980
```

Or create `~/.bookworm/servers` file with one URL per line:

```
http://69.144.163.41:8080
http://66.110.246.39:8980
https://calibrebooks.dwilliams.cloud
```

### Search for Books

```bash
# Basic search
bookworm search --query "batman"

# With format filter
bookworm search --query "indiana jones" --format epub

# With sorting
bookworm search --query "fantasy" --sort timestamp --order desc

# Limit results
bookworm search --query "sci-fi" --limit 20

# Fetch all results
bookworm search --query "classic" --all
```

### Download Books

```bash
# Download single book (auto-select format)
bookworm download 94036

# Download specific format
bookworm download 94036 --format EPUB

# Download to specific path
bookworm download 94036 --output ./mybooks/

# Download multiple books
bookworm download 94036 30098 30102
```

## Commands

### `bookworm search`

Search for books on Calibre servers.

**Options:**

| Option | Description |
|--------|-------------|
| `--query, -q` | Search string (title, author, tags) - REQUIRED |
| `--server, -s` | Calibre server URL |
| `--library, -l` | Library ID (default: books) |
| `--format, -f` | Filter by format (epub, pdf, mobi, etc.) |
| `--sort, -S` | Sort field (timestamp, title, author, size, rating, pubdate, pages) |
| `--order, -O` | Sort order (asc, desc) |
| `--limit, -n` | Max results to display (default: 50) |
| `--all` | Fetch ALL results by iterating through all pages |

### `bookworm download`

Download books by ID.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `book_ids` | One or more book IDs from search results - REQUIRED |

**Options:**

| Option | Description |
|--------|-------------|
| `--server, -s` | Calibre server URL |
| `--library, -l` | Library ID (default: books) |
| `--format, -f` | Format to download (auto-detect if not specified) |
| `--output, -o` | Output path (directory or filename) |

### `bookworm config`

Manage server configuration.

**Subcommands:**

| Command | Description |
|---------|-------------|
| `add <url>` | Add a server URL to the config |
| `remove <url>` | Remove a server URL from the config |
| `list` | List configured servers |

## Configuration

Bookworm stores server URLs in `~/.bookworm/servers`. Each URL is on a separate line.

```
# Example ~/.bookworm/servers
http://69.144.163.41:8080
http://66.110.246.39:8980
https://calibrebooks.dwilliams.cloud
```

The application iterates through the list and tries each server until one responds.

Use `--server` flag to override the config with a single URL.

## API Endpoints

Bookworm interacts with Calibre content servers using the following endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/interface-data/books-init` | GET | Initial book list with search |
| `/interface-data/more-books` | POST | Paginated book results |
| `/interface-data/book-metadata/{id}` | GET | Single book metadata |
| `/get/{format}/{id}/books` | GET | Download ebook file |

## Pagination

Bookworm handles pagination transparently:

- Calibre servers return exactly 50 results per request by default
- The CLI automatically fetches additional pages when `--all` is specified
- Offset increments are exactly 50 (0, 50, 100, 150...)
- The `--limit` flag controls DISPLAY count only, never affects API request size

## Development

```bash
# Install in editable mode
pip install -e .

# Run directly
python -m bookworm.cli search --query "test"
```

## License

MIT
