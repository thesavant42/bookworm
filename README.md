
## Bookworm CLI - OPDS Book Download Tool

A command-line utility for downloading books from Calibre OPDS servers.

### Quick Start

1. **Add a server:**
   ```bash
   python bookworm.py add-server http://69.144.163.41:8080/opds
   ```

2. **Set the default server using .env file:**
   ```bash
   python bookworm.py dotenv 1
   ```
   This creates a `.env` file in your project directory.

3. **Search for books:**
   ```bash
   python bookworm.py search "haunted mansion"
   ```

4. **Override for a single command:**
   ```bash
   python bookworm.py --target=http://108.20.223.3:7000/opds search "yetis"
   ```

### Server Management

The server URL is determined by this priority order:
1. `--target` flag (highest priority - explicit override)
2. `BOOKWORM_SERVER` environment variable
3. `.env` file (BOOKWORM_SERVER in current directory)
4. Config default server (set via `set-default-server` command)
5. No server (error if none configured)

#### List configured servers
```bash
python bookworm.py list-servers
```

#### Add a new server
```bash
python bookworm.py add-server <url>
```

#### Remove a server
```bash
python bookworm.py remove-server <url>
```

#### Set default server in config
```bash
python bookworm.py set-default-server <index>
```
Where `<index>` is the 1-based position from `list-servers` output.

#### Create .env file for project-specific server
```bash
python bookworm.py dotenv <index>
```
This creates a `.env` file in the current directory that will be automatically loaded.

#### Set environment variable for current session
```bash
set BOOKWORM_SERVER=http://69.144.163.41:8080/opds
```
(On Linux/macOS: `export BOOKWORM_SERVER=http://69.144.163.41:8080/opds`)

### Search and Browse

#### Search for books
```bash
python bookworm.py search <query> [options]
```

Options:
- `--num, -n`: Number of results per page (default: 25)
- `--sort, -s`: Sort field (date, author, title, rating, size, tags, series)
- `--order, -o`: Sort order (ascending, descending)
- `--save, -S`: Download book by index or ID
- `--save-all, -A`: Download all search results
- `--format, -f`: Book format (epub, pdf, mobi, azw3)
- `--output-folder, -O`: Output directory
- `--cover, -c`: Download book cover images
- `--delay, -d`: Delay between downloads in seconds

#### Browse catalogs
```bash
python bookworm.py browse
```

#### Download a specific book by ID
```bash
python bookworm.py download <book_id>
```

### Examples

```bash
# Set server and search using .env file
python bookworm.py dotenv 1
python bookworm.py search "haunted mansion"

# Set environment variable for current session
set BOOKWORM_SERVER=http://69.144.163.41:8080/opds
python bookworm.py search "haunted mansion"

# Override server for a single command
python bookworm.py --target=http://108.20.223.3:7000/opds search "yetis"

# Search and download all results in EPUB format
python bookworm.py search "haunted mansion" --save-all --format epub --output-folder ./books

# Browse with explicit target
python bookworm.py browse --target http://example.com:8080/opds
```

### Configuration

Configuration is stored in `~/.bookworm/config.json`. Contains:
- `opds_servers`: List of configured server URLs
- `default_server`: Default server (used if no env var or --target specified)
- `download_format`: Preferred format (default: epub)
- `output_directory`: Default download location

### Known Issues

- [ ] format - **NOT TESTED** - Search results may return limited formats
- [ ] cover - **NOT TESTED** - Cover embedding in downloaded files
