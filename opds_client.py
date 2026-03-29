"""opds_client.py: OPDS client for interacting with Calibre book servers

Ported from calibre-opds-client with modifications for CLI usage.
"""

import datetime
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple

import feedparser
import requests

from models import Book, Author, BookFormat


class OpdsClient:
    """Client for interacting with OPDS catalogs"""

    def __init__(self, base_url: str, library_id: Optional[str] = None):
        """
        Initialize the OPDS client.

        Args:
            base_url: Base URL of the OPDS server (e.g., http://example.com:8080/opds)
            library_id: Optional library ID for multi-library servers
        """
        self.base_url = base_url.rstrip('/')
        self.library_id = library_id
        self.session = requests.Session()

    def _build_url(self, path: str, params: Optional[Dict[str, str]] = None) -> str:
        """Build a full URL from a path and optional query parameters"""
        url = f"{self.base_url}{path}"
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        return url

    def _get_library_params(self) -> Dict[str, str]:
        """Get common library parameters"""
        params = {}
        if self.library_id:
            params['library_id'] = self.library_id
        return params

    def get_root_catalog(self) -> Tuple[Optional[str], Dict[str, str]]:
        """
        Get the root catalog entries.

        Returns:
            Tuple of (first_catalog_title, dict of catalog_title -> feed_url)
        """
        response = self.session.get(self.base_url)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        catalog_entries = {}
        first_title = None

        for entry in feed.entries:
            title = entry.get('title', 'No title')
            if first_title is None:
                first_title = title

            links = entry.get('links', [])
            for link in links:
                href = link.get('href', '')
                if href:
                    catalog_entries[title] = href
                    break

        return first_title, catalog_entries

    def get_catalog_books(self, catalog_url: str) -> List[Book]:
        """
        Get books from a catalog URL.

        Args:
            catalog_url: URL of the catalog to fetch

        Returns:
            List of Book objects
        """
        books = []
        visited_urls = set()

        while catalog_url and catalog_url not in visited_urls:
            visited_urls.add(catalog_url)
            response = self.session.get(catalog_url)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                book = self._parse_opds_entry(entry)
                if book:
                    books.append(book)

            # Check for next page
            catalog_url = self._find_next_url(feed)

        return books

    def _parse_opds_entry(self, entry) -> Optional[Book]:
        """Parse an OPDS feed entry into a Book object"""
        title = entry.get('title', 'Unknown')
        book_id = entry.get('id', '')

        # Extract book ID from urn:uuid: format if present
        if book_id.startswith('urn:uuid:'):
            book_id = book_id.replace('urn:uuid:', '')

        # Parse authors
        authors = []
        author_str = entry.get('author', '')
        if author_str:
            authors.append(Author(name=author_str))

        # Parse author entries if available
        if hasattr(entry, 'authors') and entry.authors:
            authors = [Author(name=a.get('name', '')) for a in entry.authors]

        # Parse formats/links
        formats = []
        for link in entry.get('links', []):
            href = link.get('href', '')
            link_type = link.get('type', '')

            # Skip thumbnails and covers
            if link_type.startswith('image/'):
                continue

            # Determine format from type or href
            format_type = self._detect_format(link_type, href)
            if format_type and href:
                # Make absolute URL
                full_url = urllib.parse.urljoin(self.base_url, href)
                formats.append(BookFormat(format_type=format_type, url=full_url))

        # Parse tags from summary
        tags = []
        summary = entry.get('summary', '')
        if summary:
            tags = self._extract_tags(summary)

        # Extract cover URL
        cover_url = None
        for link in entry.get('links', []):
            link_type = link.get('type', '')
            if link_type == 'image/jpeg' or 'thumb' in link.get('rel', '').lower():
                cover_url = link.get('href')
                break

        return Book(
            id=book_id,
            title=title,
            authors=authors,
            formats=formats,
            timestamp=entry.get('updated'),
            updated=entry.get('updated'),
            tags=tags,
            summary=summary,
            cover_url=cover_url
        )

    def _detect_format(self, link_type: str, href: str) -> Optional[str]:
        """Detect the book format from link type or URL"""
        # Check link type first
        type_to_format = {
            'application/epub+zip': 'epub',
            'application/x-mobipocket-ebook': 'mobi',
            'application/pdf': 'pdf',
            'application/azw3': 'azw3',
            'application/x-epub': 'epub',
        }

        if link_type in type_to_format:
            return type_to_format[link_type]

        # Fall back to URL extension
        ext_to_format = {
            '.epub': 'epub',
            '.mobi': 'mobi',
            '.pdf': 'pdf',
            '.azw3': 'azw3',
            '.azw': 'azw3',
        }

        href_lower = href.lower()
        for ext, fmt in ext_to_format.items():
            if href_lower.endswith(ext):
                return fmt

        return None

    def _extract_tags(self, summary: str) -> List[str]:
        """Extract tags from book summary"""
        tags = []
        tag_match = re.search(r'TAGS:\s*([^\n]+)', summary)
        if tag_match:
            tags_line = tag_match.group(1).replace('<br />', '')
            tags = [t.strip() for t in tags_line.split(',')]
        return tags

    def _find_next_url(self, feed) -> Optional[str]:
        """Find the next page URL in a feed"""
        for link in feed.feed.get('links', []):
            if link.get('rel') == 'next':
                return link.get('href')
        return None

    def search(self, query: str, num: int = 25, sort: str = 'date',
               order: str = 'descending') -> List[Book]:
        """
        Search for books using the mobile endpoint.

        Args:
            query: Search query string
            num: Number of results per page
            sort: Sort field (date, author, title, rating, size, tags, series)
            order: Sort order (ascending, descending)

        Returns:
            List of Book objects
        """
        books = []
        start = 0

        # The mobile endpoint is at the server root, not under /opds
        server_base = self.base_url.rsplit('/opds', 1)[0] if '/opds' in self.base_url else self.base_url

        while True:
            params = self._get_library_params()
            params.update({
                'search': query,
                'num': str(num),
                'sort': sort,
                'order': order,
                'start': str(start)
            })

            full_url = f"{server_base}/mobile"
            response = self.session.get(full_url, params=params)
            response.raise_for_status()
            content = response.text

            # Check if we got any results
            if 'Books' not in content:
                break

            # Parse the HTML response for book entries
            new_books = self._parse_mobile_response(content)
            if not new_books:
                break

            books.extend(new_books)

            # Check for next page
            if f'start={start + num}' not in content:
                break

            start += num

        return books

    def _parse_mobile_response(self, html: str) -> List[Book]:
        """Parse the mobile endpoint HTML response"""
        books = []

        # Pattern to match book entries
        # Example: <span class="button"><a href="/legacy/get/EPUB/94190/books/...">epub</a></span>
        link_pattern = re.compile(
            r'<span class="button"><a href="([^"]+)">(\w+)</a></span>'
        )

        # Pattern to match book info
        # Example: <span class="first-line">Title by Author</span>
        # <span class="second-line">Date Tags=[...] </span>
        title_pattern = re.compile(
            r'<span class="first-line">([^<]+)</span>'
        )

        tags_pattern = re.compile(
            r'Tags=\[([^\]]+)\]'
        )

        # Find all book entries
        links = list(link_pattern.finditer(html))
        titles = list(title_pattern.finditer(html))

        for i, link_match in enumerate(links):
            if i >= len(titles):
                break

            url = link_match.group(1)
            format_type = link_match.group(2).lower()

            title_text = titles[i].group(1).strip()

            # Parse title and author
            author = 'Unknown'
            title = title_text
            if ' by ' in title_text:
                parts = title_text.split(' by ', 1)
                title = parts[0].strip()
                author = parts[1].strip()

            # Extract tags
            tags = []
            tags_match = tags_pattern.search(html[link_match.start():link_match.start()+500])
            if tags_match:
                tags = [t.strip() for t in tags_match.group(1).split(';')]

            # Build full URL
            # The URL is relative, need to make it absolute
            server_base = self.base_url.rsplit('/opds', 1)[0] if '/opds' in self.base_url else self.base_url
            full_url = urllib.parse.urljoin(server_base, url)

            book = Book(
                id=self._extract_book_id(url),
                title=title,
                authors=[Author(name=author)],
                formats=[BookFormat(format_type=format_type, url=full_url)],
                tags=tags
            )
            books.append(book)

        return books

    def _extract_book_id(self, url: str) -> str:
        """Extract book ID from a download URL"""
        # Pattern: /legacy/get/EPUB/94190/books/...
        match = re.search(r'/legacy/get/\w+/(\d+)/', url)
        if match:
            return match.group(1)

        # Pattern: /get/EPUB/94190/books
        match = re.search(r'/get/\w+/(\d+)', url)
        if match:
            return match.group(1)

        return 'unknown'

    def get_cover(self, book_id: str) -> Optional[bytes]:
        """
        Get book cover image.

        Args:
            book_id: ID of the book

        Returns:
            Image data as bytes
        """
        params = self._get_library_params()
        url = f'/get/cover/{book_id}/books'

        try:
            full_url = self._build_url(url, params)
            response = self.session.get(full_url)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException:
            return None

    def get_book_by_id(self, book_id: str) -> Optional[Book]:
        """
        Get a book by its ID by searching and matching the exact book ID.

        Args:
            book_id: The book ID to download

        Returns:
            Book object with title and download URL
        """
        # Search with empty query to get all books
        books = self.search('', num=100)
        
        # Find the book with matching ID
        for book in books:
            if book.id == book_id:
                return book
        
        return None

    def download_book(self, url: str, dest_path: str) -> bool:
        """
        Download a book to the specified path.

        Args:
            url: Download URL
            dest_path: Local file path to save the book

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except requests.exceptions.RequestException:
            return False
